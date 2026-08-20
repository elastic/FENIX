# FENIX examples

**45** YAML configs under `examples/`. One primary example per **technique module** where possible; extra files only when they exercise a **distinct detection surface** (different syscall, staging transform, or process chain).

For bulk alert testing without picking files individually, use **`fenix run-all`** ([docs/LAB_MATRIX.md](../docs/LAB_MATRIX.md)).

> **STOP — remote staging templates will not run as checked in.**
> `fileless_staging_remote.yaml` and `fileless_staging_remote_curl.yaml` use
> `https://YOUR-LAB-HOST/...` **on purpose**. FENIX refuses that placeholder at
> runtime. Copy the file and put in a host you control, or switch
> `remote_backend` to a named adapter (`uguu` | `tmpfiles` | `catbox` | `pastebin`).
> See [docs/STAGING_REMOTE.md](../docs/STAGING_REMOTE.md).

## Index

| Example | Technique | Unique telemetry / hunt focus |
|---------|-----------|------------------------------|
| [memfd_exec.yaml](memfd_exec.yaml) | `memfd-exec` | `memfd_create`, `execve` via `/proc/self/fd/N`, custom `argv0` |
| [memfd_exec_fchmod.yaml](memfd_exec_fchmod.yaml) | `memfd-exec` | `fchmod` on memfd before exec (sympy-dev-style) |
| [memfd_exec_execveat.yaml](memfd_exec_execveat.yaml) | `memfd-exec` | `execveat` + `AT_EMPTY_PATH` on memfd fd (QLNX-style) |
| [memfd_exec_sendfile.yaml](memfd_exec_sendfile.yaml) | `memfd-exec` | `sendfile` ingest into memfd (distinct from `write`) |
| [memfd_exec_noexec_seal.yaml](memfd_exec_noexec_seal.yaml) | `memfd-exec` | `MFD_NOEXEC_SEAL` + `fchmod` hardening lab |
| [shm_exec.yaml](shm_exec.yaml) | `shm-exec` | `shm_open` on `/dev/shm`, `sendfile`, `fexecve` |
| [shm_so_load.yaml](shm_so_load.yaml) | `shm-so-load` | `dlopen` from `/dev/shm` path (no memfd) |
| [stdin_memexec.yaml](stdin_memexec.yaml) | `stdin-memexec` | File-backed lab run; use `cat elf \| fenix run stdin-memexec` for pipe |
| [memfd_script_shebang.yaml](memfd_script_shebang.yaml) | `memfd-script-exec` | Script in memfd, kernel shebang dispatch (`hello_shebang.sh`, `#!/bin/sh`) |
| [memfd_script_interpreter_python.yaml](memfd_script_interpreter_python.yaml) | `memfd-script-exec` | `python3` + `hello.py` via `/proc/self/fd/N` |
| [memfd_script_interpreter_awk.yaml](memfd_script_interpreter_awk.yaml) | `memfd-script-exec` | `awk` + `hello.awk` (not shell script) |
| [memfd_script_node_shebang.yaml](memfd_script_node_shebang.yaml) | `memfd-script-exec` | Node via shebang (`hello.js`); avoid interpreter-procfs for node |
| [memfd_self_reexec.yaml](memfd_self_reexec.yaml) | `memfd-self-reexec` | Copy `/proc/self/exe` → memfd → unlink disk → re-exec |
| [memfd_so_load.yaml](memfd_so_load.yaml) | `memfd-so-load` | `dlopen` / `dlsym` on `/proc/self/fd` `.so` (reflective load) |
| [fileless_staging_http_b64.yaml](fileless_staging_http_b64.yaml) | `fileless-staging` | HTTP GET, base64 decode, temp staging file, memfd exec |
| [fileless_staging_remote.yaml](fileless_staging_remote.yaml) | `fileless-staging` | **TEMPLATE — edit YOUR-LAB-HOST** (or named `--remote-backend`) |
| [fileless_staging_remote_curl.yaml](fileless_staging_remote_curl.yaml) | `fileless-staging` | **TEMPLATE** same chain; download with `curl` |
| [fileless_staging_http_lab.yaml](fileless_staging_http_lab.yaml) | `fileless-staging` | `lab_remote: hello-b64` (GitHub raw preset) |
| [fileless_staging_http_xor_lab.yaml](fileless_staging_http_xor_lab.yaml) | `fileless-staging` | `lab_remote: hello-xor` |
| [fileless_staging_http_interpreter_lab.yaml](fileless_staging_http_interpreter_lab.yaml) | `fileless-staging` | `lab_remote: hello-py` |
| [fileless_staging_interpreter.yaml](fileless_staging_interpreter.yaml) | `fileless-staging` | Local read → staged bytes → interpreter stdin (no memfd ELF) |
| [fileless_staging_xor.yaml](fileless_staging_xor.yaml) | `fileless-staging` | XOR decode transform before memfd exec |
| [pipe_exec_elf.yaml](pipe_exec_elf.yaml) | `pipe-exec` | `pipe` + `fexecve` (no memfd) |
| [pipe_exec_script.yaml](pipe_exec_script.yaml) | `pipe-exec` | `pipe` → interpreter stdin |
| [proc_fd_exec.yaml](proc_fd_exec.yaml) | `proc-fd-exec` | Regular file fd + unlink + `fexecve` (not memfd-backed) |
| [deleted_file_exec.yaml](deleted_file_exec.yaml) | `deleted-file-exec` | Path on disk removed while process runs |
| [interpreter_oneliner.yaml](interpreter_oneliner.yaml) | `interpreter-exec` | `python3 -c` one-liner |
| [interpreter_bash_stdin.yaml](interpreter_bash_stdin.yaml) | `interpreter-exec` | `bash` with script on stdin (distinct from `-c`) |
| [interpreter_memfd_perl_oneliner.yaml](interpreter_memfd_perl_oneliner.yaml) | `interpreter-memfd-exec` | `perl -e` memfd loader |
| [interpreter_memfd_perl_script.yaml](interpreter_memfd_perl_script.yaml) | `interpreter-memfd-exec` | `perl memfd_payload.pl` |
| [interpreter_memfd_python3_oneliner.yaml](interpreter_memfd_python3_oneliner.yaml) | `interpreter-memfd-exec` | `python3 -c` memfd loader |
| [interpreter_memfd_python3_script.yaml](interpreter_memfd_python3_script.yaml) | `interpreter-memfd-exec` | `python3 memfd_payload.py` |
| [interpreter_memfd_php_oneliner.yaml](interpreter_memfd_php_oneliner.yaml) | `interpreter-memfd-exec` | `php -r` memfd loader |
| [interpreter_memfd_php_script.yaml](interpreter_memfd_php_script.yaml) | `interpreter-memfd-exec` | `php memfd_payload.php` |
| [interpreter_memfd_ruby.yaml](interpreter_memfd_ruby.yaml) | `interpreter-memfd-exec` | `ruby -e` (default one-liner) |
| [lolbin_ld_linux.yaml](lolbin_ld_linux.yaml) | `lolbin-fd-exec` | `ld-linux-x86-64.so.2` + ELF via `/proc/self/fd/N` |
| [lolbin_busybox.yaml](lolbin_busybox.yaml) | `lolbin-fd-exec` | `busybox sh` + script via `/proc/self/fd/N` |
| [lolbin_julia.yaml](lolbin_julia.yaml) | `lolbin-fd-exec` | `julia` + script via `/proc/self/fd/N` |
| [lolbin_erlang.yaml](lolbin_erlang.yaml) | `lolbin-fd-exec` | `escript` + Erlang script via `/proc/self/fd/N` |
| [lkm_load_finit.yaml](lkm_load_finit.yaml) | `lkm-load` | `finit_module` syscall (open .ko fd) |
| [lkm_load_init.yaml](lkm_load_init.yaml) | `lkm-load` | `init_module` heap buffer |
| [lkm_load_memfd_init.yaml](lkm_load_memfd_init.yaml) | `lkm-load` | memfd → mmap → `init_module` |
| [lkm_load_memfd_init_fork.yaml](lkm_load_memfd_init_fork.yaml) | `lkm-load` | memfd → fork → child `init_module` |
| [lkm_load_memfd_finit.yaml](lkm_load_memfd_finit.yaml) | `lkm-load` | memfd → `finit_module` |
| [lkm_load_embedded.yaml](lkm_load_embedded.yaml) | `lkm-load` | embedded `.ko` → `init_module` |

