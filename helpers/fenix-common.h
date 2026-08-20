/*
 * fenix-common.h — Shared helpers for FENIX C binaries (Linux-only).
 */
#ifndef FENIX_COMMON_H
#define FENIX_COMMON_H

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/sendfile.h>
#include <sys/stat.h>
#include <unistd.h>

#ifdef __linux__
#include <linux/memfd.h>
#include <sys/syscall.h>
#endif

#ifndef MFD_CLOEXEC
#define MFD_CLOEXEC 0x0001U
#endif

#ifndef MFD_NOEXEC_SEAL
#define MFD_NOEXEC_SEAL 0x0008U
#endif

#ifndef AT_EMPTY_PATH
#define AT_EMPTY_PATH 0x1000
#endif

static inline int fenix_create_memfd_flags(const char *name, unsigned int flags)
{
#ifdef __NR_memfd_create
    return (int)syscall(__NR_memfd_create, name, flags);
#else
    errno = ENOSYS;
    return -1;
#endif
}

/** Anonymous memfd closed on exec (typical ELF-in-memfd PoCs). */
static inline int fenix_create_memfd(const char *name)
{
    return fenix_create_memfd_flags(name, MFD_CLOEXEC);
}

/** Memfd kept across exec — required for shebang scripts on /proc/self/fd/N. */
static inline int fenix_create_memfd_inheritable(const char *name)
{
    return fenix_create_memfd_flags(name, 0);
}

static inline unsigned char *fenix_read_file(const char *path, size_t *out_len)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return NULL;
    }

    struct stat st;
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0) {
        fprintf(stderr, "fenix: not a regular file with content: %s\n", path);
        close(fd);
        return NULL;
    }

    size_t len = (size_t)st.st_size;
    unsigned char *buf = malloc(len);
    if (!buf) {
        perror("malloc");
        close(fd);
        return NULL;
    }

    ssize_t n = read(fd, buf, len);
    close(fd);
    if (n < 0 || (size_t)n != len) {
        perror("read");
        free(buf);
        return NULL;
    }

    *out_len = len;
    return buf;
}

/** Copy len bytes from in_fd to out_fd using sendfile(2). */
static inline int fenix_sendfile_all(int out_fd, int in_fd, size_t len)
{
    off_t offset = 0;

    while ((size_t)offset < len) {
        ssize_t n = sendfile(out_fd, in_fd, &offset, len - (size_t)offset);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            perror("sendfile");
            return -1;
        }
        if (n == 0) {
            fprintf(stderr, "fenix: sendfile short write\n");
            return -1;
        }
    }
    return 0;
}

static inline int fenix_write_all(int fd, const void *buf, size_t len)
{
    const unsigned char *p = buf;
    size_t off = 0;

    while (off < len) {
        ssize_t n = write(fd, p + off, len - off);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            perror("write");
            return -1;
        }
        off += (size_t)n;
    }
    return 0;
}

#endif /* FENIX_COMMON_H */
