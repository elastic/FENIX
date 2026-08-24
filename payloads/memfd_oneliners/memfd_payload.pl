# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch B.V. licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
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
