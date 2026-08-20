import os
import sys

MFD_CLOEXEC = 1
fd = os.memfd_create("", MFD_CLOEXEC)
if fd < 0:
    raise OSError("memfd_create failed")
os.write(fd, sys.stdin.buffer.read())
os.execve(f"/proc/self/fd/{fd}", ["__FENIX_ARGV0__"], os.environ)
