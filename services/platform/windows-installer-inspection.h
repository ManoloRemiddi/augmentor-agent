/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Read-only independent payload inspection. Included after plain_tree and the
 * cache helpers. Only this call's never-installed worker Job can be terminated.
 */
static HANDLE inspection_parent = INVALID_HANDLE_VALUE;
static HANDLE inspection_root = INVALID_HANDLE_VALUE;
static HANDLE inspection_report = INVALID_HANDLE_VALUE;
static wchar_t inspection_path[32768];

static void augmentor_inspection_close(void) {
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

__declspec(dllexport) BOOL WINAPI AugmentorInspectionRun(const wchar_t *installed,
        const wchar_t *release_digest) {
    HANDLE metadata = INVALID_HANDLE_VALUE, job = NULL;
    PROCESS_INFORMATION process = {0}; STARTUPINFOW startup_info = {sizeof(startup_info)};
    wchar_t executable[32768], script[32768], path[32768], *command = NULL;
    BOOL ok = FALSE, started = FALSE; DWORD code = 74;
    unsigned remaining = 250000;
    if (manual.file == INVALID_HANDLE_VALUE || authorized || inspection_root == INVALID_HANDLE_VALUE ||
            inspection_report != INVALID_HANDLE_VALUE || !installed || wcschr(installed, L'"') ||
            !cache_digest(release_digest) || !AugmentorMaintenancePath(installed) ||
            !plain_tree(inspection_path, 0, &remaining)) return FALSE;
    if (swprintf_s(path, 32768, L"%ls\\release.json", inspection_path) < 0 ||
            swprintf_s(executable, 32768, L"%ls\\python\\python.exe", inspection_path) < 0 ||
            swprintf_s(script, 32768, L"%ls\\scripts\\windows-inspect-payload.py", inspection_path) < 0) return FALSE;
    metadata = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (!cache_file(metadata, NULL, FALSE, 65536) ||
            !cache_stream(metadata, INVALID_HANDLE_VALUE, release_digest)) goto done;
    command = malloc(32768 * sizeof(wchar_t));
    if (!command || swprintf_s(command, 32768, L"\"%ls\" -I -B -X utf8 \"%ls\" \"%ls\" %ls",
            executable, script, installed, release_digest) < 0) goto done;
    job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {0};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits)) ||
            !CreateProcessW(executable, command, NULL, NULL, FALSE,
                CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
                NULL, inspection_path, &startup_info, &process)) goto done;
    if (!AssignProcessToJobObject(job, process.hProcess) || ResumeThread(process.hThread) != 1) goto done;
    started = TRUE;
    if (WaitForSingleObject(process.hProcess, 120000) != WAIT_OBJECT_0 ||
            !GetExitCodeProcess(process.hProcess, &code) || code) goto done;
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION accounting;
    if (!QueryInformationJobObject(job, JobObjectBasicAccountingInformation, &accounting,
            sizeof(accounting), NULL) || accounting.ActiveProcesses) goto done;
    if (swprintf_s(path, 32768, L"%ls\\..\\inspection-result.json", inspection_path) < 0) goto done;
    inspection_report = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    ok = cache_file(inspection_report, NULL, FALSE, 4096);
done:
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
