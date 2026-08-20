require "fcntl"
SYS_memfd_create = __FENIX_MEMFD_SYSCALL__
fd = syscall(SYS_memfd_create, "", 1)
raise "memfd_create failed" if fd.nil? || fd <= 0
data = $stdin.read
# Keep memfd open: do not File.open(fd) { ... } (block closes fd → ENOENT on exec).
io = IO.new(fd, File::WRONLY)
io.autoclose = false if io.respond_to?(:autoclose=)
io.write(data)
io.flush
Fcntl.fchmod(fd, 0o755)
exec("/proc/self/fd/#{fd}", "__FENIX_ARGV0__")
