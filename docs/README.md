# FENIX documentation

Lab guides for building, running, and validating fileless-execution PoCs on Linux.

## Getting started

| Doc | Purpose |
|-----|---------|
| [../README.md](../README.md) | Install, CLI, techniques overview |
| [../examples/README.md](../examples/README.md) | YAML example index (45 configs) |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Snapshot — issues and PRs are not accepted |
| [../SECURITY.md](../SECURITY.md) | Vulnerability reporting |

## Running experiments

| Doc | Purpose |
|-----|---------|
| [LAB_MATRIX.md](LAB_MATRIX.md) | **`fenix run-all`** — full-framework coverage / alert testing |
| [CLEANUP.md](CLEANUP.md) | `fenix cleanup`, artifacts, per-technique teardown |
| [MEMFD_NOEXEC_LAB.md](MEMFD_NOEXEC_LAB.md) | `vm.memfd_noexec` / `MFD_NOEXEC_SEAL` hardening matrix |

## Techniques (deep dives)

| Doc | Technique(s) |
|-----|----------------|
| [STAGING_REMOTE.md](STAGING_REMOTE.md) | `fileless-staging` — `--remote`, `--lab-remote`, fetch backends |
| [INTERPRETER_MEMFD.md](INTERPRETER_MEMFD.md) | `interpreter-memfd-exec` — one-liner vs script-file |
| [FILELESS_LKM.md](FILELESS_LKM.md) | `lkm-load` — heap / memfd / embedded kernel module loaders |
| [LOLBINS_INSTALL.md](LOLBINS_INSTALL.md) | `lolbin-fd-exec` — ld-linux, busybox, julia, erlang |

## Research mapping

| Doc | Purpose |
|-----|---------|
| [TECHNIQUES_COVERAGE.md](TECHNIQUES_COVERAGE.md) | Public PoCs ↔ FENIX modules (fee, fireELF, QLNX, PerlyShells, …) |

## Suggested lab workflow

```bash
make all && pip install -e . && export FENIX_BIN_DIR=$PWD/bin
fenix check
fenix run-all --list              # preview coverage matrix
fenix run-all                     # core detonations
sudo env FENIX_BIN_DIR=$PWD/bin fenix run-all --full   # + LKM + extended + lolbin
fenix cleanup
```

User `run-all` then `sudo --full` is supported (see [LAB_MATRIX.md](LAB_MATRIX.md#user-then-sudo)). If you already ran `memfd-self-reexec` or `shm-exec` by hand, `make helpers` and `fenix cleanup` first.

Use **`fenix info <technique>`** for per-technique flags and **`fenix run -c examples/<file>.yaml`** for a single distinct telemetry surface.
