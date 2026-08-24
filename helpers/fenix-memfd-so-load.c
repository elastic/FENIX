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
 * fenix-memfd-so-load — dlopen a shared object from memfd (reflective load lab PoC).
 * Linux-only. Loads a benign .so and calls a named symbol.
 */

#include "fenix-common.h"

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --module <path.so> [--symbol <name>] [--name <memfd_name>]\n",
            prog);
}

int main(int argc, char **argv)
{
    const char *module_path = NULL;
    const char *symbol = "fenix_hello";
    const char *memfd_name = "fenix_module";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--module") == 0 && i + 1 < argc) {
            module_path = argv[++i];
        } else if (strcmp(argv[i], "--symbol") == 0 && i + 1 < argc) {
            symbol = argv[++i];
        } else if (strcmp(argv[i], "--name") == 0 && i + 1 < argc) {
            memfd_name = argv[++i];
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-memfd-so-load: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!module_path) {
        fprintf(stderr, "fenix-memfd-so-load: --module is required\n");
        usage(argv[0]);
        return 1;
    }

    size_t len = 0;
    unsigned char *image = fenix_read_file(module_path, &len);
    if (!image)
        return 1;

    int mfd = fenix_create_memfd(memfd_name);
    if (mfd < 0) {
        perror("memfd_create");
        free(image);
        return 1;
    }

    if (fenix_write_all(mfd, image, len) != 0) {
        free(image);
        close(mfd);
        return 1;
    }
    free(image);

    char fd_path[64];
    snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", mfd);

    void *handle = dlopen(fd_path, RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "fenix-memfd-so-load: dlopen failed: %s\n", dlerror());
        close(mfd);
        return 1;
    }

    void (*fn)(void) = (void (*)(void))dlsym(handle, symbol);
    if (!fn) {
        fprintf(stderr, "fenix-memfd-so-load: dlsym(%s) failed: %s\n", symbol, dlerror());
        dlclose(handle);
        close(mfd);
        return 1;
    }

    fn();
    dlclose(handle);
    close(mfd);
    fprintf(stderr, "fenix-memfd-so-load: symbol '%s' invoked successfully\n", symbol);
    return 0;
}
