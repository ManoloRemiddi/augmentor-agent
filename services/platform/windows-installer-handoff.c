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
static HANDLE installation = INVALID_HANDLE_VALUE;
static HANDLE manifest_file = INVALID_HANDLE_VALUE, manifest_parent = INVALID_HANDLE_VALUE;
static BOOL authorized = FALSE;
static AugmentorLease manual = {INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE,
    INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE};
#include "windows-installer-cache.h"
static void augmentor_inspection_close(void);

__declspec(dllexport) void WINAPI AugmentorHandoffClose(void) {
    augmentor_inspection_close();
    augmentor_cache_close();
    if (manifest_file != INVALID_HANDLE_VALUE) CloseHandle(manifest_file);
    if (manifest_parent != INVALID_HANDLE_VALUE) CloseHandle(manifest_parent);
    manifest_file = manifest_parent = INVALID_HANDLE_VALUE;
    augmentor_release(&manual);
    if (channel != INVALID_HANDLE_VALUE) CloseHandle(channel);
    if (installation != INVALID_HANDLE_VALUE) CloseHandle(installation);
    if (coordinator) CloseHandle(coordinator);
    if (startup != INVALID_HANDLE_VALUE) CloseHandle(startup);
    if (runtime != INVALID_HANDLE_VALUE) CloseHandle(runtime);
    channel = startup = runtime = INVALID_HANDLE_VALUE; coordinator = NULL;
    installation = INVALID_HANDLE_VALUE; authorized = FALSE;
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
    authorized = TRUE;
    ok = TRUE;
done:
    if (token) CloseHandle(token); free(identity);
    if (!ok) AugmentorHandoffClose();
    return ok;
}

/* Called by the actual extracted Setup process immediately before replacement.
 * No private Python/Qt DLL is loaded here. The coordinator's real process must
 * exit, then every application's lifetime file handle must be gone. Retain both
 * this final lease and the transferred startup writer through installation. */
__declspec(dllexport) BOOL WINAPI AugmentorHandoffExclusive(DWORD timeout) {
    if (!authorized || !coordinator || startup == INVALID_HANDLE_VALUE ||
            runtime == INVALID_HANDLE_VALUE || !timeout || timeout > 30000) return FALSE;
    if (installation != INVALID_HANDLE_VALUE) return TRUE;
    ULONGLONG deadline = GetTickCount64() + timeout;
    if (WaitForSingleObject(coordinator, timeout) != WAIT_OBJECT_0) return FALSE;
    HANDLE token = NULL, file = INVALID_HANDLE_VALUE;
    TOKEN_USER *identity = NULL; DWORD size = 0;
    wchar_t directory[32768], path[32768];
    BOOL ok = FALSE;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) goto done;
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    if (!size || !(identity = malloc(size)) ||
            !GetTokenInformation(token, TokenUser, identity, size, &size)) goto done;
    DWORD count = GetFinalPathNameByHandleW(runtime, directory, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!count || count >= 32768 ||
            swprintf_s(path, 32768, L"%ls\\installation.lock", directory) < 0) goto done;
    do {
        file = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING,
            FILE_FLAG_OPEN_REPARSE_POINT, NULL);
        if (file != INVALID_HANDLE_VALUE) break;
        if (GetLastError() != ERROR_SHARING_VIOLATION || GetTickCount64() >= deadline) goto done;
        Sleep(10);
    } while (TRUE);
    BY_HANDLE_FILE_INFORMATION info;
    if (GetFileType(file) != FILE_TYPE_DISK || !GetFileInformationByHandle(file, &info) ||
            info.nNumberOfLinks != 1 || info.dwFileAttributes &
                (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) ||
            !augmentor_private_descriptor(file, identity->User.Sid)) goto done;
    OVERLAPPED operation = {0};
    if (!LockFileEx(file, LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY,
            0, 1, 0, &operation)) goto done;
    installation = file; file = INVALID_HANDLE_VALUE; ok = TRUE;
done:
    if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
    if (token) CloseHandle(token); free(identity);
    return ok;
}

/* Fresh install, same-build repair and uninstall have no running coordinator.
 * Acquire the same private startup/lifetime gates natively, before replacement.
 * No command line can turn an authenticated handoff into a manual fallback. */
__declspec(dllexport) BOOL WINAPI AugmentorMaintenancePrepare(const wchar_t *qualification) {
    if (startup != INVALID_HANDLE_VALUE || coordinator || authorized ||
            manual.file != INVALID_HANDLE_VALUE) return FALSE;
    const wchar_t *base = NULL;
    if (qualification && qualification[0]) {
#ifdef AUGMENTOR_DEVELOPMENT_CANDIDATE
        base = qualification;
#else
        return FALSE;
#endif
    }
    return augmentor_acquire_mode(&manual, base, TRUE);
}

