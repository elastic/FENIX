# FENIX lab cleanup

FENIX leaves intentional artifacts during lab runs. Use **`fenix cleanup`** to tear down after experiments.

## What gets cleaned

| Scope | Actions |
|-------|---------|
| **Session** | Temp files registered via `temp_path()` (auto-removed on process exit) |
| **Persisted** | Paths/shm names/kmod names recorded in `.fenix/artifacts.json` from prior runs |
| **Global glob** | Known orphans: `/tmp/fenix-staged-*`, `fenix-procfd-*`, `fenix-memfd-*`, `fenix_cleanup*`, `/dev/shm/fenix_shm_*` |
| **lkm-load** | `rmmod hello_lkm` (and recorded module names when `--keep-loaded` was used) |
| **deleted-file-exec** | Recorded target paths under `/tmp` |
| **shm-exec / shm-so-load** | `/dev/shm/fenix_shm_*` |
| **interpreter-memfd-exec** | `/tmp/fenix-memfd-*` (materialized script dirs) |

Glob patterns are **narrow** on purpose — they do not match arbitrary unrelated `fenix-*` files.

## Commands

```bash
fenix cleanup --dry-run              # preview
fenix cleanup                        # full lab cleanup
fenix cleanup -t lkm-load            # per-technique
fenix cleanup -t fileless-staging
fenix cleanup --build                # also: make clean
fenix cleanup --list                 # scopes with dedicated handlers
```

## `lkm-load` and module state

Each `lkm-load` run **automatically rmmods `hello_lkm` before and after** a successful load (unless `--keep-loaded`). That keeps repeat lab runs and `fenix run-all` from failing with `init_module: File exists`.

If you used `--keep-loaded` or a run failed mid-way:

```bash
sudo env FENIX_BIN_DIR=$PWD/bin fenix cleanup -t lkm-load
# or
sudo rmmod hello_lkm
```

## After `fenix run-all`

The coverage matrix ends with a reminder to run cleanup. A full `--full` pass touches `/tmp`, `/dev/shm`, optional remote staging temps, and LKM state:

```bash
fenix cleanup
sudo env FENIX_BIN_DIR=$PWD/bin fenix cleanup -t lkm-load   # if any --keep-loaded runs
```

Two leftovers from **hand-run** techniques (not from `run-all` itself) can break a later **root** matrix:

| Leftover | Symptom | Fix |
|----------|---------|-----|
| `/dev/shm/fenix_shm_payload` owned by your user | root `shm-exec`: `shm_open: Permission denied` | `fenix cleanup` (as that user) |
| missing `bin/fenix-memfd-self-reexec` | `memfd-self-reexec` SKIP | `make helpers` |

`run-all` already unlinks the shm object and keeps the helper. See [LAB_MATRIX.md](LAB_MATRIX.md#user-then-sudo).

## Implementation

- `fenix/core/cleanup.py` — API and handlers
- `fenix/core/runner.py` — records artifacts and runs session cleanup after each `fenix run`
- `fenix/techniques/lkm_load.py` — pre/post `rmmod` for repeatable module loads

Child processes started with `--no-wait` are **not** killed — only filesystem and module artifacts.
