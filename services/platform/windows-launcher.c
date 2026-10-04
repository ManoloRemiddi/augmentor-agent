/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Embed the private CPython in a native Windows executable. No global Python,
 * PATH DLL lookup, console flash, or extraction on each launch is required.
 */
#define PY_SSIZE_T_CLEAN
/* All Python symbols are loaded explicitly below, not linked on process entry. */
#define MS_NO_COREDLL
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <Python.h>
#include <wchar.h>
#include <io.h>
#include <fcntl.h>
static BOOL health_check = FALSE;
#ifdef AUGMENTOR_LIFETIME_LEASE
#include "windows-lease.h"
static AugmentorLease lease = {INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE,
    INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE};
static HANDLE updates = INVALID_HANDLE_VALUE;

/* Only the startup reader is releasable from Python. The lifetime lease stays
 * held through runtime finalization and actual process exit. */
__declspec(dllexport) BOOL WINAPI AugmentorStartupReady(void) {
    HANDLE startup = InterlockedExchangePointer((PVOID volatile *)&lease.startup,
        INVALID_HANDLE_VALUE);
    return startup == INVALID_HANDLE_VALUE || CloseHandle(startup);
}
#endif

#ifndef AUGMENTOR_SCRIPT
#ifdef AUGMENTOR_BROWSER_HOST
#define AUGMENTOR_SCRIPT L"scripts\\launch-windows-browser.py"
#else
#define AUGMENTOR_SCRIPT L"scripts\\launch-windows.py"
#endif
#endif

static int failure(const wchar_t *message) {
    if (health_check) {
        const char error[] = "Augmentor local health could not start.\n";
        DWORD written;
        WriteFile(GetStdHandle(STD_ERROR_HANDLE), error, (DWORD)(sizeof(error)-1), &written, NULL);
        return 1;
    }
#ifdef AUGMENTOR_BROWSER_HOST
    (void)message;
    const char error[] = "Augmentor's native browser host could not start. Repair this installation.\n";
    DWORD written;
    WriteFile(GetStdHandle(STD_ERROR_HANDLE), error, (DWORD)(sizeof(error)-1), &written, NULL);
#else
    MessageBoxW(NULL, message, L"Augmentor could not start", MB_OK | MB_ICONERROR);
#endif
    return 1;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command, int show) {
    (void)instance; (void)previous; (void)command; (void)show;
    int argc = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv || argc < 1) return failure(L"Cannot read launch arguments.");
#ifdef AUGMENTOR_LIFETIME_LEASE
    const wchar_t *qualification = NULL;
#ifdef AUGMENTOR_DEVELOPMENT_CANDIDATE
    if (argc >= 3 && !wcscmp(argv[1], L"--qualification-root")) qualification = argv[2];
#endif
#ifndef AUGMENTOR_BROWSER_HOST
    /* This mode chooses a fixed read-only script, never the desktop script
     * with a journal-bypass flag. It cannot accept desktop/service arguments. */
    int action = qualification ? 3 : 1;
    if (argc > action && !wcscmp(argv[action], L"--local-health")) {
        health_check = TRUE;
        if (argc != action + 1) { LocalFree(argv); return 64; }
    }
#endif
    if (!augmentor_acquire(&lease, qualification)) {
        LocalFree(argv);
        /* Disposable CI launches cannot leave an unattended modal dialog. */
        if (!qualification) failure(L"Augmentor cannot start during installation maintenance or with invalid private application data. Finish maintenance or repair the installation, then try again.");
        return 73;
    }
    if (!health_check && !augmentor_updates_clear(lease.base, &updates)) {
        LocalFree(argv);
        if (!qualification) failure(L"An unfinished Augmentor update needs recovery before the app can open. Your conversations and settings were preserved.");
        return 74;
    }
    /* Retain through CPython finalization and process exit. The OS also releases
     * the lease on a crash; no stale marker blocks the next startup. */
#endif
    if (health_check && (_fileno(stdout) < 0 || _setmode(_fileno(stdout), _O_BINARY) == -1))
        return failure(L"The health observer did not provide an output handle.");
