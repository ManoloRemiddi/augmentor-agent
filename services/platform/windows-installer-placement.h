/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Preserve an owned installation's old payload before authenticated replacement.
 * Original update bytes stay unresolved; no replay, rollback or pruning here.
 */
#include <stdio.h>
static HANDLE placement_base = INVALID_HANDLE_VALUE, placement_updates = INVALID_HANDLE_VALUE;
static HANDLE placement_writer = INVALID_HANDLE_VALUE, placement_record = INVALID_HANDLE_VALUE;
static HANDLE placement_backups = INVALID_HANDLE_VALUE, placement_attempt = INVALID_HANDLE_VALUE;
static BOOL placement_attempted = FALSE, placement_ready = FALSE;

static void augmentor_placement_close(void) {
    HANDLE *handles[] = {&placement_record, &placement_writer, &placement_updates,
        &placement_attempt, &placement_backups, &placement_base};
    for (unsigned i = 0; i < sizeof(handles)/sizeof(handles[0]); ++i) {
        if (*handles[i] != INVALID_HANDLE_VALUE) CloseHandle(*handles[i]);
        *handles[i] = INVALID_HANDLE_VALUE;
    }
    placement_attempted = placement_ready = FALSE;
}

__declspec(dllexport) BOOL WINAPI AugmentorPrepareReplacement(const wchar_t *application) {
    typedef struct {
        wchar_t base[32768], updates[32768], backups[32768], attempt[32768];
        wchar_t path[32768], current[32768], displaced[32768];
    } PlacementPaths;
    PlacementPaths *paths = NULL;
    PSID user = NULL; PSECURITY_DESCRIPTOR base_security = NULL, directory_security = NULL, file_security = NULL;
    wchar_t digest[65], nonce[33], sddl[512], *sid = NULL;
    BYTE random[16]; char receipt[1024]; DWORD count, length, attributes;
    BOOL ok = FALSE, existed = FALSE;
    if (!authorized || installation == INVALID_HANDLE_VALUE || startup == INVALID_HANDLE_VALUE ||
            runtime == INVALID_HANDLE_VALUE || cache_installer == INVALID_HANDLE_VALUE ||
            cache_receipt == INVALID_HANDLE_VALUE || !cache_selection_valid(cache_selection_after) ||
            !application || !AugmentorMaintenancePath(application)) return FALSE;
    if (placement_attempted) return placement_ready;
    placement_attempted = TRUE;
    paths = calloc(1, sizeof(*paths));
    if (!paths) goto done;
    wchar_t *base = paths->base, *updates = paths->updates, *backups = paths->backups;
    wchar_t *attempt = paths->attempt, *path = paths->path;
    wchar_t *current = paths->current, *displaced = paths->displaced;
    if (GetSecurityInfo(runtime, SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION,
            &user, NULL, NULL, NULL, &base_security) != ERROR_SUCCESS) goto done;
    count = GetFinalPathNameByHandleW(runtime, base, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!count || count >= 32768 || wcsncmp(base, L"\\\\?\\", 4)) goto done;
    memmove(base, base + 4, (count - 3) * sizeof(wchar_t));
    wchar_t *slash = wcsrchr(base, L'\\');
    if (!slash || _wcsicmp(slash, L"\\run")) goto done;
    *slash = 0;
    placement_base = augmentor_private_directory(base, user, NULL, FALSE);
    if (placement_base == INVALID_HANDLE_VALUE ||
            swprintf_s(updates, 32768, L"%ls\\updates", base) < 0) goto done;
    placement_updates = augmentor_private_directory(updates, user, NULL, FALSE);
    if (placement_updates == INVALID_HANDLE_VALUE ||
            swprintf_s(path, 32768, L"%ls\\writer.lock", updates) < 0) goto done;
    placement_writer = CreateFileW(path, GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    BY_HANDLE_FILE_INFORMATION info;
    if (placement_writer == INVALID_HANDLE_VALUE || GetFileType(placement_writer) != FILE_TYPE_DISK ||
            !GetFileInformationByHandle(placement_writer, &info) || info.nNumberOfLinks != 1 ||
            info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) ||
            !augmentor_private_descriptor(placement_writer, user)) goto done;
    OVERLAPPED operation = {0};
    if (!LockFileEx(placement_writer, LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY,
            0, 1, 0, &operation) || swprintf_s(path, 32768, L"%ls\\active.json", updates) < 0) goto done;
    placement_record = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (!cache_file(placement_record, user, TRUE, 65536) ||
            !cache_stream_digest(placement_record, INVALID_HANDLE_VALUE, NULL, digest) ||
            !ConvertSidToStringSidW(user, &sid) ||
            swprintf_s(sddl, 512, L"O:%lsD:P(A;OICI;FA;;;%ls)(A;OICI;FA;;;SY)", sid, sid) < 0 ||
            !ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &directory_security, NULL)) goto done;
    SECURITY_ATTRIBUTES directory_attributes = {sizeof(directory_attributes), directory_security, FALSE};
    if (swprintf_s(backups, 32768, L"%ls\\payload-backups", base) < 0) goto done;
    placement_backups = augmentor_private_directory(backups, user, &directory_attributes, TRUE);
    if (placement_backups == INVALID_HANDLE_VALUE ||
            BCryptGenRandom(NULL, random, sizeof(random), BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) goto done;
    for (unsigned i = 0; i < 16; ++i) swprintf_s(nonce + 2*i, 33 - 2*i, L"%02x", random[i]);
    if (swprintf_s(attempt, 32768, L"%ls\\%ls", backups, nonce) < 0 ||
            !CreateDirectoryW(attempt, &directory_attributes)) goto done;
    placement_attempt = augmentor_private_directory(attempt, user, NULL, FALSE);
    if (placement_attempt == INVALID_HANDLE_VALUE ||
            swprintf_s(sddl, 512, L"O:%lsD:P(A;;FA;;;%ls)(A;;FA;;;SY)", sid, sid) < 0 ||
            !ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &file_security, NULL)) goto done;
    SECURITY_ATTRIBUTES file_attributes = {sizeof(file_attributes), file_security, FALSE};
    count = GetFullPathNameW(application, 32768, path, NULL);
    if (!count || count >= 32768 ||
            swprintf_s(current, 32768, L"\\\\?\\%ls\\current", path) < 0 ||
            swprintf_s(displaced, 32768, L"\\\\?\\%ls\\payload", attempt) < 0) goto done;
    attributes = GetFileAttributesW(current);
    if (attributes == INVALID_FILE_ATTRIBUTES) {
        DWORD error = GetLastError();
        if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND) goto done;
    } else {
        if (!(attributes & FILE_ATTRIBUTE_DIRECTORY) || attributes & FILE_ATTRIBUTE_REPARSE_POINT) goto done;
        existed = TRUE;
    }
    if (swprintf_s(path, 32768, L"\\\\?\\%ls\\update.json", attempt) < 0 ||
            !cache_publish(attempt, path, &file_attributes, placement_record, digest, NULL, 0, FALSE)) goto done;
    /* Restricted ASCII identifiers only; neither paths nor saved process commands
     * become native instructions. This record describes this fresh attempt. */
    const size_t prefix = sizeof(CACHE_SELECTION_PREFIX) - 1;
    int formatted = sprintf_s(receipt, sizeof(receipt),
        "{\"schema\":\"augmentor-payload-placement/1\",\"attempt\":\"%ls\","
        "\"recordSHA256\":\"%ls\",\"installerSHA256\":\"%.*s\",\"releaseSHA256\":\"%.*s\",\"hadPayload\":%s}\n",
        nonce, digest, 64, (char *)cache_selection_after + prefix,
        64, (char *)cache_selection_after + prefix + 65, existed ? "true" : "false");
    if (formatted < 1) goto done;
    length = (DWORD)formatted;
    if (swprintf_s(path, 32768, L"\\\\?\\%ls\\intent.json", attempt) < 0 ||
            !cache_publish(attempt, path, &file_attributes, INVALID_HANDLE_VALUE, NULL,
                (BYTE *)receipt, length, FALSE)) goto done;
    /* Same-volume rename only: no copy/delete fallback, replacement, scheduling
     * for reboot, recursive deletion, or automatic retry after an unknown result.
     * Existing descendant ACLs remain their own; the private parent is not a
     * claim that every displaced file acquired a new security descriptor. */
    if (existed && !MoveFileExW(current, displaced, MOVEFILE_WRITE_THROUGH)) goto done;
    if (swprintf_s(path, 32768, L"\\\\?\\%ls\\prepared.json", attempt) < 0 ||
            !cache_publish(attempt, path, &file_attributes, INVALID_HANDLE_VALUE, NULL,
                (BYTE *)receipt, length, FALSE)) goto done;
    placement_ready = ok = TRUE;
done:
    if (file_security) LocalFree(file_security);
    if (directory_security) LocalFree(directory_security);
    if (base_security) LocalFree(base_security);
    if (sid) LocalFree(sid);
    free(paths);
    /* Retain every acquired admission/pin until Setup closes, including failures.
     * Preserve all attempt files and any displaced payload for fresh inspection. */
    return ok;
}
