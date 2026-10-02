/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Read-only independent payload inspection. Included after plain_tree and the
 * cache helpers. Only this call's never-installed worker Job can be terminated.
 */
static HANDLE inspection_parent = INVALID_HANDLE_VALUE;
static HANDLE inspection_root = INVALID_HANDLE_VALUE;
static HANDLE inspection_report = INVALID_HANDLE_VALUE;
static HANDLE inspection_updates = INVALID_HANDLE_VALUE;
static HANDLE inspection_writer = INVALID_HANDLE_VALUE, inspection_record = INVALID_HANDLE_VALUE;
static wchar_t inspection_path[32768];
static wchar_t inspection_installer[65];
static DWORD inspection_stage = 0, inspection_detail = 0;
static BOOL inspection_health_attempted = FALSE;
static BOOL inspection_source_verified = FALSE;
static wchar_t inspection_release[65];

__declspec(dllexport) DWORD WINAPI AugmentorInspectionStage(void) { return inspection_stage; }
__declspec(dllexport) DWORD WINAPI AugmentorInspectionDetail(void) { return inspection_detail; }

static void augmentor_inspection_close(void) {
    if (inspection_record != INVALID_HANDLE_VALUE) CloseHandle(inspection_record);
    if (inspection_writer != INVALID_HANDLE_VALUE) CloseHandle(inspection_writer);
    if (inspection_updates != INVALID_HANDLE_VALUE) CloseHandle(inspection_updates);
    inspection_record = inspection_writer = inspection_updates = INVALID_HANDLE_VALUE;
    inspection_installer[0] = 0;
    inspection_health_attempted = FALSE;
    inspection_source_verified = FALSE;
    inspection_release[0] = 0;
    if (inspection_report != INVALID_HANDLE_VALUE) CloseHandle(inspection_report);
    if (inspection_root != INVALID_HANDLE_VALUE) CloseHandle(inspection_root);
    if (inspection_parent != INVALID_HANDLE_VALUE) CloseHandle(inspection_parent);
    inspection_report = inspection_root = inspection_parent = INVALID_HANDLE_VALUE;
    inspection_path[0] = 0;
}

/* Anchor extraction to the temporary directory containing this loaded Inno
 * helper. Create fresh protected directories before Inno extracts any code.
 * Existing paths, including another private directory, are never adopted. */
__declspec(dllexport) BOOL WINAPI AugmentorInspectionPrepare(const wchar_t *temporary) {
    HMODULE module = NULL; HANDLE token = NULL;
    TOKEN_USER *identity = NULL; DWORD size = 0;
    wchar_t actual[32768], expected[32768], parent[32768], sddl[512], *sid = NULL;
    PSECURITY_DESCRIPTOR security = NULL; BOOL ok = FALSE;
    if (manual.file == INVALID_HANDLE_VALUE || authorized || !temporary ||
            inspection_parent != INVALID_HANDLE_VALUE) return FALSE;
    DWORD count = GetFullPathNameW(temporary, 32768, expected, NULL);
    if (!count || count >= 32768 || !augmentor_plain_ancestors(expected) ||
            !GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                (LPCWSTR)&AugmentorInspectionPrepare, &module)) return FALSE;
    count = GetModuleFileNameW(module, actual, 32768);
    if (!count || count >= 32768) return FALSE;
    wchar_t *slash = wcsrchr(actual, L'\\');
    if (!slash) return FALSE;
    *slash = 0;
    if (_wcsicmp(actual, expected) ||
            swprintf_s(parent, 32768, L"%ls\\{app}", expected) < 0 ||
            swprintf_s(inspection_path, 32768, L"%ls\\current", parent) < 0) return FALSE;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) goto done;
    GetTokenInformation(token, TokenUser, NULL, 0, &size);
    if (!size || !(identity = malloc(size)) ||
            !GetTokenInformation(token, TokenUser, identity, size, &size) ||
            !ConvertSidToStringSidW(identity->User.Sid, &sid) ||
            swprintf_s(sddl, 512, L"O:%lsD:P(A;OICI;FA;;;%ls)(A;OICI;FA;;;SY)", sid, sid) < 0 ||
            !ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &security, NULL)) goto done;
    SECURITY_ATTRIBUTES attributes = {sizeof(attributes), security, FALSE};
    if (!CreateDirectoryW(parent, &attributes)) goto done;
    inspection_parent = augmentor_private_directory(parent, identity->User.Sid, NULL, FALSE);
    if (inspection_parent == INVALID_HANDLE_VALUE || !CreateDirectoryW(inspection_path, &attributes)) goto done;
    inspection_root = augmentor_private_directory(inspection_path, identity->User.Sid, NULL, FALSE);
    ok = inspection_root != INVALID_HANDLE_VALUE;