#ifdef AUGMENTOR_BROWSER_HOST
    /* Native messaging is a binary length-prefixed protocol, never console text. */
    if (_fileno(stdin) < 0 || _fileno(stdout) < 0 ||
        _setmode(_fileno(stdin), _O_BINARY) == -1 ||
        _setmode(_fileno(stdout), _O_BINARY) == -1)
        return failure(L"The browser did not provide protocol handles.");
#endif
    wchar_t root[32768], home[32768], dll[32768], python[32768], script[32768];
    DWORD length = GetModuleFileNameW(NULL, root, 32768);
    if (!length || length >= 32768) return failure(L"Cannot locate this application.");
    wchar_t *slash = wcsrchr(root, L'\\');
    if (!slash) return failure(L"Invalid application path.");
    *slash = L'\0';
    if (swprintf_s(home, 32768, L"%ls\\python", root) < 0 ||
        swprintf_s(dll, 32768, L"%ls\\python313.dll", home) < 0 ||
        swprintf_s(python, 32768, L"%ls\\python.exe", home) < 0 ||
        swprintf_s(script, 32768, L"%ls\\%ls", root,
            health_check ? L"scripts\\windows-local-health.py" : AUGMENTOR_SCRIPT) < 0)
        return failure(L"The application path is too long.");
    SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    HMODULE library = LoadLibraryExW(dll, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!library) return failure(L"The private Python runtime could not load. Repair this installation.");
    /* Resolve explicitly so the OS does not search for Python before main. */
#define LOAD(result, name, arguments) \
    typedef result (*name##_fn) arguments; \
    name##_fn p_##name = (name##_fn)(void *)GetProcAddress(library, #name); \
    if (!p_##name) return failure(L"The private Python runtime is incompatible.")
    LOAD(void, PyConfig_InitIsolatedConfig, (PyConfig *));
    LOAD(void, PyPreConfig_InitIsolatedConfig, (PyPreConfig *));
    LOAD(PyStatus, Py_PreInitialize, (const PyPreConfig *));
    LOAD(PyStatus, PyConfig_SetString, (PyConfig *, wchar_t **, const wchar_t *));
    LOAD(PyStatus, PyConfig_SetArgv, (PyConfig *, Py_ssize_t, wchar_t * const *));
    LOAD(PyStatus, Py_InitializeFromConfig, (const PyConfig *));
    LOAD(void, PyConfig_Clear, (PyConfig *));
    LOAD(int, PyStatus_Exception, (PyStatus));
    LOAD(int, Py_RunMain, (void));
    wchar_t **args = calloc((size_t)argc, sizeof(wchar_t *));
    if (!args) { LocalFree(argv); return failure(L"Not enough memory to start."); }
    args[0] = script;
    for (int i = 1; i < argc; ++i) args[i] = argv[i];
    PyConfig config;
    p_PyConfig_InitIsolatedConfig(&config);
    config.write_bytecode = 0;
    config.install_signal_handlers = 1;
    config.parse_argv = 0;
    PyStatus status;
#define CONFIGURE(call) do { status = (call); if (p_PyStatus_Exception(status)) goto error; } while (0)
    PyPreConfig preconfig;
    p_PyPreConfig_InitIsolatedConfig(&preconfig);
    preconfig.utf8_mode = 1;
    CONFIGURE(p_Py_PreInitialize(&preconfig));
    /* Child services share the text contract; isolated children also pass -Xutf8. */
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    CONFIGURE(p_PyConfig_SetString(&config, &config.home, home));
    CONFIGURE(p_PyConfig_SetString(&config, &config.program_name, python));
    CONFIGURE(p_PyConfig_SetString(&config, &config.executable, python));
    CONFIGURE(p_PyConfig_SetString(&config, &config.run_filename, script));
    CONFIGURE(p_PyConfig_SetArgv(&config, argc, args));
    CONFIGURE(p_Py_InitializeFromConfig(&config));
    p_PyConfig_Clear(&config);
    free(args); LocalFree(argv);
    return p_Py_RunMain();
error:
    p_PyConfig_Clear(&config);
    free(args); LocalFree(argv);
    return failure(L"Python initialization failed. Repair this installation.");
}
