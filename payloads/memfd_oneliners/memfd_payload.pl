use strict;
use warnings;
my @fds = (__FENIX_MEMFD_SYSCALL__);
my $name = "";
my $f;
for my $nr (@fds) {
    my $r = syscall($nr, $name, 1);
    if ($r > 0) { $f = $r; last }
}
die "memfd_create failed\n" unless defined $f;
open(my $o, ">&=", $f) or die "dup failed\n";
binmode STDIN;
print $o do { local $/; <STDIN> };
exec {"/proc/$$/fd/$f"} "__FENIX_ARGV0__" or die "exec failed: $!\n";
