/*
 * fenix-stdin-memexec — Read ELF from stdin or file into memfd and exec (memexec-style). Linux-only.
 */
#include "fenix-common.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s [--payload <path>] [--name <memfd_name>]\n"
            "       [--method procfs-fd|fexecve|execveat] [--fchmod]\n"
            "  Without --payload, reads ELF bytes from stdin until EOF.\n",
            prog);
}

static unsigned char *read_stdin(size_t *out_len)
{
    size_t cap = 65536;
    size_t len = 0;
    unsigned char *buf = malloc(cap);
    if (!buf) {
        perror("malloc");
        return NULL;
    }

    for (;;) {
        if (len == cap) {
            cap *= 2;
            unsigned char *nbuf = realloc(buf, cap);
            if (!nbuf) {
                perror("realloc");
                free(buf);
                return NULL;
            }
            buf = nbuf;
        }
        ssize_t n = read(STDIN_FILENO, buf + len, cap - len);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            perror("read stdin");
            free(buf);
            return NULL;
        }
        if (n == 0)
            break;
        len += (size_t)n;
    }

    if (len == 0) {
        fprintf(stderr, "fenix-stdin-memexec: no data on stdin\n");
        free(buf);
        return NULL;
    }

    *out_len = len;
    return buf;
}

int main(int argc, char **argv)
{
    const char *payload_path = NULL;
    const char *memfd_name = "fenix_stdin_payload";
    const char *method = "execveat";
    int do_fchmod = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc)
            payload_path = argv[++i];
        else if (strcmp(argv[i], "--name") == 0 && i + 1 < argc)
            memfd_name = argv[++i];
        else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc)
            method = argv[++i];
        else if (strcmp(argv[i], "--fchmod") == 0)
            do_fchmod = 1;
        else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-stdin-memexec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    size_t len = 0;
    unsigned char *data = NULL;
    int data_owned = 1;

    if (payload_path) {
        data = fenix_read_file(payload_path, &len);
        if (!data)
            return 1;
    } else {
        data = read_stdin(&len);
        if (!data)
            return 1;
    }

    int mfd = fenix_create_memfd(memfd_name);
    if (mfd < 0) {
        perror("memfd_create");
        if (data_owned)
            free(data);
        return 1;
    }

    if (fenix_write_all(mfd, data, len) != 0) {
        close(mfd);
        if (data_owned)
            free(data);
        return 1;
    }
    if (data_owned)
        free(data);

    if (do_fchmod && fchmod(mfd, 0755) != 0) {
        perror("fchmod");
        close(mfd);
        return 1;
    }

    if (lseek(mfd, 0, SEEK_SET) != 0) {
        perror("lseek");
        close(mfd);
        return 1;
    }

    char fd_path[64];
    char *exec_argv[] = { "fenix_stdin_elf", NULL };
    snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", mfd);

    if (strcmp(method, "procfs-fd") == 0) {
        execve(fd_path, exec_argv, environ);
        perror("execve");
    } else if (strcmp(method, "fexecve") == 0) {
        fexecve(mfd, exec_argv, environ);
        perror("fexecve");
    } else if (strcmp(method, "execveat") == 0) {
        execveat(mfd, "", exec_argv, environ, AT_EMPTY_PATH);
        perror("execveat");
    } else {
        fprintf(stderr, "fenix-stdin-memexec: unknown method '%s'\n", method);
        close(mfd);
        return 1;
    }

    close(mfd);
    return 1;
}