done:
    if (security) LocalFree(security);
    if (sid) LocalFree(sid);
    if (token) CloseHandle(token);
    free(identity);
    if (!ok) augmentor_inspection_close();
    return ok;
}

/* Snapshot only the canonical private active record while holding its live
 * writer lock and denying record writes/deletion. This does not create a new
 * writer file, infer liveness from saved PIDs, or change persistent state. */
__declspec(dllexport) BOOL WINAPI AugmentorInspectionSnapshot(const wchar_t *installer_digest) {
    PSID user = NULL; PSECURITY_DESCRIPTOR base_security = NULL, record_security = NULL;
    HANDLE copy = INVALID_HANDLE_VALUE; BOOL ok = FALSE;
    wchar_t directory[32768], path[32768]; BYTE *content = NULL;
    DWORD count = 0, written = 0;
    if (manual.base == INVALID_HANDLE_VALUE || manual.file == INVALID_HANDLE_VALUE || authorized ||
            inspection_root == INVALID_HANDLE_VALUE || inspection_writer != INVALID_HANDLE_VALUE ||
            inspection_record != INVALID_HANDLE_VALUE || !cache_digest(installer_digest)) return FALSE;
    if (GetSecurityInfo(manual.base, SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION,
            &user, NULL, NULL, NULL, &base_security) != ERROR_SUCCESS) goto done;
    count = GetFinalPathNameByHandleW(manual.base, directory, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!count || count >= 32768 || wcsncmp(directory, L"\\\\?\\", 4)) goto done;
    memmove(directory, directory + 4, (count - 3) * sizeof(wchar_t));
    if (wcscat_s(directory, 32768, L"\\updates")) goto done;
    inspection_updates = augmentor_private_directory(directory, user, NULL, FALSE);
    if (inspection_updates == INVALID_HANDLE_VALUE ||
            swprintf_s(path, 32768, L"%ls\\writer.lock", directory) < 0) goto done;
    inspection_writer = CreateFileW(path, GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    BY_HANDLE_FILE_INFORMATION info;
    if (inspection_writer == INVALID_HANDLE_VALUE || GetFileType(inspection_writer) != FILE_TYPE_DISK ||
            !GetFileInformationByHandle(inspection_writer, &info) || info.nNumberOfLinks != 1 ||
            info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) ||
            !augmentor_private_descriptor(inspection_writer, user)) goto done;
    OVERLAPPED operation = {0};
    if (!LockFileEx(inspection_writer, LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY,
            0, 1, 0, &operation) || swprintf_s(path, 32768, L"%ls\\active.json", directory) < 0) goto done;
    inspection_record = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (!cache_file(inspection_record, user, TRUE, 65536) ||
            GetSecurityInfo(inspection_record, SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
                NULL, NULL, NULL, NULL, &record_security) != ERROR_SUCCESS) goto done;
    content = malloc(65537);
    if (!content || !ReadFile(inspection_record, content, 65537, &count, NULL) || !count || count > 65536 ||
            swprintf_s(path, 32768, L"%ls\\recovery-record.json", inspection_path) < 0) goto done;
    SECURITY_ATTRIBUTES attributes = {sizeof(attributes), record_security, FALSE};
    copy = CreateFileW(path, GENERIC_WRITE, 0, &attributes, CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (copy == INVALID_HANDLE_VALUE || !WriteFile(copy, content, count, &written, NULL) ||
            written != count || !FlushFileBuffers(copy) ||
            wcscpy_s(inspection_installer, 65, installer_digest)) goto done;
    ok = TRUE;
done:
    if (copy != INVALID_HANDLE_VALUE) CloseHandle(copy);
    if (record_security) LocalFree(record_security);
    if (base_security) LocalFree(base_security);
    free(content);
    /* Every retained handle, including a refused snapshot, is released by the
     * caller's existing finally block. It cannot be reused as an authority. */
    return ok;
}

static BOOL inspection_worker(const wchar_t *installed, const wchar_t *release_digest,
        BOOL health, const wchar_t *qualification) {
    HANDLE metadata = INVALID_HANDLE_VALUE, job = NULL;
    PROCESS_INFORMATION process = {0}; STARTUPINFOW startup_info = {sizeof(startup_info)};
    wchar_t executable[32768], script[32768], path[32768], *command = NULL;
    BOOL ok = FALSE, started = FALSE; DWORD code = 74;
    unsigned remaining = 250000;
    inspection_stage = 1; inspection_detail = 0;
    if (manual.file == INVALID_HANDLE_VALUE || authorized || inspection_root == INVALID_HANDLE_VALUE ||
            inspection_report != INVALID_HANDLE_VALUE || !installed || wcschr(installed, L'"') ||
            !cache_digest(release_digest) || !AugmentorMaintenancePath(installed) ||
            !plain_tree(inspection_path, 0, &remaining)) return FALSE;
    if (swprintf_s(path, 32768, L"%ls\\release.json", inspection_path) < 0 ||
            swprintf_s(executable, 32768, L"%ls\\python\\python.exe", inspection_path) < 0 ||
            swprintf_s(script, 32768, L"%ls\\scripts\\windows-inspect-payload.py", inspection_path) < 0) return FALSE;
    inspection_stage = 2;
    metadata = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (!cache_file(metadata, NULL, FALSE, 65536) ||
            !cache_stream(metadata, INVALID_HANDLE_VALUE, release_digest)) goto done;
    inspection_stage = 3;
    command = malloc(32768 * sizeof(wchar_t));
    if (!command || swprintf_s(command, 32768, L"\"%ls\" -I -B -X utf8 \"%ls\" \"%ls\" %ls %ls %ls \"%ls\"",
            executable, script, installed, release_digest,
            inspection_installer[0] ? inspection_installer : L"-",
            health ? L"health" : L"inspect", qualification ? qualification : L"-") < 0) goto done;
    inspection_stage = 4;
    job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {0};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits))) goto done;
    inspection_stage = 5;
    if (!CreateProcessW(executable, command, NULL, NULL, FALSE,
                CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
                NULL, inspection_path, &startup_info, &process)) goto done;
    inspection_stage = 6;
    if (!AssignProcessToJobObject(job, process.hProcess)) goto done;
    inspection_stage = 7;
    if (ResumeThread(process.hThread) != 1) goto done;
    started = TRUE;
    inspection_stage = 8;
    ULONGLONG deadline = GetTickCount64() + 120000;
    if (WaitForSingleObject(process.hProcess, 120000) != WAIT_OBJECT_0) goto done;
    inspection_stage = 9;
    if (!GetExitCodeProcess(process.hProcess, &code)) goto done;
    if (code) { inspection_detail = code; goto done; }
    inspection_stage = 10;
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION accounting;
    do {
        if (!QueryInformationJobObject(job, JobObjectBasicAccountingInformation, &accounting,
                sizeof(accounting), NULL)) goto done;
        if (!accounting.ActiveProcesses) break;
        if (GetTickCount64() >= deadline) goto done;
        Sleep(10);
    } while (TRUE);
    inspection_stage = 11;
    if (swprintf_s(path, 32768, L"%ls\\..\\%ls", inspection_path,
            health ? L"health-result.json" : L"inspection-result.json") < 0) goto done;
    inspection_report = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    ok = cache_file(inspection_report, NULL, FALSE, 4096);