/* Never traverse an existing redirect during application replacement/removal.
 * This is path validation, not protection against a malicious same-user writer.
 * Maintenance gates already exclude cooperating Augmentor writers. */
static BOOL plain_tree(const wchar_t *directory, unsigned depth, unsigned *remaining) {
    if (depth > 128 || !*remaining) return FALSE;
    wchar_t *path = malloc(32768 * sizeof(wchar_t));
    WIN32_FIND_DATAW found; HANDLE search = INVALID_HANDLE_VALUE;
    BOOL ok = FALSE;
    if (!path || swprintf_s(path, 32768, L"%ls\\*", directory) < 0) goto done;
    search = FindFirstFileW(path, &found);
    if (search == INVALID_HANDLE_VALUE) {
        ok = GetLastError() == ERROR_FILE_NOT_FOUND;
        goto done;
    }
    do {
        if (!wcscmp(found.cFileName, L".") || !wcscmp(found.cFileName, L"..")) continue;
        if (!*remaining || found.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT ||
                swprintf_s(path, 32768, L"%ls\\%ls", directory, found.cFileName) < 0) goto done;
        --*remaining;
        if (found.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            if (!plain_tree(path, depth + 1, remaining)) goto done;
        } else {
            HANDLE file = CreateFileW(path, FILE_READ_ATTRIBUTES,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                NULL, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, NULL);
            if (file == INVALID_HANDLE_VALUE) goto done;
            BY_HANDLE_FILE_INFORMATION info;
            BOOL valid = GetFileType(file) == FILE_TYPE_DISK && GetFileInformationByHandle(file, &info) &&
                info.nNumberOfLinks == 1 && !(info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT));
            CloseHandle(file);
            if (!valid) goto done;
        }
    } while (FindNextFileW(search, &found));
    ok = GetLastError() == ERROR_NO_MORE_FILES;
done:
    if (search != INVALID_HANDLE_VALUE) FindClose(search);
    free(path); return ok;
}

__declspec(dllexport) BOOL WINAPI AugmentorMaintenancePath(const wchar_t *directory) {
    if ((!authorized && manual.file == INVALID_HANDLE_VALUE) || !directory) return FALSE;
    wchar_t path[32768];
    DWORD length = GetFullPathNameW(directory, 32768, path, NULL);
    if (!length || length >= 32764 || path[1] != L':' || path[2] != L'\\' || wcschr(path + 2, L':')) return FALSE;
    /* Setup's own Win32 path policy is independent of the embedded app's
     * longPathAware manifest. Its payload includes ordinary paths over 260
     * characters; use explicit extended local paths for every native walk. */
    memmove(path + 4, path, (length + 1) * sizeof(wchar_t));
    memcpy(path, L"\\\\?\\", 4 * sizeof(wchar_t)); length += 4;
    BOOL exists = TRUE;
    for (DWORD i = 7; i <= length; ++i) {
        if (i < length && path[i] != L'\\') continue;
        wchar_t saved = path[i]; path[i] = 0;
        DWORD attributes = GetFileAttributesW(path), error = GetLastError();
        path[i] = saved;
        if (attributes == INVALID_FILE_ATTRIBUTES) {
            if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND) return FALSE;
            exists = FALSE;
        } else if (attributes & FILE_ATTRIBUTE_REPARSE_POINT || !(attributes & FILE_ATTRIBUTE_DIRECTORY)) return FALSE;
    }
    unsigned remaining = 250000;
    return !exists || plain_tree(path, 0, &remaining);
}

/* Own only exact REG_SZ values under HKCU. Callers supply compiled installer
 * locations, never command-line registry redirects. No recursive key removal,
 * foreign replacement, HKLM write or StartupApproved mutation is available.
 * Results: 0 error, 1 absent, 2 matching/success, 3 foreign. Actions: inspect,
 * create-if-absent, remove-if-matching. Keep the same installation gate held. */
