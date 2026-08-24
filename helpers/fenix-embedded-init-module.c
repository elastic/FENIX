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
