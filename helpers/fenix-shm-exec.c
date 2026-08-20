/*
 * fenix-shm-exec — Execute ELF via POSIX shm_open on tmpfs (/dev/shm). Linux-only.
 */
#include "fenix-common.h"

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --payload <path> [--name <shm_name>]\n"
            "       [--method procfs-fd|fexecve] [--ingest write|sendfile] [--unlink]\n",
            prog);
}

int main(int argc, char **argv)
{
    const char *payload_path = NULL;
    const char *shm_name = "fenix_shm_payload";
    const char *method = "procfs-fd";
    const char *ingest = "write";
    int do_unlink = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc)
            payload_path = argv[++i];
        else if (strcmp(argv[i], "--name") == 0 && i + 1 < argc)
            shm_name = argv[++i];
        else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc)
            method = argv[++i];
        else if (strcmp(argv[i], "--ingest") == 0 && i + 1 < argc)
            ingest = argv[++i];
        else if (strcmp(argv[i], "--unlink") == 0)
            do_unlink = 1;
        else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-shm-exec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!payload_path) {
        fprintf(stderr, "fenix-shm-exec: --payload is required\n");
        usage(argv[0]);
        return 1;
    }

    char shm_path[256];
    snprintf(shm_path, sizeof(shm_path), "/%s", shm_name[0] == '/' ? shm_name + 1 : shm_name);

    int shm_fd = shm_open(shm_path, O_RDWR | O_CREAT | O_TRUNC, 0700);
    if (shm_fd < 0) {
        perror("shm_open");
        return 1;
    }

    int src = open(payload_path, O_RDONLY);
    if (src < 0) {
        perror("open payload");
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }

    struct stat st;
    if (fstat(src, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0) {
        fprintf(stderr, "fenix-shm-exec: invalid payload\n");
        close(src);
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }

    size_t len = (size_t)st.st_size;
    if (ftruncate(shm_fd, (off_t)len) != 0) {
        perror("ftruncate");
        close(src);
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }

    int rc = -1;
    if (strcmp(ingest, "sendfile") == 0) {
        rc = fenix_sendfile_all(shm_fd, src, len);
    } else if (strcmp(ingest, "write") == 0) {
        unsigned char *data = malloc(len);
        if (!data) {
            perror("malloc");
            close(src);
            close(shm_fd);
            shm_unlink(shm_path);
            return 1;
        }
        ssize_t n = read(src, data, len);
        close(src);
        if (n < 0 || (size_t)n != len) {
            perror("read");
            free(data);
            close(shm_fd);
            shm_unlink(shm_path);
            return 1;
        }
        rc = fenix_write_all(shm_fd, data, len);
        free(data);
    } else {
        fprintf(stderr, "fenix-shm-exec: unknown ingest '%s'\n", ingest);
        close(src);
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }
    close(src);

    if (rc != 0) {
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }

    char disk_path[512];
    snprintf(disk_path, sizeof(disk_path), "/dev/shm%s", shm_path);

    close(shm_fd);
    shm_fd = open(disk_path, O_RDONLY);
    if (shm_fd < 0) {
        perror("open shm for exec");
        if (!do_unlink)
            shm_unlink(shm_path);
        return 1;
    }

    if (do_unlink)
        shm_unlink(shm_path);

    char fd_path[64];
    char *exec_argv[] = { "fenix_shm_elf", NULL };
    snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", shm_fd);

    if (strcmp(method, "fexecve") == 0) {
        fexecve(shm_fd, exec_argv, environ);
        perror("fexecve");
    } else if (strcmp(method, "procfs-fd") == 0) {
        /* Always exec via /proc/self/fd — /dev/shm is often mounted noexec */
        execve(fd_path, exec_argv, environ);
        perror("execve procfs-fd");
    } else {
        fprintf(stderr, "fenix-shm-exec: unknown method '%s'\n", method);
    }

    close(shm_fd);
    if (!do_unlink)
        shm_unlink(shm_path);
    return 1;
}
