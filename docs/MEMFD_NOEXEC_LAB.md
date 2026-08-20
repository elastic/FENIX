# memfd_noexec hardening lab matrix

Linux kernels from 6.3 onward support non-executable anonymous memfds (`MFD_NOEXEC_SEAL`) and the `vm.memfd_noexec` sysctl. FENIX includes labeled PoCs so detection engineers can validate rules against both **legacy** and **hardened** hosts.

## Sysctl values (`vm.memfd_noexec`)

| Value | Behavior |
|-------|----------|
| `0` | Default: memfds are executable unless sealed otherwise (legacy) |
| `1` | New memfds default to non-executable |
| `2` | Enforce non-executable memfds (reject executable mappings) |

Check current setting:

```bash
sysctl vm.memfd_noexec
```

## FENIX techniques to exercise

### Baseline (always works on lab VMs)

```bash
fenix run memfd-exec --payload payloads/hello_elf/hello --method procfs-fd
```

### sendfile ingest (distinct syscall chain)

```bash
fenix run memfd-exec --payload payloads/hello_elf/hello --ingest sendfile
fenix run -c examples/memfd_exec_sendfile.yaml
```

### MFD_NOEXEC_SEAL + fchmod bypass attempt

Creates the memfd with `MFD_NOEXEC_SEAL`, then applies `fchmod(0755)` before `execveat` — mirrors defender research on seal bypass attempts.

```bash
fenix run memfd-exec --payload payloads/hello_elf/hello \
  --noexec-seal --fchmod --method execveat
fenix run -c examples/memfd_exec_noexec_seal.yaml
```

On kernels without `MFD_NOEXEC_SEAL`, the helper exits with a clear error; use baseline `memfd-exec` instead.

On hardened hosts (Ubuntu 24.04+, `vm.memfd_noexec` ≥ 1), **`fchmod: Operation not permitted` is the expected outcome** — the seal blocks the bypass. That is a successful lab result, not a misconfiguration. **Do not use `sudo`** for this case; root does not lift `MFD_NOEXEC_SEAL`.

With `vm.memfd_noexec = 0`, `--noexec-seal` still applies `MFD_NOEXEC_SEAL` on the memfd, so `fchmod` can still fail. After a failed run, the CLI prints sysctl commands to enable system-wide policy (`vm.memfd_noexec=1`, with a hardening warning) or to relax it (`=0`, with a security warning) when already hardened.

`sudo fenix` fails if `fenix` is only installed in a venv (sudo does not activate it). Use the venv binary explicitly:

```bash
sudo env FENIX_BIN_DIR=$PWD/bin $PWD/.venv/bin/fenix run lkm-load ...
```

`memfd-exec` does not require root except when your lab policy demands it for unrelated reasons.

### tmpfs / shm path (no memfd_create)

```bash
fenix run shm-exec --payload payloads/hello_elf/hello --method fexecve
fenix run -c examples/shm_exec.yaml
```

### stdin → memfd (memexec-style)

```bash
cat payloads/hello_elf/hello | fenix run stdin-memexec --method execveat --fchmod
fenix run -c examples/stdin_memexec.yaml
```

## Suggested test matrix

Bulk run (excludes `noexec-seal` by default): `fenix run-all` — see [LAB_MATRIX.md](LAB_MATRIX.md).

| Host profile | Commands to run |
|--------------|-----------------|
| Ubuntu 22.04 (legacy memfd exec) | `memfd_exec.yaml`, `shm_exec.yaml`, `stdin_memexec.yaml` |
| Ubuntu 24.04+ (`vm.memfd_noexec=1`) | `memfd_exec_noexec_seal.yaml`, baseline memfd-exec |
| Hardened (`vm.memfd_noexec=2`) | Expect `--noexec-seal --fchmod` to fail; confirm detection fires |

## Detection hints

- `memfd_create` + `sendfile` + `execveat` (sendfile ingest example)
- `shm_open` + `execve` on `/dev/shm/*` (no memfd syscall)
- Process `exe` showing `memfd:` or deleted paths after `stdin-memexec`
- Audit rules on `memfd_create` flags including `MFD_NOEXEC_SEAL`

## References

- [Kernel: non-executable mfd](https://www.kernel.org/doc/html/latest/userspace-api/mfd_noexec.html)
- [Gavin Ray — noexec bypass with memfd_create](https://gavinray97.github.io/blog/memfd-create-noexec)
- [THC — bypassing noexec](https://iq.thc.org/bypassing-noexec-and-executing-arbitrary-binaries)
