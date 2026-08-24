/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch B.V. licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *	http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
/*
 * fenix-finit-module — Load a kernel module via finit_module (lab PoC).
 * Supports file-backed and memfd-backed loading. Requires root. Linux-only.
 */

#include "fenix-common.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <linux/module.h>
#include <sys/syscall.h>

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --module <path.ko> --method finit_module|memfd-finit-module\n",
            prog);
}

int main(int argc, char **argv)
{
    const char *module_path = NULL;
    const char *method = "finit_module";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--module") == 0 && i + 1 < argc) {
            module_path = argv[++i];
        } else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc) {
            method = argv[++i];
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-finit-module: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!module_path) {
        fprintf(stderr, "fenix-finit-module: --module is required\n");
        usage(argv[0]);
        return 1;
    }

    if (geteuid() != 0) {
        fprintf(stderr, "fenix-finit-module: must be run as root\n");
        return 1;
    }

    int fd = -1;

    if (strcmp(method, "finit_module") == 0) {
        fd = open(module_path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) {
            perror("open module");
            return 1;
        }
    } else if (strcmp(method, "memfd-finit-module") == 0) {
        size_t len = 0;
        unsigned char *image = fenix_read_file(module_path, &len);
        if (!image)
            return 1;

        fd = fenix_create_memfd("fenix_lkm");
        if (fd < 0) {
            perror("memfd_create");
            free(image);
            return 1;
        }

        if (fenix_write_all(fd, image, len) != 0) {
            close(fd);
            free(image);
            return 1;
        }
        free(image);

        if (lseek(fd, 0, SEEK_SET) != 0) {
            perror("lseek memfd");
            close(fd);
            return 1;
        }
    } else {
        fprintf(stderr, "fenix-finit-module: unknown method '%s'\n", method);
        usage(argv[0]);
        return 1;
    }

    long rc = syscall(SYS_finit_module, fd, "", 0);
    close(fd);

    if (rc != 0) {
        perror("finit_module");
        return 1;
    }

    fprintf(stderr, "fenix-finit-module: module loaded successfully\n");
    return 0;
}
