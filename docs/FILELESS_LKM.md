# Fileless kernel module loading (lab)

FENIX `lkm-load` reproduces common **in-memory LKM loader** patterns for detection engineering. The benign `hello_lkm` module only writes to the kernel log on load/unload.

## Method map

| Pattern | FENIX `--method` | Helper |
|---------|------------------|--------|
| Heap read + `init_module` | `init_module` | `fenix-init-module` |
| memfd → mmap → `init_module` | `memfd-init-module` | `fenix-init-module` |
| memfd → fork → child `init_module` | `memfd-init-module-fork` | `fenix-init-module` |
| open `.ko` → `finit_module` | `finit_module` | `fenix-finit-module` |
| memfd fd → `finit_module` | `memfd-finit-module` | `fenix-finit-module` |
| Embedded `.ko` in binary | `embedded-init-module` | `fenix-embedded-init-module` |

FENIX integrates the same syscall surfaces under one CLI.

## Requirements

- **root** (effective UID 0)
- `--i-understand-this-loads-kernel-code`
- Built `payloads/hello_lkm/hello_lkm.ko` (`make payloads`)
- For `embedded-init-module`: `make all` (generates `hello_lkm_embed.h` and `bin/fenix-embedded-init-module`)

## Build

```bash
make payloads    # hello_lkm.ko + hello_lkm_embed.h
make helpers     # fenix-init-module, fenix-finit-module, fenix-embedded-init-module
export FENIX_BIN_DIR=$PWD/bin
```

## Run

Use the venv binary under `sudo`:

```bash
export FENIX_BIN_DIR=$PWD/bin
F="$PWD/.venv/bin/fenix"
M="payloads/hello_lkm/hello_lkm.ko"
U="--i-understand-this-loads-kernel-code"

sudo env FENIX_BIN_DIR=$PWD/bin $F run lkm-load --module $M --method memfd-init-module $U
sudo env FENIX_BIN_DIR=$PWD/bin $F run lkm-load --method embedded-init-module $U

sudo dmesg | tail -5
```

### Repeatable runs

By default FENIX **rmmods `hello_lkm` before and after** each load so you do not get `init_module: File exists` on reruns.

```bash
# Leave module loaded for manual inspection
sudo env FENIX_BIN_DIR=$PWD/bin $F run lkm-load --module $M --method finit_module $U --keep-loaded
sudo env FENIX_BIN_DIR=$PWD/bin $F cleanup -t lkm-load
```

### All methods (coverage / alerts)

```bash
sudo env FENIX_BIN_DIR=$PWD/bin fenix run-all --with-lkm
# or
sudo env FENIX_BIN_DIR=$PWD/bin fenix run-all --full
```

## YAML examples

| File | Method |
|------|--------|
| `examples/lkm_load_init.yaml` | `init_module` |
| `examples/lkm_load_memfd_init.yaml` | `memfd-init-module` |
| `examples/lkm_load_memfd_init_fork.yaml` | `memfd-init-module-fork` |
| `examples/lkm_load_finit.yaml` | `finit_module` |
| `examples/lkm_load_memfd_finit.yaml` | `memfd-finit-module` |
| `examples/lkm_load_embedded.yaml` | `embedded-init-module` |

```bash
fenix run -c examples/lkm_load_memfd_finit.yaml   # still needs sudo for the helper
```

## Telemetry notes

- **memfd + load_module** sequences: parent/child process correlation may differ for `memfd-init-module-fork` (memfd in parent, `init_module` in child).
- **embedded-init-module**: no runtime `.ko` file read; `init_module` from a static buffer in the helper.
- **heap `init_module`**: full module image in userspace memory without memfd.

Validate rules in your stack with `fenix info lkm-load` and the walkthrough on a single run (omit `--no-explain`).
