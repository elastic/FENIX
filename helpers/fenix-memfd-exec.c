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
 * fenix-memfd-exec — Execute ELF from anonymous memfd (lab PoC). Linux-only.
 */
#include "fenix-common.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --payload <path> [--name <memfd_name>]\n"
            "       [--method procfs-fd|fexecve|execveat] [--argv0 <name>]\n"
            "       [--ingest write|sendfile] [--fchmod] [--noexec-seal]\n",
            prog);
}

static int load_payload_to_memfd(const char *payload_path, int mfd, const char *ingest)
{
    int src = open(payload_path, O_RDONLY);
    if (src < 0) {
        perror("open payload");
        return -1;
    }

    struct stat st;
    if (fstat(src, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0) {
        fprintf(stderr, "fenix-memfd-exec: invalid payload file\n");
        close(src);
        return -1;
    }

    size_t len = (size_t)st.st_size;
    int rc = -1;

    if (strcmp(ingest, "sendfile") == 0) {
        rc = fenix_sendfile_all(mfd, src, len);
    } else if (strcmp(ingest, "write") == 0) {
        unsigned char *data = malloc(len);
        if (!data) {
            perror("malloc");
            close(src);
            return -1;
        }
        ssize_t n = read(src, data, len);
        close(src);
        if (n < 0 || (size_t)n != len) {
            perror("read");
            free(data);
            return -1;
        }
        rc = fenix_write_all(mfd, data, len);
        free(data);
        return rc;
    } else {
        fprintf(stderr, "fenix-memfd-exec: unknown ingest '%s'\n", ingest);
        close(src);
        return -1;
    }

    close(src);
    return rc;
}

int main(int argc, char **argv)
{
    const char *payload_path = NULL;
    const char *memfd_name = "fenix_payload";
    const char *method = "procfs-fd";
    const char *argv0_override = NULL;
    const char *ingest = "write";
    int do_fchmod = 0;
    int try_noexec_seal = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc)
            payload_path = argv[++i];
        else if (strcmp(argv[i], "--name") == 0 && i + 1 < argc)
            memfd_name = argv[++i];
        else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc)
            method = argv[++i];
        else if (strcmp(argv[i], "--argv0") == 0 && i + 1 < argc)
            argv0_override = argv[++i];
        else if (strcmp(argv[i], "--ingest") == 0 && i + 1 < argc)
            ingest = argv[++i];
        else if (strcmp(argv[i], "--fchmod") == 0)
            do_fchmod = 1;
        else if (strcmp(argv[i], "--noexec-seal") == 0)
            try_noexec_seal = 1;
        else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-memfd-exec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!payload_path) {
        fprintf(stderr, "fenix-memfd-exec: --payload is required\n");
        usage(argv[0]);
        return 1;
    }

    unsigned int mfd_flags = MFD_CLOEXEC;
    if (try_noexec_seal)
        mfd_flags = MFD_NOEXEC_SEAL;

    int mfd = fenix_create_memfd_flags(memfd_name, mfd_flags);
    if (mfd < 0) {
        if (try_noexec_seal) {
            fprintf(stderr,
                    "fenix-memfd-exec: MFD_NOEXEC_SEAL unsupported on this kernel "
                    "(try without --noexec-seal)\n");
        }
        perror("memfd_create");
        return 1;
    }

    if (load_payload_to_memfd(payload_path, mfd, ingest) != 0) {
        close(mfd);
        return 1;
    }

    if (do_fchmod && fchmod(mfd, 0755) != 0) {
        if (try_noexec_seal) {
            fprintf(stderr,
                    "fenix-memfd-exec: fchmod(0755) denied on MFD_NOEXEC_SEAL memfd "
                    "(expected — seal blocks exec bypass)\n");
            fprintf(stderr,
                    "  See sysctl / lab hints printed below by the fenix CLI.\n");
        } else {
            perror("fchmod");
        }
        close(mfd);
        return try_noexec_seal ? 2 : 1;
    }

    if (lseek(mfd, 0, SEEK_SET) != 0) {
        perror("lseek");
        close(mfd);
        return 1;
    }

    const char *display = argv0_override ? argv0_override : memfd_name;
    char fd_path[64];
    char *exec_argv[] = { (char *)display, NULL };

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
        fprintf(stderr, "fenix-memfd-exec: unknown method '%s'\n", method);
        close(mfd);
        return 1;
    }

    close(mfd);
    return 1;
}
