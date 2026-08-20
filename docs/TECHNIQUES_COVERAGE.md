# FENIX coverage vs public fileless-execution sources

Lab mapping for detection-engineering research. Out-of-scope items (persistence, ptrace injection, eBPF hiding, C2) are listed but not implemented.

## Coverage matrix

| Technique pattern | Example sources | FENIX module | Status |
|-------------------|-----------------|--------------|--------|
| memfd + `/proc/self/fd` exec ELF | [sympy-dev](https://socket.dev/blog/pypi-package-impersonates-sympy-to-deliver-cryptomining-malware), [magisterquis](https://magisterquis.github.io/2018/03/31/in-memory-only-elf-execution.html), [mohitdabas](https://mohitdabas.in/blog/linux-maldev-fileless-execution-memfd-create/), [fireELF](https://github.com/rek7/fireELF), [fee](https://github.com/nnsee/fileless-elf-exec), [pupy](https://github.com/n1nj4sec/pupy) | `memfd-exec` | Covered |
| memfd + `fexecve` | fireELF, magisterquis | `memfd-exec --method fexecve` | Covered |
| memfd + `execveat` | [QLNX](https://www.trendmicro.com/en_us/research/26/e/quasar-linux-qlnx-a-silent-foothold-in-the-software-supply-chain.html) | `memfd-exec --method execveat` | Covered |
| memfd + `fchmod` + exec | sympy-dev | `memfd-exec --fchmod` | Covered |
| HTTP(S) stage → memfd exec | sympy-dev, fireELF, [RemoteELFMemExec](https://github.com/Rubikcuv5/RemoteELFMemExec) | `fileless-staging` | Covered |
| XOR-encrypted remote ELF | RemoteELFMemExec | `fileless-staging --decode xor --xor-key` | Covered |
| curl \| tar \| perl memfd | [PerlyShells](https://blog.jrdioca.com/offensive%20security/offensive%20security%20-%20evasion/red%20teaming/apt%20emulation/2026/01/04/PerlyShells/) | `fileless-staging --decompress tar --tar-member` | Covered |
| Perl/Python memfd one-liner | fee, PerlyShells | `interpreter-memfd-exec`, `memfd-script-exec` | Covered |
| argv0 / process masquerade | PerlyShells, RemoteELFMemExec | `memfd-exec --argv0` | Covered |
| Self-copy `/proc/self/exe` → memfd → unlink → re-exec | QLNX | `memfd-self-reexec` | Covered |
| Reflective `.so` via memfd `dlopen` | QLNX | `memfd-so-load` | Covered |
| Pipe + `fexecve` ELF | — | `pipe-exec` | Covered |
| Open fd + `/proc/self/fd` (non-memfd) | magisterquis | `proc-fd-exec` | Covered |
| Deleted backing file + exec | RemoteELFMemExec legacy | `deleted-file-exec` | Covered |
| Interpreter one-liners (expanded) | fee, PerlyShells | `interpreter-exec` | Covered |
| Interpreter memfd stdin ELF (`perl -e` / python/ruby) | PerlyShells, supply-chain loaders | `interpreter-memfd-exec` | Covered |
| In-memory kernel module (heap / memfd / embedded) | Public in-memory LKM loader PoCs | `lkm-load` | Covered — see `docs/FILELESS_LKM.md` |
| LD_PRELOAD persistence | QLNX | — | Out of scope |
| ptrace / `/proc/pid/mem` inject | QLNX, pupy | — | Out of scope |
| eBPF concealment | QLNX | — | Out of scope |
| BOF/COFF in-memory | QLNX | — | Out of scope |
| `/proc/self/comm` rename only | QLNX, PerlyShells | — | Out of scope (evasion) |
| hackshell bash hygiene | [hackshell](https://github.com/hackerschoice/hackshell) | — | Not execution (shell tradecraft) |
| tmpfs/shm-only `.so` load | QLNX, SilentLoader | `shm-so-load` | Covered |
| `shm_open` ELF exec (non-memfd) | SilentLoader | `shm-exec` | Covered |
| `sendfile` → memfd → exec | Cexigua | `memfd-exec --ingest sendfile` | Covered |
| stdin / pipe → memfd → execveat | memexec, THC | `stdin-memexec` | Covered |
| `MFD_NOEXEC_SEAL` + fchmod lab | kernel 6.3+ | `memfd-exec --noexec-seal --fchmod` | Covered (see `docs/MEMFD_NOEXEC_LAB.md`) |
| LoLbin + `/proc/self/fd/N` | detection engineering | `lolbin-fd-exec` (ld-linux, busybox, julia, erlang) | Covered |
| LKM memfd → `load_module` | Public in-memory LKM loader PoCs | `lkm-load` (`memfd-finit-module`, `memfd-init-module`, …) | Covered — `docs/FILELESS_LKM.md` |
| Full-framework detonation | detection validation | `fenix run-all` | Covered — `docs/LAB_MATRIX.md` |

## Validating coverage

On a Linux lab VM after `make all && pip install -e .`:

```bash
export FENIX_BIN_DIR=$PWD/bin
fenix run-all --list
fenix run-all
sudo env FENIX_BIN_DIR=$PWD/bin fenix run-all --full
fenix cleanup
```

User then sudo is supported ([LAB_MATRIX.md](LAB_MATRIX.md#user-then-sudo)). If you already ran `memfd-self-reexec` or `shm-exec` by hand, `make helpers` and `fenix cleanup` first.

Map alerts to case ids in the `run-all` summary table and to example YAML in `examples/README.md`.

## References

- Socket: sympy-dev PyPI memfd loader
- Trend Micro: Quasar Linux (QLNX)
- Stuart: In-Memory-Only ELF Execution
- fireELF, fee, RemoteELFMemExec, pupy, PerlyShells, mohitdabas
