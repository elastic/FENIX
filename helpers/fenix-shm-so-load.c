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
 * fenix-shm-so-load — dlopen a .so from POSIX shared memory (tmpfs). Linux-only.
 */
#include "fenix-common.h"

#include <dlfcn.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --module <path.so> [--symbol <name>] [--name <shm_name>]\n",
            prog);
}

int main(int argc, char **argv)
{
    const char *module_path = NULL;
    const char *symbol = "fenix_hello";
    const char *shm_name = "fenix_shm_module";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--module") == 0 && i + 1 < argc)
            module_path = argv[++i];
        else if (strcmp(argv[i], "--symbol") == 0 && i + 1 < argc)
            symbol = argv[++i];
        else if (strcmp(argv[i], "--name") == 0 && i + 1 < argc)
            shm_name = argv[++i];
        else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-shm-so-load: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!module_path) {
        fprintf(stderr, "fenix-shm-so-load: --module is required\n");
        usage(argv[0]);
        return 1;
    }

    size_t len = 0;
    unsigned char *image = fenix_read_file(module_path, &len);
    if (!image)
        return 1;

    char shm_path[256];
    snprintf(shm_path, sizeof(shm_path), "/%s", shm_name[0] == '/' ? shm_name + 1 : shm_name);

    int shm_fd = shm_open(shm_path, O_RDWR | O_CREAT | O_TRUNC, 0700);
    if (shm_fd < 0) {
        perror("shm_open");
        free(image);
        return 1;
    }

    if (ftruncate(shm_fd, (off_t)len) != 0) {
        perror("ftruncate");
        free(image);
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }

    if (fenix_write_all(shm_fd, image, len) != 0) {
        free(image);
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }
    free(image);

    char disk_path[512];
    snprintf(disk_path, sizeof(disk_path), "/dev/shm%s", shm_path);

    void *handle = dlopen(disk_path, RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "fenix-shm-so-load: dlopen failed: %s\n", dlerror());
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }

    void (*fn)(void) = (void (*)(void))dlsym(handle, symbol);
    if (!fn) {
        fprintf(stderr, "fenix-shm-so-load: dlsym(%s) failed: %s\n", symbol, dlerror());
        dlclose(handle);
        close(shm_fd);
        shm_unlink(shm_path);
        return 1;
    }

    fn();
    dlclose(handle);
    close(shm_fd);
    shm_unlink(shm_path);
    fprintf(stderr, "fenix-shm-so-load: symbol '%s' invoked successfully\n", symbol);
    return 0;
}