## Removed / merged (duplicates)

| Former file | Reason |
|-------------|--------|
| `perl_oneliner.yaml` | Same telemetry as `interpreter_oneliner.yaml` (only interpreter name differed) |
| `fileless_staging_local.yaml` | End state duplicated `memfd_exec.yaml` (procfs-fd, same ELF) |
| `memfd_script_exec.yaml` | Replaced by `memfd_script_shebang.yaml` (clearer distinct surface vs interpreter-exec) |
| `fileless_staging_pastebin.yaml` | Renamed to `fileless_staging_http_b64.yaml` |
| `lkm_load.yaml` | Split into `lkm_load_finit.yaml` / `lkm_load_init.yaml` for distinct syscalls |
| `memfd_exec_explain.yaml` | Walkthrough is on by default; duplicated `memfd_exec.yaml` |
| `interpreter_memfd_perl.yaml` | Alias of `interpreter_memfd_perl_oneliner.yaml` |
| `interpreter_memfd_python3.yaml` | Alias of `interpreter_memfd_python3_oneliner.yaml` |

## Run any example

```bash
export FENIX_BIN_DIR=$PWD/bin
fenix examples                    # list YAML files
fenix info memfd-exec             # flags and telemetry for a technique
fenix run -c examples/<file>.yaml
fenix cleanup                     # remove /tmp, /dev/shm, test LKM artifacts after lab work
```

### Run all techniques (coverage matrix)

```bash
fenix run-all --list              # case ids + tiers
fenix run-all                     # core (~19 detonations)
sudo env FENIX_BIN_DIR=$PWD/bin fenix run-all --full
```

That order is supported. If you already ran `examples/memfd_self_reexec.yaml` (unlinks the helper) or `examples/shm_exec.yaml` (leaves `/dev/shm/fenix_shm_payload`), run `make helpers` and `fenix cleanup` before the sudo pass — [docs/LAB_MATRIX.md](../docs/LAB_MATRIX.md).

LKM YAML files still require **sudo** when run individually (`fenix run -c examples/lkm_load_*.yaml`).

After a lab session, run **`fenix cleanup`** (or `fenix cleanup --dry-run`) — see [docs/CLEANUP.md](../docs/CLEANUP.md).
