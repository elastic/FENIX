# Changelog

All notable changes to FENIX are documented here.

## [1.0.0] — 2026-08-20

Public release. Not published to PyPI.

### Removed

- **`interpreter-memfd-exec` Lua and Node loaders** — unreliable without extra packages; supported interpreters are perl, python3, php, and ruby
- **Remote backends** `auto`, `0x0`, `transfer.sh`, and `litterbox`
- Duplicate example YAML (`memfd_exec_explain.yaml`, alias `interpreter_memfd_perl.yaml` / `interpreter_memfd_python3.yaml`)

### Changed

- **License** — Apache License 2.0 (Elasticsearch B.V.); `hello_lkm.c` remains GPL-2.0-only
- **Python** — require 3.10+
- **Default lab-remote base** — `https://raw.githubusercontent.com/elastic/fenix/main` (override with `FENIX_LAB_STAGING_BASE`)
- **`fenix run-all`** — shm-exec unlinks the `/dev/shm` object; memfd-self-reexec keeps the helper, so user `run-all` then `sudo --full` does not FAIL/SKIP those cases

### Added

- `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Runtime refusal when `fileless-staging` still uses the `YOUR-LAB-HOST` placeholder
- `finit_module` and optional ruby interpreter-memfd cases in `fenix run-all`
- **`fileless-staging --remote`** — opt-in only; you name `put`/`post` plus `--remote-upload-url`, or a third-party adapter. FENIX never selects a public bin. `run-all --full` does not upload.

## [0.2.0] — 2026-05-20

### Added

- **`fenix run-all`** — lab coverage matrix with tiers (`core`, `extended`, `lolbin`, `remote`, `lkm`) and PASS/FAIL/SKIP summary ([docs/LAB_MATRIX.md](docs/LAB_MATRIX.md))
- **`lkm-load` methods** — `memfd-init-module`, `memfd-init-module-fork`, `memfd-finit-module`, `embedded-init-module` (helpers + examples)
- **`fenix-embedded-init-module`** helper (embedded `hello_lkm.ko` via `xxd`)
- **Remote staging** — `fileless-staging --remote` with multi-backend upload and fetch options ([docs/STAGING_REMOTE.md](docs/STAGING_REMOTE.md))
- **`interpreter-memfd-exec`** — one-liner and script-file memfd loader modes ([docs/INTERPRETER_MEMFD.md](docs/INTERPRETER_MEMFD.md))
- **Documentation index** — [docs/README.md](docs/README.md)

### Changed

- **`lkm-load`** — auto-`rmmod hello_lkm` before/after runs by default; `--keep-loaded` to opt out
- **README** — technique/helper/example counts, sudo/venv guidance, doc map
- **Examples** — LKM and interpreter-memfd YAML configs indexed in `examples/README.md`

### Documentation

- Consolidated and cross-linked all guides for production/lab handoff
- PR template and CONTRIBUTING updated for `run-all` and catalog sync

## [0.1.0] — initial lab framework

- Core memfd, shm, pipe, proc-fd, staging, interpreter, and LKM techniques
- C helpers, YAML examples, `fenix cleanup`, explain walkthrough
