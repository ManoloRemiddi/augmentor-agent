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

#ifndef AUGMENTOR_SCRIPT
#define AUGMENTOR_SCRIPT L"scripts\\launch-windows.py"
#endif

static int failure(const wchar_t *message) {
    MessageBoxW(NULL, message, L"Augmentor could not start", MB_OK | MB_ICONERROR);
    return 1;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command, int show) {
    (void)instance; (void)previous; (void)command; (void)show;
    wchar_t root[32768], home[32768], dll[32768], python[32768], script[32768];
    DWORD length = GetModuleFileNameW(NULL, root, 32768);
    if (!length || length >= 32768) return failure(L"Cannot locate this application.");
    wchar_t *slash = wcsrchr(root, L'\\');
    if (!slash) return failure(L"Invalid application path.");
    *slash = L'\0';
    if (swprintf_s(home, 32768, L"%ls\\python", root) < 0 ||
        swprintf_s(dll, 32768, L"%ls\\python313.dll", home) < 0 ||
        swprintf_s(python, 32768, L"%ls\\python.exe", home) < 0 ||
        swprintf_s(script, 32768, L"%ls\\%ls", root, AUGMENTOR_SCRIPT) < 0)
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
    int argc = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv || argc < 1) return failure(L"Cannot read launch arguments.");
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
