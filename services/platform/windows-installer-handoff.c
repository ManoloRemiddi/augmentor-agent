/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Inno's x64 Setup loads this helper, including on ARM64 Windows. No application
 * DLL/runtime is loaded from the replacement directory during maintenance.
 */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>
#include "windows-lease.h"

static HANDLE channel = INVALID_HANDLE_VALUE, startup = INVALID_HANDLE_VALUE;
static HANDLE runtime = INVALID_HANDLE_VALUE, coordinator = NULL;

__declspec(dllexport) void WINAPI AugmentorHandoffClose(void) {
    if (channel != INVALID_HANDLE_VALUE) CloseHandle(channel);
    if (startup != INVALID_HANDLE_VALUE) CloseHandle(startup);
    if (runtime != INVALID_HANDLE_VALUE) CloseHandle(runtime);
    if (coordinator) CloseHandle(coordinator);
    channel = startup = runtime = INVALID_HANDLE_VALUE; coordinator = NULL;
}

static BOOL exchange_bytes(void *buffer, DWORD length, BOOL write, DWORD timeout) {
    OVERLAPPED operation = {0};
    operation.hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!operation.hEvent) return FALSE;
    DWORD transferred = 0;
    BOOL ok = write ? WriteFile(channel, buffer, length, &transferred, &operation)
                    : ReadFile(channel, buffer, length, &transferred, &operation);
    if (!ok && GetLastError() == ERROR_IO_PENDING) {
        DWORD result = WaitForSingleObject(operation.hEvent, timeout);
        if (result == WAIT_OBJECT_0) ok = GetOverlappedResult(channel, &operation, &transferred, FALSE);
        else {
            CancelIoEx(channel, &operation);
            GetOverlappedResult(channel, &operation, &transferred, TRUE);
            ok = FALSE;
        }
    }
    CloseHandle(operation.hEvent);
    return ok && transferred == length;
}

static BOOL same_user(HANDLE process, PSID user) {
    HANDLE token = NULL; TOKEN_USER *identity = NULL; DWORD size = 0; BOOL ok = FALSE;
    if (!OpenProcessToken(process, TOKEN_QUERY, &token)) goto done;
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    if (!size || !(identity = malloc(size)) ||
            !GetTokenInformation(token, TokenUser, identity, size, &size)) goto done;
    ok = EqualSid(user, identity->User.Sid);
done:
    free(identity); if (token) CloseHandle(token); return ok;
}

static BOOL validate_gate(PSID user, const wchar_t *qualification) {
    wchar_t directory[32768], expected[32768], actual[32768];
    if (qualification && qualification[0]) {
#ifdef AUGMENTOR_DEVELOPMENT_CANDIDATE
        DWORD count = GetFullPathNameW(qualification, 32768, directory, NULL);
        if (!count || count >= 32768) return FALSE;
#else
        return FALSE;
#endif
    } else {
        wchar_t local[MAX_PATH];
        if (FAILED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, SHGFP_TYPE_CURRENT, local)) ||
                swprintf_s(directory, 32768, L"%ls\\Augmentor\\run", local) < 0) return FALSE;
    }
    runtime = augmentor_private_directory(directory, user, NULL, FALSE);
    if (runtime == INVALID_HANDLE_VALUE ||
            swprintf_s(expected, 32768, L"%ls\\startup.lock", directory) < 0) return FALSE;
    BY_HANDLE_FILE_INFORMATION info;
    if (GetFileType(startup) != FILE_TYPE_DISK || !GetFileInformationByHandle(startup, &info) ||
            info.nNumberOfLinks != 1 || info.dwFileAttributes &
                (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) ||
            !augmentor_private_descriptor(startup, user)) return FALSE;
    DWORD count = GetFinalPathNameByHandleW(startup, actual, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!count || count >= 32768 || wcsncmp(actual, L"\\\\?\\", 4) || _wcsicmp(actual + 4, expected)) return FALSE;
    /* Confirm that this transfer actually excludes a fresh startup reader. */
    HANDLE probe = CreateFileW(expected, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (probe != INVALID_HANDLE_VALUE) { CloseHandle(probe); return FALSE; }
    return GetLastError() == ERROR_SHARING_VIOLATION;
}

__declspec(dllexport) BOOL WINAPI AugmentorHandoffPrepare(const wchar_t *pipe,
        DWORD expected_pid, const wchar_t *qualification) {
    HANDLE token = NULL; TOKEN_USER *identity = NULL; DWORD size = 0, observed_pid = 0;
    BOOL ok = FALSE;
    const unsigned char hello[8] = {'A','U','G','I',1,0,0,0};
    const unsigned char ready[8] = {'R','E','A','D','Y',0,0,0};
    unsigned char response[12], decision[8];
    if (channel != INVALID_HANDLE_VALUE || startup != INVALID_HANDLE_VALUE || !expected_pid ||
            !pipe || wcslen(pipe) > 256 || wcsncmp(pipe, L"\\\\.\\pipe\\Augmentor.Agent.", 24)) return FALSE;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) goto done;
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    if (!size || !(identity = malloc(size)) ||
            !GetTokenInformation(token, TokenUser, identity, size, &size)) goto done;
    channel = CreateFileW(pipe, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING,
        FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION, NULL);
    if (channel == INVALID_HANDLE_VALUE || !GetNamedPipeServerProcessId(channel, &observed_pid) ||
            observed_pid != expected_pid) goto done;
    coordinator = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, FALSE, observed_pid);
    if (!coordinator || WaitForSingleObject(coordinator, 0) != WAIT_TIMEOUT ||
            !same_user(coordinator, identity->User.Sid)) goto done;
    if (!exchange_bytes((void *)hello, 8, TRUE, 5000) || !exchange_bytes(response, 12, FALSE, 5000) ||
            memcmp(response, "GATE", 4)) goto done;
    uint64_t handle_value; memcpy(&handle_value, response + 4, sizeof(handle_value));
    if (!handle_value || handle_value == UINT64_MAX || handle_value > UINTPTR_MAX) goto done;
    startup = (HANDLE)(uintptr_t)handle_value;
    if (!validate_gate(identity->User.Sid, qualification) || !exchange_bytes((void *)ready, 8, TRUE, 5000) ||
            !exchange_bytes(decision, 8, FALSE, 65000) || memcmp(decision, "APPLY\0\0\0", 8) ||
            !exchange_bytes("ACCEPTED", 8, TRUE, 5000)) goto done;
    /* Admission transfers only after explicit APPLY. The separate final
     * installation lease still has to exclude all application processes. */
    CloseHandle(channel); channel = INVALID_HANDLE_VALUE;
    ok = TRUE;
done:
    if (token) CloseHandle(token); free(identity);
    if (!ok) AugmentorHandoffClose();
    return ok;
}