__declspec(dllexport) DWORD WINAPI AugmentorOwnedRegistry(const wchar_t *path,
        const wchar_t *name, const wchar_t *expected, DWORD action) {
    HKEY key = NULL; wchar_t *value = NULL; DWORD result = 0;
    /* Pascal Script marshals an empty String as NULL. Windows accepts NULL
     * or an empty name for a key's default value (used by native messaging). */
    if (!name) name = L"";
    if ((installation == INVALID_HANDLE_VALUE && manual.file == INVALID_HANDLE_VALUE) ||
            !path || !expected || action > 2 ||
            wcsncmp(path, L"Software\\", 9) || wcslen(path) > 1024 ||
            wcslen(name) > 256 || wcslen(expected) > 32766) return 0;
    REGSAM access = KEY_QUERY_VALUE | KEY_WOW64_64KEY | (action ? KEY_SET_VALUE : 0);
    LSTATUS error = RegOpenKeyExW(HKEY_CURRENT_USER, path, 0, access, &key);
    if (error == ERROR_FILE_NOT_FOUND && action == 1)
        error = RegCreateKeyExW(HKEY_CURRENT_USER, path, 0, NULL, 0, access, NULL, &key, NULL);
    if (error == ERROR_FILE_NOT_FOUND) return 1;
    if (error != ERROR_SUCCESS) return 0;
    DWORD kind = 0, length = 0;
    error = RegQueryValueExW(key, name, NULL, &kind, NULL, &length);
    if (error == ERROR_FILE_NOT_FOUND) result = 1;
    else if (error != ERROR_SUCCESS) goto done;
    else {
        if (kind != REG_SZ || length < sizeof(wchar_t) || length > 65534 || length % sizeof(wchar_t)) {
            result = 3; goto done;
        }
        value = calloc(1, length + sizeof(wchar_t));
        if (!value) goto done;
        error = RegQueryValueExW(key, name, NULL, &kind, (BYTE *)value, &length);
        if (error != ERROR_SUCCESS) goto done;
        if (kind != REG_SZ || length < sizeof(wchar_t) || length % sizeof(wchar_t) ||
                value[length / sizeof(wchar_t) - 1] ||
                (wcslen(value) + 1) * sizeof(wchar_t) != length || wcscmp(value, expected)) {
            result = 3; goto done;
        }
        result = 2;
    }
    if (action == 1 && result == 1) {
        if (RegSetValueExW(key, name, 0, REG_SZ, (const BYTE *)expected,
                (DWORD)((wcslen(expected) + 1) * sizeof(wchar_t))) != ERROR_SUCCESS ||
                RegFlushKey(key) != ERROR_SUCCESS) result = 0;
        else result = 2;
    } else if (action == 2 && result == 2) {
        if (RegDeleteValueW(key, name) != ERROR_SUCCESS || RegFlushKey(key) != ERROR_SUCCESS) result = 0;
    }
done:
    free(value); if (key) RegCloseKey(key); return result;
}

/* Keep a private browser manifest unchanged while Inno hashes it and removes
 * its matching registry pointers. No application Python or JSON parser runs
 * in the uninstaller, and persistent browser/user files are not deleted. */
__declspec(dllexport) BOOL WINAPI AugmentorRetainManifest(const wchar_t *path) {
    HANDLE token = NULL, file = INVALID_HANDLE_VALUE, parent = INVALID_HANDLE_VALUE;
    TOKEN_USER *identity = NULL; DWORD size = 0; BOOL accepted = FALSE;
    wchar_t directory[32768];
    if ((installation == INVALID_HANDLE_VALUE && manual.file == INVALID_HANDLE_VALUE) ||
            manifest_file != INVALID_HANDLE_VALUE || !path) return FALSE;
    DWORD length = GetFullPathNameW(path, 32768, directory, NULL);
    if (!length || length >= 32768) return FALSE;
    wchar_t *slash = wcsrchr(directory, L'\\');
    if (!slash) return FALSE;
    *slash = 0;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) goto done;
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    if (!size || !(identity = malloc(size)) ||
            !GetTokenInformation(token, TokenUser, identity, size, &size)) goto done;
    parent = augmentor_private_directory(directory, identity->User.Sid, NULL, FALSE);
    if (parent == INVALID_HANDLE_VALUE) goto done;
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    BY_HANDLE_FILE_INFORMATION info; LARGE_INTEGER length_bytes;
    if (file == INVALID_HANDLE_VALUE || !GetFileInformationByHandle(file, &info) ||
            !GetFileSizeEx(file, &length_bytes) || length_bytes.QuadPart < 1 || length_bytes.QuadPart > 65536 ||
            info.nNumberOfLinks != 1 || info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) ||
            !augmentor_private_descriptor(file, identity->User.Sid)) goto done;
    manifest_file = file; file = INVALID_HANDLE_VALUE;
    manifest_parent = parent; parent = INVALID_HANDLE_VALUE;
    accepted = TRUE;
done:
    if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
    if (parent != INVALID_HANDLE_VALUE) CloseHandle(parent);
    if (token) CloseHandle(token);
    free(identity); return accepted;
}

#include "windows-installer-inspection.h"
