/*
 * fenix-deleted-exec — Copy payload to path, exec, then unlink (lab PoC helper).
 * Linux-only.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s --payload <path> --path <target> [--args <argstring>]\n"
            "       [--wait | --no-wait]\n",
            prog);
}

static int copy_file(const char *src, const char *dst)
{
    int in = open(src, O_RDONLY);
    if (in < 0) {
        perror("open payload");
        return -1;
    }

    int out = open(dst, O_WRONLY | O_CREAT | O_TRUNC, 0700);
    if (out < 0) {
        perror("open target");
        close(in);
        return -1;
    }

    char buf[8192];
    ssize_t n;
    while ((n = read(in, buf, sizeof(buf))) > 0) {
        ssize_t w = write(out, buf, (size_t)n);
        if (w != n) {
            perror("write target");
            close(in);
            close(out);
            return -1;
        }
    }

    if (n < 0) {
        perror("read payload");
        close(in);
        close(out);
        return -1;
    }

    close(in);
    close(out);
    return 0;
}

static char **split_args(const char *argstring, int *out_count)
{
    if (!argstring || argstring[0] == '\0') {
        *out_count = 0;
        return NULL;
    }

    char *copy = strdup(argstring);
    if (!copy)
        return NULL;

    int cap = 8;
    int count = 0;
    char **argv = calloc((size_t)cap, sizeof(char *));
    if (!argv) {
        free(copy);
        return NULL;
    }

    char *save = NULL;
    for (char *tok = strtok_r(copy, " ", &save); tok; tok = strtok_r(NULL, " ", &save)) {
        if (count + 1 >= cap) {
            cap *= 2;
            char **tmp = realloc(argv, (size_t)cap * sizeof(char *));
            if (!tmp) {
                free(copy);
                free(argv);
                return NULL;
            }
            argv = tmp;
        }
        argv[count++] = strdup(tok);
    }

    free(copy);
    *out_count = count;
    return argv;
}

static void free_argv(char **argv, int count)
{
    if (!argv)
        return;
    for (int i = 0; i < count; i++)
        free(argv[i]);
    free(argv);
}

int main(int argc, char **argv)
{
    const char *payload_path = NULL;
    const char *target_path = NULL;
    const char *extra_args = NULL;
    int do_wait = 1;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc) {
            payload_path = argv[++i];
        } else if (strcmp(argv[i], "--path") == 0 && i + 1 < argc) {
            target_path = argv[++i];
        } else if (strcmp(argv[i], "--args") == 0 && i + 1 < argc) {
            extra_args = argv[++i];
        } else if (strcmp(argv[i], "--wait") == 0) {
            do_wait = 1;
        } else if (strcmp(argv[i], "--no-wait") == 0) {
            do_wait = 0;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-deleted-exec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!payload_path || !target_path) {
        fprintf(stderr, "fenix-deleted-exec: --payload and --path are required\n");
        usage(argv[0]);
        return 1;
    }

    if (copy_file(payload_path, target_path) != 0)
        return 1;

    if (chmod(target_path, 0700) != 0) {
        perror("chmod");
        unlink(target_path);
        return 1;
    }

    int extra_count = 0;
    char **extra_argv = split_args(extra_args, &extra_count);

    int total = 1 + extra_count;
    char **exec_argv = calloc((size_t)(total + 1), sizeof(char *));
    if (!exec_argv) {
        perror("calloc");
        free_argv(extra_argv, extra_count);
        unlink(target_path);
        return 1;
    }

    exec_argv[0] = strdup(target_path);
    for (int i = 0; i < extra_count; i++)
        exec_argv[i + 1] = extra_argv[i];
    exec_argv[total] = NULL;
    free(extra_argv);

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        free_argv(exec_argv, total);
        unlink(target_path);
        return 1;
    }

    if (pid == 0) {
        /*
         * Open before unlink so the inode stays valid, then execute via fexecve
         * after removing the directory entry (deleted-file execution pattern).
         */
        int fd = open(target_path, O_RDONLY);
        if (fd < 0) {
            perror("open target");
            _exit(127);
        }
        if (unlink(target_path) != 0) {
            perror("unlink");
            close(fd);
            _exit(127);
        }
        fexecve(fd, exec_argv, environ);
        perror("fexecve");
        close(fd);
        _exit(127);
    }

    free_argv(exec_argv, total);

    if (!do_wait)
        return 0;

    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return 1;
    }

    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return 1;
}
