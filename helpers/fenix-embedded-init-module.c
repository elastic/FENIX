/*
 * fenix-embedded-init-module — Load a pre-embedded .ko via init_module.
 * Built with hello_lkm_embed.h from payloads/hello_lkm/hello_lkm.ko. Requires root.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <linux/module.h>
#include <sys/syscall.h>

#include "hello_lkm_embed.h"

#ifndef __NR_init_module
#ifdef __x86_64__
#define __NR_init_module 175
#elif defined(__aarch64__)
#define __NR_init_module 105
#endif
#endif

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    if (geteuid() != 0) {
        fprintf(stderr, "fenix-embedded-init-module: must be run as root\n");
        return 1;
    }

    long rc = syscall(__NR_init_module, hello_lkm_ko, hello_lkm_ko_len, "");
    if (rc != 0) {
        perror("init_module");
        return 1;
    }

    fprintf(stderr,
            "fenix-embedded-init-module: loaded %u bytes via embedded buffer + init_module\n",
            hello_lkm_ko_len);
    return 0;
}
