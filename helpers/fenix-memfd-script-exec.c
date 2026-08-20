/*
 * fenix-memfd-script-exec — Execute a script from an anonymous memfd (lab PoC).
 * Linux-only.
 */

#include "fenix-common.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s (--script-file <path> | --content <text>) --name <memfd_name>\n"
            "       [--interpreter <path>] [--method shebang|interpreter-procfs|fexecve-interpreter]\n",
            prog);
}

static char *read_script_file(const char *path, size_t *out_len)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open script-file");
        return NULL;
    }

    struct stat st;
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0) {
        fprintf(stderr, "fenix-memfd-script-exec: invalid script file\n");
        close(fd);
        return NULL;
    }

    size_t len = (size_t)st.st_size;
    char *buf = malloc(len + 1);
    if (!buf) {
        close(fd);
        return NULL;
    }

    ssize_t n = read(fd, buf, len);
    close(fd);
    if (n < 0 || (size_t)n != len) {
        perror("read script-file");
        free(buf);
        return NULL;
    }
    buf[len] = '\0';
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
            perror("write memfd");
            return -1;
        }
        off += (size_t)n;
    }
    return 0;
}

static int has_shebang(const char *content, size_t len)
{
    return len >= 2 && content[0] == '#' && content[1] == '!';
}

/* awk treats argv[1] as a *data* file and blocks on stdin; needs -f for program source. */
static int interpreter_is_awk(const char *path)
{
    const char *base = strrchr(path, '/');
    base = base ? base + 1 : path;
    return strcmp(base, "awk") == 0 || strcmp(base, "gawk") == 0 ||
           strcmp(base, "mawk") == 0 || strcmp(base, "nawk") == 0;
}

static int exec_interpreter_on_fd(const char *interpreter, const char *method,
                                  const char *fd_path, int mfd)
{
    char *argv_pos[] = { (char *)interpreter, (char *)fd_path, NULL };
    char *argv_awk[] = { (char *)interpreter, "-f", (char *)fd_path, NULL };
    char **argv_exec = interpreter_is_awk(interpreter) ? argv_awk : argv_pos;

    if (strcmp(method, "fexecve-interpreter") == 0) {
        fexecve(mfd, argv_exec, environ);
        perror("fexecve-interpreter");
    } else {
        execve(interpreter, argv_exec, environ);
        perror("execve interpreter-procfs");
    }
    return -1;
}

int main(int argc, char **argv)
{
    const char *script_file = NULL;
    const char *content = NULL;
    const char *memfd_name = "fenix_script";
    const char *interpreter = NULL;
    const char *method = "shebang";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--script-file") == 0 && i + 1 < argc) {
            script_file = argv[++i];
        } else if (strcmp(argv[i], "--content") == 0 && i + 1 < argc) {
            content = argv[++i];
        } else if (strcmp(argv[i], "--name") == 0 && i + 1 < argc) {
            memfd_name = argv[++i];
        } else if (strcmp(argv[i], "--interpreter") == 0 && i + 1 < argc) {
            interpreter = argv[++i];
        } else if (strcmp(argv[i], "--method") == 0 && i + 1 < argc) {
            method = argv[++i];
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "fenix-memfd-script-exec: unknown option: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    size_t len = 0;
    char *script = NULL;
    int script_is_malloc = 0;

    if (script_file) {
        script = read_script_file(script_file, &len);
        script_is_malloc = 1;
        if (!script)
            return 1;
    } else if (content) {
        len = strlen(content);
        script = (char *)content;
    } else {
        fprintf(stderr, "fenix-memfd-script-exec: --script-file or --content required\n");
        usage(argv[0]);
        return 1;
    }

    int had_shebang = has_shebang(script, len);

    if (!interpreter && !had_shebang) {
        fprintf(stderr,
                "fenix-memfd-script-exec: script has no shebang; pass --interpreter\n");
        if (script_is_malloc)
            free(script);
        return 1;
    }

    /* Shebang interpreters must reopen /proc/self/fd/N — do not use MFD_CLOEXEC. */
    int mfd = fenix_create_memfd_inheritable(memfd_name);
    if (mfd < 0) {
        perror("memfd_create");
        if (script_is_malloc)
            free(script);
        return 1;
    }

    if (write_all(mfd, script, len) != 0) {
        close(mfd);
        if (script_is_malloc)
            free(script);
        return 1;
    }
    if (script_is_malloc)
        free(script);

    if (lseek(mfd, 0, SEEK_SET) != 0) {
        perror("lseek memfd");
        close(mfd);
        return 1;
    }

    char fd_path[64];
    snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", mfd);

    if (interpreter && strcmp(method, "shebang") != 0) {
        exec_interpreter_on_fd(interpreter, method, fd_path, mfd);
        close(mfd);
        return 1;
    }

    if (had_shebang && strcmp(method, "shebang") == 0) {
        char *argv_exec[] = { fd_path, NULL };
        execve(fd_path, argv_exec, environ);
        perror("execve shebang");
        close(mfd);
        return 1;
    }

    if (interpreter) {
        exec_interpreter_on_fd(interpreter, "interpreter-procfs", fd_path, mfd);
    } else {
        fprintf(stderr, "fenix-memfd-script-exec: no interpreter available\n");
    }

    close(mfd);
    return 1;
}
