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
#include <sys/file.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <pwd.h>

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

static int startup_descriptor = -1;
static int installation_descriptor = -1;

/* The socket runtime is temporary; update intent survives reboot in state. */
static void require_updates_clear(void) {
    const char *state = getenv("XDG_STATE_HOME");
    char *default_state = NULL;
    if (!state || !*state) {
        struct passwd *user = getpwuid(getuid());
        if (!user || !user->pw_dir ||
            asprintf(&default_state, "%s/Library/Application Support/Augmentor/state", user->pw_dir) < 0)
            fail("cannot locate persistent update state");
        state = default_state;
    }
    if (*state != '/') fail("state directory must be absolute");
    char *directory = join(state, "augmentor/updates");
    struct stat info;
    if (lstat(directory, &info) != 0) {
        if (errno != ENOENT) fail("cannot inspect persistent update state");
    } else {
        if (!S_ISDIR(info.st_mode) || info.st_uid != getuid() || (info.st_mode & 0077))
            fail("update state must be private and owned by this user");
        char *record = join(directory, "active.json");
        if (lstat(record, &info) == 0 || errno != ENOENT)
            fail("an unfinished update needs verification before reopening");
        free(record);
    }
    free(directory); free(default_state);
}

/* Called by the embedded desktop after its control endpoint is discoverable. */
int AugmentorStartupReady(void) {
    if (startup_descriptor >= 0) {
        int descriptor = startup_descriptor;
        startup_descriptor = -1;
        if (close(descriptor) != 0) return 0;
    }
    return 1;
}

static int read_lease(const char *runtime, const char *name) {
    char *path = join(runtime, name);
    int descriptor = open(path, O_RDWR | O_CREAT | O_NOFOLLOW, 0600);
    free(path);
    struct stat info;
    if (descriptor < 0 || fstat(descriptor, &info) != 0 || !S_ISREG(info.st_mode) ||
        info.st_uid != getuid() || (info.st_mode & 0077) || info.st_nlink != 1)
        fail("invalid private maintenance lock");
    if (flock(descriptor, LOCK_SH | LOCK_NB) != 0)
        fail("installation maintenance is in progress");
    return descriptor;
}

static void retain_launch_leases(void) {
    const char *runtime = getenv("XDG_RUNTIME_DIR");
    char *default_runtime = NULL;
    if (!runtime || !*runtime) {
        if (asprintf(&default_runtime, "/tmp/augmentor-%u", (unsigned)getuid()) < 0)
            fail("out of memory");
        runtime = default_runtime;
    }
    if (*runtime != '/') fail("runtime directory must be absolute");
    if (mkdir(runtime, 0700) != 0 && errno != EEXIST) fail("cannot create runtime directory");
    struct stat info;
    if (lstat(runtime, &info) != 0 || !S_ISDIR(info.st_mode) ||
        info.st_uid != getuid() || (info.st_mode & 0077))
        fail("runtime directory must be private and owned by this user");
    if (strcmp(AUGMENTOR_COMPONENT, "desktop") == 0)
        startup_descriptor = read_lease(runtime, "startup.lock");
    require_updates_clear();
    /* Hold before resolving resources or initializing Python. No child inherits
     * through subprocess; the fixed browser exec retains this lifetime lease. */
    installation_descriptor = read_lease(runtime, "installation.lock");
    free(default_runtime);
}

int main(int argc, char **argv) {
    retain_launch_leases();
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
