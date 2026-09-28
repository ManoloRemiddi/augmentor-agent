/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Preserve exact installer bytes before changing application files. This is
 * byte retention, not publisher authentication or permission to roll back.
 * Included after the maintenance handles in windows-installer-handoff.c.
 */
#include <bcrypt.h>

static HANDLE cache_directory = INVALID_HANDLE_VALUE;
static HANDLE cache_installer = INVALID_HANDLE_VALUE, cache_receipt = INVALID_HANDLE_VALUE;

static void augmentor_cache_close(void) {
    if (cache_receipt != INVALID_HANDLE_VALUE) CloseHandle(cache_receipt);
    if (cache_installer != INVALID_HANDLE_VALUE) CloseHandle(cache_installer);
    if (cache_directory != INVALID_HANDLE_VALUE) CloseHandle(cache_directory);
    cache_directory = cache_installer = cache_receipt = INVALID_HANDLE_VALUE;
}

static BOOL cache_digest(const wchar_t *value) {
    if (!value || wcslen(value) != 64) return FALSE;
    for (unsigned i = 0; i < 64; ++i)
        if (!((value[i] >= L'0' && value[i] <= L'9') || (value[i] >= L'a' && value[i] <= L'f'))) return FALSE;
    return TRUE;
}

static BOOL cache_file(HANDLE file, PSID user, BOOL private_file, LONGLONG maximum) {
    BY_HANDLE_FILE_INFORMATION info; LARGE_INTEGER size;
    return file != INVALID_HANDLE_VALUE && GetFileType(file) == FILE_TYPE_DISK &&
        GetFileInformationByHandle(file, &info) && GetFileSizeEx(file, &size) &&
        size.QuadPart > 0 && size.QuadPart <= maximum && info.nNumberOfLinks == 1 &&
        !(info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) &&
        (!private_file || augmentor_private_descriptor(file, user));
}

/* Hash and optionally copy the already pinned handle, never reopen its name. */
static BOOL cache_stream(HANDLE source, HANDLE destination, const wchar_t *expected) {
    BCRYPT_ALG_HANDLE algorithm = NULL; BCRYPT_HASH_HANDLE hash = NULL;
    BYTE *buffer = malloc(1024 * 1024), digest[32];
    DWORD count, written; LARGE_INTEGER zero = {0}; BOOL ok = FALSE;
    wchar_t observed[65];
    if (!buffer || !SetFilePointerEx(source, zero, NULL, FILE_BEGIN) ||
            BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0) < 0 ||
            BCryptCreateHash(algorithm, &hash, NULL, 0, NULL, 0, 0) < 0) goto done;
    for (;;) {
        if (!ReadFile(source, buffer, 1024 * 1024, &count, NULL)) goto done;
        if (!count) break;
        if (BCryptHashData(hash, buffer, count, 0) < 0) goto done;
        if (destination != INVALID_HANDLE_VALUE &&
                (!WriteFile(destination, buffer, count, &written, NULL) || written != count)) goto done;
    }
    if (BCryptFinishHash(hash, digest, sizeof(digest), 0) < 0) goto done;
    for (unsigned i = 0; i < 32; ++i) swprintf_s(observed + 2*i, 65 - 2*i, L"%02x", digest[i]);
    ok = !wcscmp(observed, expected);
    if (ok && destination != INVALID_HANDLE_VALUE) ok = FlushFileBuffers(destination);
done:
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
    free(buffer); return ok;
}

/* Create/flush/rename only a fresh random sibling; never replace an existing
 * retained installer or receipt. An interrupted pending file is not selected. */
