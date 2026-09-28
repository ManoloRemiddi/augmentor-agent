/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Acquire the application's lifetime lease BEFORE loading private runtime DLLs.
 * The byte-zero lock matches platform_adapters/locks.py. No inherited paths,
 * persistent maintenance flag, process termination or credential access here.
 */
#ifndef AUGMENTOR_WINDOWS_LEASE_H
#define AUGMENTOR_WINDOWS_LEASE_H
#include <stdlib.h>
#include <aclapi.h>
#include <sddl.h>
#include <shlobj.h>

typedef struct {
    HANDLE base, run, file;
} AugmentorLease;

static void augmentor_release(AugmentorLease *lease) {
    if (lease->file != INVALID_HANDLE_VALUE) CloseHandle(lease->file);
    if (lease->run != INVALID_HANDLE_VALUE) CloseHandle(lease->run);
    if (lease->base != INVALID_HANDLE_VALUE) CloseHandle(lease->base);
    lease->file = lease->run = lease->base = INVALID_HANDLE_VALUE;
}

static BOOL augmentor_private_descriptor(HANDLE handle, PSID user) {
    PSID owner = NULL;
    PACL acl = NULL;
    PSECURITY_DESCRIPTOR security = NULL;
    SECURITY_DESCRIPTOR_CONTROL control;
    DWORD revision;
    BOOL accepted = FALSE, user_access = FALSE;
    if (GetSecurityInfo(handle, SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
            &owner, NULL, &acl, NULL, &security) != ERROR_SUCCESS) return FALSE;
    if (!owner || !EqualSid(owner, user) || !acl ||
            !GetSecurityDescriptorControl(security, &control, &revision) ||
            !(control & SE_DACL_PROTECTED)) goto done;
    for (DWORD i = 0; i < acl->AceCount; ++i) {
        ACCESS_ALLOWED_ACE *ace = NULL;
        if (!GetAce(acl, i, (void **)&ace) || ace->Header.AceType != ACCESS_ALLOWED_ACE_TYPE)
            goto done;
        PSID sid = &ace->SidStart;
        if (!EqualSid(sid, user) && !IsWellKnownSid(sid, WinLocalSystemSid)) goto done;
        if (EqualSid(sid, user) && !(ace->Header.AceFlags & INHERIT_ONLY_ACE) &&
                (ace->Mask & FILE_ALL_ACCESS) == FILE_ALL_ACCESS) user_access = TRUE;
    }
    accepted = user_access;
done:
    LocalFree(security);
    return accepted;
}

/* Ordinary absolute local paths only. Keep owned directory handles open without
 * delete sharing; an installer cannot rename those directories under the lease. */
static BOOL augmentor_plain_ancestors(const wchar_t *path) {
    wchar_t check[32768];
    size_t length = wcslen(path);
    if (length < 3 || length >= 32768 || path[1] != L':' || path[2] != L'\\' ||
            wcschr(path + 2, L':')) return FALSE;
    if (wcscpy_s(check, 32768, path)) return FALSE;
    for (size_t i = 3; i <= length; ++i) {
        if (i < length && check[i] != L'\\') continue;
        wchar_t saved = check[i]; check[i] = 0;
        DWORD attributes = GetFileAttributesW(check);
        check[i] = saved;
        if (attributes == INVALID_FILE_ATTRIBUTES ||
                attributes & FILE_ATTRIBUTE_REPARSE_POINT ||
                !(attributes & FILE_ATTRIBUTE_DIRECTORY)) return FALSE;
    }
    return TRUE;
}

