/*
 * fenix-init-module — Load a kernel module via init_module (lab PoC).
 * Methods: heap, memfd+mmap, memfd+mmap+fork.
 * Requires root. Linux-only.
 */

#include "fenix-common.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

#include <linux/module.h>
#include <sys/syscall.h>

#ifndef __NR_init_module
#ifdef __x86_64__
#define __NR_init_module 175
#elif defined(__aarch64__)
#define __NR_init_module 105
#endif
#endif

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --module <path.ko> --method "
            "init_module|memfd-init-module|memfd-init-module-fork\n",
            prog);
}

static int do_init_module(void *image, unsigned long len)
{
    long rc = syscall(__NR_init_module, image, len, "");
    if (rc != 0) {
        perror("init_module");
        return -1;
    }
    return 0;
}

static int load_heap(const char *module_path)
{
    size_t len = 0;
    void *image = fenix_read_file(module_path, &len);
    if (!image)
        return -1;

    int rc = do_init_module(image, (unsigned long)len);
    free(image);
    return rc;
}

static int slurp_to_memfd(const char *module_path, size_t *out_len)
{
    size_t len = 0;
    unsigned char *file = fenix_read_file(module_path, &len);
    if (!file)
        return -1;

    int mfd = fenix_create_memfd("fenix_lkm");
    if (mfd < 0) {
        perror("memfd_create");
        free(file);
        return -1;
    }

    if (fenix_write_all(mfd, file, len) != 0) {
        close(mfd);
        free(file);
        return -1;
    }
    free(file);

    *out_len = len;
    return mfd;
}

static int load_memfd_mmap(const char *module_path, int fork_child)
{
    size_t len = 0;
    int mfd = slurp_to_memfd(module_path, &len);
    if (mfd < 0)
        return -1;

    if (fork_child) {
        pid_t pid = fork();
        if (pid < 0) {
            perror("fork");
            close(mfd);
            return -1;
        }
        if (pid == 0) {
            void *image = mmap(NULL, len, PROT_READ, MAP_PRIVATE, mfd, 0);
            if (image == MAP_FAILED) {
                perror("mmap");
                _exit(2);
            }
            if (do_init_module(image, (unsigned long)len) != 0)
                _exit(3);
            _exit(0);
        }

        int status = 0;
        if (waitpid(pid, &status, 0) < 0) {
            perror("waitpid");
            close(mfd);
            return -1;
        }
        close(mfd);

        if (WIFEXITED(status) && WEXITSTATUS(status) == 0)
            return 0;

        fprintf(stderr, "fenix-init-module: child failed (status=%d)\n", status);
        return -1;
    }

    void *image = mmap(NULL, len, PROT_READ, MAP_PRIVATE, mfd, 0);
    if (image == MAP_FAILED) {
        perror("mmap");
        close(mfd);
        return -1;
    }

    int rc = do_init_module(image, (unsigned long)len);
    close(mfd);
    return rc;
}

int main(int argc, char **argv)
{
    const char *module_path = NULL;
    const char *method = "init_module";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--module") == 0 && i + 1 < argc) {
            module_path = argv[++i];
        } else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc) {
            method = argv[++i];
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-init-module: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!module_path) {
        fprintf(stderr, "fenix-init-module: --module is required\n");
        usage(argv[0]);
        return 1;
    }

    if (geteuid() != 0) {
        fprintf(stderr, "fenix-init-module: must be run as root\n");
        return 1;
    }

    int rc = -1;
    if (strcmp(method, "init_module") == 0) {
        rc = load_heap(module_path);
    } else if (strcmp(method, "memfd-init-module") == 0) {
        rc = load_memfd_mmap(module_path, 0);
    } else if (strcmp(method, "memfd-init-module-fork") == 0) {
        rc = load_memfd_mmap(module_path, 1);
    } else {
        fprintf(stderr, "fenix-init-module: unknown method '%s'\n", method);
        usage(argv[0]);
        return 1;
    }

    if (rc != 0)
        return 1;

    fprintf(stderr, "fenix-init-module: module loaded via %s\n", method);
    return 0;
}
