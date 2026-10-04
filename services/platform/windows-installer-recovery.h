/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Observe independent source restoration outside the replaceable application.
 */
static BOOL recovery_observer_attempted = FALSE;

__declspec(dllexport) BOOL WINAPI AugmentorRecoveryObserve(const wchar_t *installed,
        const wchar_t *release_digest, const wchar_t *helper_digest,
        const wchar_t *installation_key, const wchar_t *application_id,
        const wchar_t *qualification) {
    typedef struct {
        wchar_t base[32768], expected[32768], executable[32768], script[32768];
        wchar_t path[32768], command[32768];
    } RecoveryPaths;
    RecoveryPaths *paths = NULL;
    HANDLE metadata = INVALID_HANDLE_VALUE, job = NULL;
    PROCESS_INFORMATION process = {0}; STARTUPINFOW startup_info = {sizeof(startup_info)};
    BOOL ok = FALSE, started = FALSE, qualified = qualification && qualification[0];
    DWORD count, code = 74; unsigned remaining = 250000;
    inspection_stage = 20; inspection_detail = 0;
    if (recovery_observer_attempted || authorized || !inspection_source_verified || inspection_health_attempted ||
            manual.file == INVALID_HANDLE_VALUE || manual.startup == INVALID_HANDLE_VALUE ||
            inspection_writer == INVALID_HANDLE_VALUE || inspection_record == INVALID_HANDLE_VALUE ||
            inspection_root == INVALID_HANDLE_VALUE || cache_installer == INVALID_HANDLE_VALUE ||
            cache_receipt == INVALID_HANDLE_VALUE || !cache_selection_valid(cache_selection_after) ||
            !cache_digest(release_digest) || !cache_digest(helper_digest) ||
            wcscmp(release_digest, inspection_release) || !installed || wcschr(installed, L'"') ||
            !installation_key || wcschr(installation_key, L'"') || wcslen(installation_key) > 1024 ||
            !application_id || wcschr(application_id, L'"') || wcslen(application_id) > 128 ||
            !AugmentorMaintenancePath(installed) || !plain_tree(inspection_path, 0, &remaining)) return FALSE;
    const size_t prefix = sizeof(CACHE_SELECTION_PREFIX) - 1;
    for (unsigned i = 0; i < 64; ++i)
        if (cache_selection_after[prefix+i] != inspection_installer[i] ||
                cache_selection_after[prefix+65+i] != inspection_release[i]) return FALSE;
    recovery_observer_attempted = TRUE;
    paths = calloc(1, sizeof(*paths));
    if (!paths) goto done;
    count = GetFinalPathNameByHandleW(manual.base, paths->base, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
    if (!count || count >= 32768 || wcsncmp(paths->base, L"\\\\?\\", 4)) goto done;
    memmove(paths->base, paths->base+4, (count-3)*sizeof(wchar_t));
    if (qualified) {
#ifdef AUGMENTOR_DEVELOPMENT_CANDIDATE
        count = GetFullPathNameW(qualification, 32768, paths->expected, NULL);
        if (!count || count >= 32768 || _wcsicmp(paths->base, paths->expected)) goto done;
#else
        goto done;
#endif
    }
    inspection_stage = 21;
    if (swprintf_s(paths->path, 32768, L"%ls\\release.json", inspection_path) < 0 ||
            swprintf_s(paths->executable, 32768, L"%ls\\python\\python.exe", inspection_path) < 0 ||
            swprintf_s(paths->script, 32768, L"%ls\\scripts\\windows-recover-source.py", inspection_path) < 0) goto done;
    metadata = CreateFileW(paths->path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    if (!cache_file(metadata, NULL, FALSE, 65536) ||
            !cache_stream(metadata, INVALID_HANDLE_VALUE, release_digest) ||
            swprintf_s(paths->command, 32768,
                L"\"%ls\" -I -B -X utf8 \"%ls\" \"%ls\" \"%ls\" %ls %ls %ls \"%ls\" \"%ls\" %u",
                paths->executable, paths->script, installed, paths->base, release_digest,
                inspection_installer, helper_digest, installation_key, application_id, qualified ? 1 : 0) < 0) goto done;
    inspection_stage = 22;
    job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {0};
    /* Only the explicitly launched installer requests breakaway. Ordinary health
     * children remain contained. Losing this observer must not kill Setup. */
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits))) goto done;
    inspection_stage = 23;
    if (!CreateProcessW(paths->executable, paths->command, NULL, NULL, FALSE,
            CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT, NULL,
            inspection_path, &startup_info, &process)) goto done;
    inspection_stage = 24;
    if (!AssignProcessToJobObject(job, process.hProcess)) goto done;
    /* The worker obtains fresh admission and compares the exact snapshot before
     * intent. The inner source installer then obtains its own native admission.
     * Keep source artifact/scratch pins, but no lock needed by those operations. */
    CloseHandle(inspection_writer); inspection_writer = INVALID_HANDLE_VALUE;
    CloseHandle(inspection_record); inspection_record = INVALID_HANDLE_VALUE;
    if (cache_selection != INVALID_HANDLE_VALUE) CloseHandle(cache_selection);
    cache_selection = INVALID_HANDLE_VALUE;
    if (inspection_report != INVALID_HANDLE_VALUE) CloseHandle(inspection_report);
    inspection_report = INVALID_HANDLE_VALUE;
    augmentor_release(&manual);
    inspection_stage = 25;
    if (ResumeThread(process.hThread) != 1) goto done;
    started = TRUE;
    inspection_stage = 26;
    /* The observer has a ten-minute actual-Setup bound plus inventory/health.
     * This outer bound must not terminate it at its inner observation limit. */
    ULONGLONG deadline = GetTickCount64() + 1200000;
    if (WaitForSingleObject(process.hProcess, 1200000) != WAIT_OBJECT_0) goto done;
    inspection_stage = 27;
    if (!GetExitCodeProcess(process.hProcess, &code)) goto done;
    if (code) { inspection_detail = code; goto done; }
    inspection_stage = 28;
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION accounting;
    do {
        if (!QueryInformationJobObject(job, JobObjectBasicAccountingInformation, &accounting, sizeof(accounting), NULL)) goto done;
        if (!accounting.ActiveProcesses) break;
        if (GetTickCount64() >= deadline) goto done;
        Sleep(10);
    } while (TRUE);
    inspection_stage = 29;
    if (swprintf_s(paths->path, 32768, L"%ls\\..\\recovery-result.json", inspection_path) < 0) goto done;
    inspection_report = CreateFileW(paths->path, GENERIC_READ, FILE_SHARE_READ, NULL,
        OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    ok = cache_file(inspection_report, NULL, FALSE, 4096);
done:
    if (!ok && !inspection_detail) inspection_detail = GetLastError();
    if (process.hProcess && !started) TerminateProcess(process.hProcess, 74);
    /* This can end the owned observer/health probes, never its independent Setup. */
    if (job) CloseHandle(job);
    if (process.hProcess) { WaitForSingleObject(process.hProcess, 10000); CloseHandle(process.hProcess); }
    if (process.hThread) CloseHandle(process.hThread);
    if (metadata != INVALID_HANDLE_VALUE) CloseHandle(metadata);
    free(paths);
    return ok;
}