static HANDLE augmentor_private_directory(const wchar_t *path, PSID user,
        SECURITY_ATTRIBUTES *attributes, BOOL create) {
    wchar_t parent[32768];
    if (wcscpy_s(parent, 32768, path)) return INVALID_HANDLE_VALUE;
    wchar_t *slash = wcsrchr(parent, L'\\');
    if (!slash || slash <= parent + 2) return INVALID_HANDLE_VALUE;
    *slash = 0;
    if (!augmentor_plain_ancestors(parent)) return INVALID_HANDLE_VALUE;
    if (create && !CreateDirectoryW(path, attributes) && GetLastError() != ERROR_ALREADY_EXISTS)
        return INVALID_HANDLE_VALUE;
    if (!augmentor_plain_ancestors(path)) return INVALID_HANDLE_VALUE;
    HANDLE handle = CreateFileW(path, READ_CONTROL | FILE_READ_ATTRIBUTES,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (handle == INVALID_HANDLE_VALUE) return handle;
    BY_HANDLE_FILE_INFORMATION info;
    if (!GetFileInformationByHandle(handle, &info) ||
            !(info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) ||
            info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT ||
            !augmentor_private_descriptor(handle, user)) {
        CloseHandle(handle); return INVALID_HANDLE_VALUE;
    }
    return handle;
}

/* qualification is supplied only by a development-candidate build. Its existing
 * private root is verified, never created or inferred from environment values. */
static BOOL augmentor_acquire(AugmentorLease *lease, const wchar_t *qualification) {
    HANDLE token = NULL;
    TOKEN_USER *identity = NULL;
    wchar_t *sid = NULL;
    PSECURITY_DESCRIPTOR security = NULL;
    DWORD size = 0;
    BOOL accepted = FALSE;
    wchar_t base[32768], run[32768], file[32768], sddl[512];
    lease->base = lease->run = lease->file = INVALID_HANDLE_VALUE;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) goto done;
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    if (!size || !(identity = malloc(size)) ||
            !GetTokenInformation(token, TokenUser, identity, size, &size) ||
            !ConvertSidToStringSidW(identity->User.Sid, &sid)) goto done;
    if (swprintf_s(sddl, 512, L"O:%lsD:P(A;OICI;FA;;;%ls)(A;OICI;FA;;;SY)", sid, sid) < 0 ||
            !ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &security, NULL))
        goto done;
    SECURITY_ATTRIBUTES attributes = {sizeof(attributes), security, FALSE};
    if (qualification) {
        DWORD count = GetFullPathNameW(qualification, 32768, base, NULL);
        if (!count || count >= 32768) goto done;
    } else {
        wchar_t local[MAX_PATH];
        if (FAILED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, SHGFP_TYPE_CURRENT, local)) ||
                swprintf_s(base, 32768, L"%ls\\Augmentor", local) < 0) goto done;
    }
    lease->base = augmentor_private_directory(base, identity->User.Sid, &attributes, !qualification);
    if (lease->base == INVALID_HANDLE_VALUE ||
            swprintf_s(run, 32768, L"%ls\\run", base) < 0) goto done;
    lease->run = augmentor_private_directory(run, identity->User.Sid, &attributes, TRUE);
    if (lease->run == INVALID_HANDLE_VALUE ||
            swprintf_s(file, 32768, L"%ls\\installation.lock", run) < 0) goto done;
    /* Files have no inherited access. Match Python's protected current-user
     * owner even when launched from an elevated administrator test session. */
    LocalFree(security); security = NULL;
    if (swprintf_s(sddl, 512, L"O:%lsD:P(A;;FA;;;%ls)(A;;FA;;;SY)", sid, sid) < 0 ||
            !ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &security, NULL))
        goto done;
    attributes.lpSecurityDescriptor = security;
    lease->file = CreateFileW(file, GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, &attributes, OPEN_ALWAYS,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (lease->file == INVALID_HANDLE_VALUE) goto done;
    BY_HANDLE_FILE_INFORMATION info;
    if (!GetFileInformationByHandle(lease->file, &info) || info.nNumberOfLinks != 1 ||
            info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) ||
            !augmentor_private_descriptor(lease->file, identity->User.Sid)) goto done;
    OVERLAPPED overlap = {0};
    accepted = LockFileEx(lease->file, LOCKFILE_FAIL_IMMEDIATELY, 0, 1, 0, &overlap);
done:
    if (security) LocalFree(security);
    if (sid) LocalFree(sid);
    free(identity);
    if (token) CloseHandle(token);
    if (!accepted) augmentor_release(lease);
    return accepted;
}
#endif
