/* Copyright © 2026 Manolo Remiddi
 * SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
 * Keep the desktop in its native Mach-O process for macOS app attribution.
 * The bundled Python remains the interpreter for independent service children.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <mach-o/dyld.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef AUGMENTOR_COMPONENT
#error "Build with an explicit Augmentor component"
#endif

static void fail(const char *message) {
    fprintf(stderr, "Augmentor could not start: %s\n", message);
    exit(1);
}

static char *join(const char *root, const char *suffix) {
    char *result = NULL;
    if (asprintf(&result, "%s/%s", root, suffix) < 0) fail("out of memory");
    return result;
}

int main(int argc, char **argv) {
    uint32_t size = 0;
    _NSGetExecutablePath(NULL, &size);
    char *buffer = malloc(size);
    if (!buffer || _NSGetExecutablePath(buffer, &size) != 0) fail("cannot locate executable");
    char *executable = realpath(buffer, NULL);
    free(buffer);
    if (!executable) fail("cannot resolve executable");
    char *slash = strrchr(executable, '/');
    if (!slash) fail("invalid executable path");
    *slash = '\0';
    char *relative = join(executable, "../Resources/app");
    char *root = realpath(relative, NULL);
    free(relative);
    free(executable);
    if (!root) fail("application resources are missing");
    char *home = join(root, "python");
    char *python = join(home, "bin/python3");
    char *script = join(root, "scripts/launch-component.py");
    char **args = calloc((size_t)argc + 2, sizeof(char *));
    if (!args) fail("out of memory");
    args[0] = script;
    args[1] = AUGMENTOR_COMPONENT;
    for (int i = 1; i < argc; ++i) args[i + 1] = argv[i];

    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.write_bytecode = 0;
    config.install_signal_handlers = 1;
    config.parse_argv = 0;
    PyStatus status;
#define CONFIGURE(call) do { status = (call); if (PyStatus_Exception(status)) goto error; } while (0)
    CONFIGURE(PyConfig_SetBytesString(&config, &config.home, home));
    CONFIGURE(PyConfig_SetBytesString(&config, &config.program_name, python));
    CONFIGURE(PyConfig_SetBytesString(&config, &config.executable, python));
    CONFIGURE(PyConfig_SetBytesString(&config, &config.run_filename, script));
    CONFIGURE(PyConfig_SetBytesArgv(&config, argc + 1, args));
    CONFIGURE(Py_InitializeFromConfig(&config));
    PyConfig_Clear(&config);
    free(args); free(script); free(python); free(home); free(root);
    return Py_RunMain();
error:
    PyConfig_Clear(&config);
    Py_ExitStatusException(status);
}
