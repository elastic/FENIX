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
 * fenix-pipe-exec — Execute ELF or script via pipe (lab PoC). Linux-only.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --type elf --payload <path>\n"
            "       %s --type script (--script-file <path> | --content <text>) --interpreter <path>\n",
            prog, prog);
}

static unsigned char *read_file(const char *path, size_t *out_len)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return NULL;
    }

    struct stat st;
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0) {
        fprintf(stderr, "fenix-pipe-exec: invalid file\n");
        close(fd);
        return NULL;
    }

    size_t len = (size_t)st.st_size;
    unsigned char *buf = malloc(len);
    if (!buf) {
        close(fd);
        return NULL;
    }

    ssize_t n = read(fd, buf, len);
    close(fd);
    if (n < 0 || (size_t)n != len) {
        free(buf);
        return NULL;
    }
    *out_len = len;
    return buf;
}

static int write_all(int fd, const void *buf, size_t len)
{
    const unsigned char *p = buf;
    size_t off = 0;
    while (off < len) {
        ssize_t n = write(fd, p + off, len - off);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            perror("write pipe");
            return -1;
        }
        off += (size_t)n;
    }
    return 0;
}

static int exec_elf_pipe(const unsigned char *data, size_t len)
{
    int fds[2];
    if (pipe(fds) != 0) {
        perror("pipe");
        return 1;
    }

    if (write_all(fds[1], data, len) != 0) {
        close(fds[0]);
        close(fds[1]);
        return 1;
    }
    close(fds[1]);

    if (fchmod(fds[0], 0755) != 0) {
        perror("fchmod pipe");
        close(fds[0]);
        return 1;
    }

    char *argv_exec[] = { "fenix_pipe_elf", NULL };
    fexecve(fds[0], argv_exec, environ);
    if (errno == EPERM) {
        fprintf(stderr,
                "fenix-pipe-exec: fexecve from pipe fd denied (EPERM — common on Linux 5.x+ / hardened VMs)\n");
        fprintf(stderr,
                "  Lab OK: strace still shows pipe → write → fchmod → fexecve (distinct from memfd-exec)\n");
        fprintf(stderr,
                "  For hello output: fenix run memfd-exec --payload <elf> --method fexecve\n");
        fprintf(stderr,
                "  Or: fenix run pipe-exec --type script --interpreter python3 --code 'print(\"hello\")'\n");
    } else {
        perror("fexecve pipe");
    }
    close(fds[0]);
    return 1;
}

static int exec_script_pipe(const char *data, size_t len, const char *interpreter)
{
    int fds[2];
    if (pipe(fds) != 0) {
        perror("pipe");
        return 1;
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        close(fds[0]);
        close(fds[1]);
        return 1;
    }

    if (pid == 0) {
        close(fds[1]);
        if (dup2(fds[0], STDIN_FILENO) < 0) {
            perror("dup2 stdin");
            _exit(127);
        }
        close(fds[0]);
        char *argv_exec[] = { (char *)interpreter, NULL };
        execve(interpreter, argv_exec, environ);
        perror("execve interpreter");
        _exit(127);
    }

    close(fds[0]);
    if (write_all(fds[1], data, len) != 0) {
        close(fds[1]);
        return 1;
    }
    close(fds[1]);

    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return 1;
    }
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return 1;
}

int main(int argc, char **argv)
{
    const char *type = "elf";
    const char *payload = NULL;
    const char *script_file = NULL;
    const char *content = NULL;
    const char *interpreter = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--type") == 0 && i + 1 < argc) {
            type = argv[++i];
        } else if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc) {
            payload = argv[++i];
        } else if (strcmp(argv[i], "--script-file") == 0 && i + 1 < argc) {
            script_file = argv[++i];
        } else if (strcmp(argv[i], "--content") == 0 && i + 1 < argc) {
            content = argv[++i];
        } else if (strcmp(argv[i], "--interpreter") == 0 && i + 1 < argc) {
            interpreter = argv[++i];
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-pipe-exec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (strcmp(type, "elf") == 0) {
        if (!payload) {
            fprintf(stderr, "fenix-pipe-exec: --payload required for type elf\n");
            return 1;
        }
        size_t len = 0;
        unsigned char *data = read_file(payload, &len);
        if (!data)
            return 1;
        int rc = exec_elf_pipe(data, len);
        free(data);
        return rc;
    }

    if (strcmp(type, "script") == 0) {
        if (!interpreter) {
            fprintf(stderr, "fenix-pipe-exec: --interpreter required for type script\n");
            return 1;
        }
        size_t len = 0;
        unsigned char *data = NULL;
        if (script_file) {
            data = read_file(script_file, &len);
        } else if (content) {
            len = strlen(content);
            data = (unsigned char *)content;
        } else {
            fprintf(stderr, "fenix-pipe-exec: --script-file or --content required\n");
            return 1;
        }
        if (!data)
            return 1;
        int rc = exec_script_pipe((const char *)data, len, interpreter);
        if (script_file && data)
            free(data);
        return rc;
    }

    fprintf(stderr, "fenix-pipe-exec: unknown type '%s'\n", type);
    return 1;
}
