# Lab coverage matrix (`fenix run-all`)

Run the full FENIX framework in one pass to validate detection rules, endpoint telemetry, or SIEM correlation — without manually invoking each technique.

## Quick start

```bash
cd ~/FENIX
make all && pip install -e .
export FENIX_BIN_DIR=$PWD/bin

# Core matrix (19 cases, no root)
fenix run-all

# Preview planned runs
fenix run-all --list
fenix run-all --dry-run

# Full coverage (37 cases: extended + lolbin + all LKM methods; no internet upload)
sudo env FENIX_BIN_DIR=$PWD/bin $PWD/.venv/bin/fenix run-all --full

# Cleanup in-process (avoids "fenix: not found" after sudo)
$PWD/.venv/bin/fenix run-all --cleanup
```

**`sudo fenix` fails** — sudo does not use your venv `PATH`. Always pass the full binary:

```bash
F="$PWD/.venv/bin/fenix"
export FENIX_BIN_DIR=$PWD/bin
$F run-all
sudo env FENIX_BIN_DIR=$PWD/bin $F run-all --full
$F cleanup
```

Or use the wrapper script:

```bash
bash scripts/run_lab_matrix.sh
```

## User then sudo

The sequence above is the intended lab flow. The matrix is built so a non-root `run-all` does not poison the following `sudo --full`:

- **shm-exec** uses `--unlink` so `/dev/shm/fenix_shm_payload` is not left owned by your user. A leftover object in sticky `/dev/shm` makes root `shm_open` fail with `Permission denied` (`fs.protected_regular`).
- **memfd-self-reexec** uses `--no-unlink` so `bin/fenix-memfd-self-reexec` stays on disk. The standalone command and `examples/memfd_self_reexec.yaml` still unlink (that *is* the technique) — restore with `make helpers`.

If you already detonated those by hand:

```bash
make helpers
fenix cleanup
sudo env FENIX_BIN_DIR=$PWD/bin $F run-all --full
```

Optional SKIPs (not failures): **pipe-exec ELF** (`EPERM` on some kernels), missing LoLbins (julia/erlang), **ruby** interpreter-memfd when `Fcntl.fchmod` is absent.

## Tiers

| Tier | How to enable | Contents |
|------|---------------|----------|
| `core` | default | One representative run per technique / primary syscall surface |
| `extended` | `--full` | Extra methods: execveat, sendfile, xor staging, pipe ELF, proc-fd unlink, awk memfd-script, perl script-file, … |
| `lolbin` | `--with-lolbin` or `--full` | busybox / julia / erlang when installed (`fenix list lolbins`) |
| `remote` | `--with-remote` | `fileless-staging --remote` only if you set `FENIX_REMOTE_BACKEND` or `FENIX_REMOTE_UPLOAD_URL` |
| `lkm` | `--with-lkm` or `--full` | All six `lkm-load` methods (root + `hello_lkm.ko` + embedded helper) |

## Options

| Flag | Effect |
|------|--------|
| `-t, --technique <id>` | Run only cases for one technique |
| `--fail-fast` | Stop on first hard failure |
| `--list` / `-l` | Print case table and exit |
| `--dry-run` / `-n` | Same as `--list` (no detonation) |

```bash
fenix run-all -t memfd-exec
fenix run-all --with-lkm --with-remote
```

## Outcomes

Each case reports **PASS**, **FAIL**, **SKIP**, or **ERROR** in a summary table.

| Result | Meaning |
|--------|---------|
| PASS | Exit code 0 |
| FAIL | Non-zero exit (required case) |
| SKIP | Optional case failed, missing dependency, not root, dry-run, or precondition (e.g. no busybox) |
| ERROR | Exception (e.g. validation error) |

Optional cases include **pipe-exec ELF** (often `EPERM`), missing LoLbins, **ruby** interpreter-memfd when `Fcntl.fchmod` is missing, and **fileless-staging --remote** when no backend is configured.

## Case index (core)

| Case id | Technique | Detection focus |
|---------|-----------|-----------------|
| `memfd-exec-procfs-fd` | memfd-exec | memfd → exec via `/proc/self/fd/N` |
| `memfd-exec-fexecve` | memfd-exec | memfd → `fexecve` |
| `memfd-script-shebang` | memfd-script-exec | shebang on memfd |
| `memfd-script-python-procfs` | memfd-script-exec | interpreter + fd path |
| `memfd-self-reexec` | memfd-self-reexec | `/proc/self/exe` → memfd → re-exec |
| `memfd-so-load` | memfd-so-load | memfd → `dlopen` |
| `shm-exec-procfs-fd` | shm-exec | `/dev/shm` ELF via procfs-fd |
| `stdin-memexec` | stdin-memexec | stdin → memfd → exec |
| `fileless-staging-local-memfd` | fileless-staging | local → memfd |
| `fileless-staging-interpreter-stdin` | fileless-staging | script → interpreter stdin |
| `pipe-exec-script` | pipe-exec | pipe → interpreter |
| `proc-fd-exec-procfs` | proc-fd-exec | non-memfd fd exec |
| `deleted-file-exec` | deleted-file-exec | unlink after exec |
| `interpreter-exec-python` | interpreter-exec | `python3 -c` |
| `interpreter-memfd-*` | interpreter-memfd-exec | perl/python/php one-liners |
| `lolbin-ld-linux` | lolbin-fd-exec | dynamic linker + fd |

Extended and LKM cases are listed in `fenix run-all --list --full`.

## Walkthrough

`run-all` sets `no_explain: true` on every case to reduce noise. For learning, run individual techniques:

```bash
fenix run memfd-exec --payload payloads/hello_elf/hello --method procfs-fd
```

## Detection research

Each case id targets a distinct telemetry chain (memfd+fd, interpreter memfd, staging download, LKM memfd sequence, and so on). Map those ids to your own detection content; this repository does not ship SIEM rules.

## Implementation

- `fenix/core/lab_matrix.py` — case definitions and tiers
- `fenix/core/lab_runner.py` — execution and summary report
- `fenix/cli.py` — `run-all` command

When adding a technique, add at least one **core** `LabCase` so `run-all` stays representative of the framework.