done:
    if (!ok && !inspection_detail) inspection_detail = GetLastError();
    /* Only the suspended worker created above can escape an assignment error.
     * Once assigned, closing its Job ends only this read-only inspection range. */
    if (process.hProcess && !started) TerminateProcess(process.hProcess, 74);
    if (job) CloseHandle(job);
    if (process.hProcess) {
        WaitForSingleObject(process.hProcess, 10000);
        CloseHandle(process.hProcess);
    }
    if (process.hThread) CloseHandle(process.hThread);
    if (metadata != INVALID_HANDLE_VALUE) CloseHandle(metadata);
    free(command);
    return ok;
}

__declspec(dllexport) BOOL WINAPI AugmentorInspectionRun(const wchar_t *installed,
        const wchar_t *release_digest) {
    if (inspection_health_attempted) return FALSE;
    BOOL ok = inspection_worker(installed, release_digest, FALSE, NULL);
    inspection_source_verified = ok && inspection_installer[0] &&
        inspection_writer != INVALID_HANDLE_VALUE && inspection_record != INVALID_HANDLE_VALUE &&
        wcscpy_s(inspection_release, 65, release_digest) == 0;
    return ok;
}

/* Observe the fixed, isolated source-health action after independent source
 * assessment. Keep the writer and active-record pins throughout. Exchange the
 * exclusive installation/startup handles for ordinary read admission so the
 * native probe can start. An active journal still blocks normal app startup;
 * held read admission prevents repair/removal. No files or records are changed. */
