/*
 * fenix-memfd-self-reexec — Copy /proc/self/exe into memfd, unlink on-disk path, re-exec.
 * QLNX-style fileless self-relocation (lab PoC). Linux-only.
 */

#include "fenix-common.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s [--name <memfd_name>] [--method execveat|procfs-fd]\n"
            "       [--argv0 <name>] [--no-unlink]\n",
            prog);
}

static int copy_fd_to_memfd(int src, int dst)
{
    char buf[8192];
    ssize_t n;
    while ((n = read(src, buf, sizeof(buf))) > 0) {
        ssize_t off = 0;
        while (off < n) {
            ssize_t w = write(dst, buf + off, (size_t)(n - off));
            if (w < 0) {
                perror("write memfd");
                return -1;
            }
            off += w;
        }
    }
    if (n < 0) {
        perror("read exe");
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *memfd_name = "fenix_self";
    const char *method = "execveat";
    const char *argv0_override = NULL;
    int do_unlink = 1;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--name") == 0 && i + 1 < argc) {
            memfd_name = argv[++i];
        } else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc) {
            method = argv[++i];
        } else if (strcmp(argv[i], "--argv0") == 0 && i + 1 < argc) {
            argv0_override = argv[++i];
        } else if (strcmp(argv[i], "--no-unlink") == 0) {
            do_unlink = 0;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-memfd-self-reexec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len < 0) {
        perror("readlink /proc/self/exe");
        return 1;
    }
    exe_path[len] = '\0';

    if (getenv("FENIX_MFD_RE")) {
        fprintf(stderr, "fenix-memfd-self-reexec: re-exec from memfd complete (%s)\n", exe_path);
        return 0;
    }

    if (strstr(exe_path, "memfd:") != NULL || strstr(exe_path, "(deleted)") != NULL) {
        fprintf(stderr, "fenix-memfd-self-reexec: already running from memory (%s)\n", exe_path);
        return 0;
    }

    int src = open(exe_path, O_RDONLY);
    if (src < 0) {
        perror("open /proc/self/exe");
        return 1;
    }

    int mfd = fenix_create_memfd(memfd_name);
    if (mfd < 0) {
        perror("memfd_create");
        close(src);
        return 1;
    }

    if (copy_fd_to_memfd(src, mfd) != 0) {
        close(src);
        close(mfd);
        return 1;
    }
    close(src);

    if (fchmod(mfd, 0755) != 0) {
        perror("fchmod memfd");
        close(mfd);
        return 1;
    }

    int flags = fcntl(mfd, F_GETFD);
    if (flags >= 0)
        fcntl(mfd, F_SETFD, flags & ~FD_CLOEXEC);

    if (do_unlink) {
        if (unlink(exe_path) != 0) {
            perror("unlink on-disk binary");
            /* continue: may already be memfd-backed */
        }
    }

    if (lseek(mfd, 0, SEEK_SET) != 0) {
        perror("lseek memfd");
        close(mfd);
        return 1;
    }

    const char *display = argv0_override ? argv0_override : memfd_name;
    char fd_path[64];
    snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", mfd);
    char *exec_argv[] = { (char *)display, NULL };

    setenv("FENIX_MFD_RE", "1", 1);

    if (strcmp(method, "execveat") == 0) {
        execveat(mfd, "", exec_argv, environ, AT_EMPTY_PATH);
        perror("execveat");
    } else if (strcmp(method, "procfs-fd") == 0) {
        execve(fd_path, exec_argv, environ);
        perror("execve procfs-fd");
    } else {
        fprintf(stderr, "fenix-memfd-self-reexec: unknown method '%s'\n", method);
        close(mfd);
        return 1;
    }

    close(mfd);
    return 1;
}