static BOOL cache_publish(const wchar_t *directory, const wchar_t *target,
        SECURITY_ATTRIBUTES *security, HANDLE source, const wchar_t *digest,
        const BYTE *content, DWORD length) {
    BYTE nonce[16]; wchar_t suffix[33], temporary[32768];
    HANDLE file = INVALID_HANDLE_VALUE; BOOL created = FALSE, ok = FALSE; DWORD written;
    if (BCryptGenRandom(NULL, nonce, sizeof(nonce), BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) return FALSE;
    for (unsigned i = 0; i < 16; ++i) swprintf_s(suffix + 2*i, 33 - 2*i, L"%02x", nonce[i]);
    if (swprintf_s(temporary, 32768, L"\\\\?\\%ls\\pending-%ls.tmp", directory, suffix) < 0) return FALSE;
    file = CreateFileW(temporary, GENERIC_READ | GENERIC_WRITE, 0, security, CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (file == INVALID_HANDLE_VALUE) goto done;
    created = TRUE;
    if (source != INVALID_HANDLE_VALUE) ok = cache_stream(source, file, digest);
    else ok = WriteFile(file, content, length, &written, NULL) && written == length && FlushFileBuffers(file);
    CloseHandle(file); file = INVALID_HANDLE_VALUE;
    if (ok) ok = MoveFileExW(temporary, target, MOVEFILE_WRITE_THROUGH);
done:
    if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
    if (!ok && created) DeleteFileW(temporary); /* Only this call's unpublished file. */
    return ok;
}

__declspec(dllexport) BOOL WINAPI AugmentorRetainInstaller(const wchar_t *source_path,
        const wchar_t *installer_digest, const wchar_t *release_digest) {
    HANDLE token = NULL, source = INVALID_HANDLE_VALUE, base = INVALID_HANDLE_VALUE;
    TOKEN_USER *identity = NULL; DWORD size = 0, count; wchar_t *sid = NULL;
    PSECURITY_DESCRIPTOR security = NULL; BOOL ok = FALSE;
    wchar_t directory[32768], installer_path[32768], receipt_path[32768], sddl[512];
    BYTE receipt[64], observed[65]; DWORD read;
    if ((installation == INVALID_HANDLE_VALUE && manual.file == INVALID_HANDLE_VALUE) ||
            cache_directory != INVALID_HANDLE_VALUE || !source_path ||
            !cache_digest(installer_digest) || !cache_digest(release_digest)) return FALSE;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) goto done;
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    if (!size || !(identity = malloc(size)) || !GetTokenInformation(token, TokenUser, identity, size, &size) ||
            !ConvertSidToStringSidW(identity->User.Sid, &sid)) goto done;
    /* Derive the cache only from the already validated private maintenance
     * handle. No download, environment value or installer switch chooses it. */
    count = GetFinalPathNameByHandleW(manual.base != INVALID_HANDLE_VALUE ? manual.base : runtime,
        directory, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!count || count >= 32768 || wcsncmp(directory, L"\\\\?\\", 4)) goto done;
    memmove(directory, directory + 4, (count - 3) * sizeof(wchar_t));
    if (manual.base == INVALID_HANDLE_VALUE) {
        wchar_t *slash = wcsrchr(directory, L'\\');
        if (!slash || _wcsicmp(slash, L"\\run")) goto done;
        *slash = 0;
    }
    base = augmentor_private_directory(directory, identity->User.Sid, NULL, FALSE);
    if (base == INVALID_HANDLE_VALUE || wcscat_s(directory, 32768, L"\\recovery")) goto done;
    if (swprintf_s(sddl, 512, L"O:%lsD:P(A;OICI;FA;;;%ls)(A;OICI;FA;;;SY)", sid, sid) < 0 ||
            !ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &security, NULL)) goto done;
    SECURITY_ATTRIBUTES attributes = {sizeof(attributes), security, FALSE};
    cache_directory = augmentor_private_directory(directory, identity->User.Sid, &attributes, TRUE);
    if (cache_directory == INVALID_HANDLE_VALUE ||
            swprintf_s(installer_path, 32768, L"\\\\?\\%ls\\%ls.exe", directory, installer_digest) < 0 ||
            swprintf_s(receipt_path, 32768, L"\\\\?\\%ls\\%ls.release", directory, installer_digest) < 0) goto done;
    LocalFree(security); security = NULL;
    if (swprintf_s(sddl, 512, L"O:%lsD:P(A;;FA;;;%ls)(A;;FA;;;SY)", sid, sid) < 0 ||
            !ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &security, NULL)) goto done;
    attributes.lpSecurityDescriptor = security;
    source = CreateFileW(source_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (!cache_file(source, identity->User.Sid, FALSE, 2146435072)) goto done;
    cache_installer = CreateFileW(installer_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (cache_installer == INVALID_HANDLE_VALUE) {
        if (GetLastError() != ERROR_FILE_NOT_FOUND ||
                !cache_publish(directory, installer_path, &attributes, source, installer_digest, NULL, 0)) goto done;
        cache_installer = CreateFileW(installer_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
            FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    } else if (!cache_stream(source, INVALID_HANDLE_VALUE, installer_digest)) goto done;
    if (!cache_file(cache_installer, identity->User.Sid, TRUE, 2146435072) ||
            !cache_stream(cache_installer, INVALID_HANDLE_VALUE, installer_digest)) goto done;
    for (unsigned i = 0; i < 64; ++i) receipt[i] = (BYTE)release_digest[i];
    cache_receipt = CreateFileW(receipt_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (cache_receipt == INVALID_HANDLE_VALUE) {
        if (GetLastError() != ERROR_FILE_NOT_FOUND ||
                !cache_publish(directory, receipt_path, &attributes, INVALID_HANDLE_VALUE, NULL, receipt, 64)) goto done;
        cache_receipt = CreateFileW(receipt_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
            FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    }
    if (!cache_file(cache_receipt, identity->User.Sid, TRUE, 64) ||
            !ReadFile(cache_receipt, observed, 65, &read, NULL) || read != 64 || memcmp(receipt, observed, 64)) goto done;
    ok = TRUE;
done:
    if (source != INVALID_HANDLE_VALUE) CloseHandle(source);
    if (base != INVALID_HANDLE_VALUE) CloseHandle(base);
    if (token) CloseHandle(token);
    if (security) LocalFree(security);
    if (sid) LocalFree(sid);
    free(identity);
    if (!ok) augmentor_cache_close();
    return ok;
}
