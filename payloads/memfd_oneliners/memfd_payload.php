<?php
if (!class_exists("FFI")) {
    fwrite(STDERR, "php memfd lab requires FFI (e.g. apt install php-ffi)\n");
    exit(1);
}
if (!function_exists("pcntl_exec")) {
    fwrite(STDERR, "php memfd lab requires pcntl (e.g. apt install php-cli with pcntl)\n");
    exit(1);
}

$libc = FFI::cdef(
    "int memfd_create(const char *name, unsigned int flags);
     ssize_t write(int fd, const void *buf, size_t count);
     int fchmod(int fd, int mode);",
    "libc.so.6"
);

$fd = $libc->memfd_create("", 1);
if ($fd < 0) {
    fwrite(STDERR, "memfd_create failed\n");
    exit(1);
}

$elf = stream_get_contents(STDIN);
if ($elf === false || $elf === "") {
    fwrite(STDERR, "no stdin payload\n");
    exit(1);
}

$len = strlen($elf);
$buf = FFI::new("char[$len]");
FFI::memcpy($buf, $elf, $len);
$written = $libc->write($fd, FFI::addr($buf), $len);
if ($written < 0 || (int) $written !== $len) {
    fwrite(STDERR, "write to memfd failed\n");
    exit(1);
}

if ($libc->fchmod($fd, 0755) < 0) {
    fwrite(STDERR, "fchmod memfd failed\n");
    exit(1);
}

$path = "/proc/self/fd/$fd";
pcntl_exec($path, ["__FENIX_ARGV0__"]);
fwrite(STDERR, "pcntl_exec failed\n");
exit(1);