__declspec(dllexport) BOOL WINAPI AugmentorInspectionHealth(const wchar_t *installed,
        const wchar_t *release_digest, const wchar_t *qualification) {
    wchar_t base[32768], expected[32768]; DWORD count;
    AugmentorLease reader = {INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE,
        INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE};
    inspection_stage = 12; inspection_detail = 0;
    if (authorized || manual.file == INVALID_HANDLE_VALUE || manual.startup == INVALID_HANDLE_VALUE ||
            inspection_record == INVALID_HANDLE_VALUE || inspection_writer == INVALID_HANDLE_VALUE ||
            inspection_report == INVALID_HANDLE_VALUE || !inspection_installer[0] ||
            inspection_health_attempted) return FALSE;
    inspection_health_attempted = TRUE;
    count = GetFinalPathNameByHandleW(manual.base, base, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!count || count >= 32768 || wcsncmp(base, L"\\\\?\\", 4)) return FALSE;
    memmove(base, base + 4, (count - 3) * sizeof(wchar_t));
    if (qualification && qualification[0]) {
#ifdef AUGMENTOR_DEVELOPMENT_CANDIDATE
        count = GetFullPathNameW(qualification, 32768, expected, NULL);
        if (!count || count >= 32768 || _wcsicmp(expected, base)) return FALSE;
#else
        return FALSE;
#endif
    } else qualification = NULL;
    CloseHandle(manual.file); manual.file = INVALID_HANDLE_VALUE;
    CloseHandle(manual.startup); manual.startup = INVALID_HANDLE_VALUE;
    /* Retain the original directory handles while reacquiring the same private
     * namespace. If another maintenance attempt wins the gap, refuse without
     * waiting, killing it, retrying, or dropping the unresolved record. */
    if (!augmentor_acquire(&reader, base)) {
        inspection_detail = GetLastError(); return FALSE;
    }
    CloseHandle(manual.run); CloseHandle(manual.base);
    manual = reader;
    CloseHandle(inspection_report); inspection_report = INVALID_HANDLE_VALUE;
    return inspection_worker(installed, release_digest, TRUE, qualification);
}
