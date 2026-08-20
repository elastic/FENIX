# Interpreter memfd loaders (`interpreter-memfd-exec`)

Two **detection surfaces** for the same in-process memfd + stdin ELF + `/proc/self/fd` exec chain:

| Mode | Example argv shape | FENIX |
|------|-------------------|--------|
| **one-liner** | `python3 -c '<memfd loader>'` | `--mode one-liner` (default) |
| **script-file** | `python3 /tmp/fenix-memfd-…/memfd_payload.py` | `--mode script-file` |

Templates live in `payloads/memfd_oneliners/memfd_payload.{pl,py,php,rb}`.

Supported interpreters: **perl**, **python3**, **php**, **ruby** (stdlib + distro packages only).

## Perl

```bash
export FENIX_BIN_DIR=$PWD/bin

# perl -e '…'
fenix run interpreter-memfd-exec --interpreter perl --mode one-liner
cat payloads/hello_elf/hello | fenix run interpreter-memfd-exec --interpreter perl --mode one-liner

# perl memfd_payload.pl
fenix run interpreter-memfd-exec --interpreter perl --mode script-file
```

## Python3

```bash
fenix run interpreter-memfd-exec --interpreter python3 --mode one-liner
fenix run interpreter-memfd-exec --interpreter python3 --mode script-file
```

## PHP

```bash
sudo apt install -y php-cli php-ffi   # FFI (memfd write) + pcntl (exec)
# PHP uses FFI write+fchmod on the memfd fd (file_put_contents on /proc/self/fd fails).
# one-liner: `php -r` gets the script body without `<?php` (CLI -r cannot parse tags).

fenix run interpreter-memfd-exec --interpreter php --mode one-liner
fenix run interpreter-memfd-exec --interpreter php --mode script-file
```

## Ruby

```bash
cat payloads/hello_elf/hello | fenix run interpreter-memfd-exec --interpreter ruby --mode one-liner
fenix run interpreter-memfd-exec --interpreter ruby --mode script-file
```

## YAML

```bash
fenix run -c examples/interpreter_memfd_perl_oneliner.yaml
fenix run -c examples/interpreter_memfd_perl_script.yaml
fenix run -c examples/interpreter_memfd_python3_oneliner.yaml
fenix run -c examples/interpreter_memfd_python3_script.yaml
fenix run -c examples/interpreter_memfd_php_oneliner.yaml
fenix run -c examples/interpreter_memfd_php_script.yaml
fenix run -c examples/interpreter_memfd_ruby.yaml
```

## Options

| Flag | Purpose |
|------|---------|
| `--mode one-liner` | `interpreter -e/-c/-r` with expanded loader in argv |
| `--mode script-file` | `interpreter /tmp/fenix-memfd-*/memfd_payload.<ext>` |
| `--script PATH` | Override template (default: repo `memfd_payload.*`) |
| `--argv0 NAME` | Masquerade exec argv[0] (default `fenix_payload`) |
| `--payload PATH` | ELF bytes on stdin (default `hello_elf`) |

## Shell equivalents (manual lab)

```bash
# One-liner (amd64 syscall 319)
CODE=$(sed 's/__FENIX_MEMFD_SYSCALL__/319/;s/__FENIX_ARGV0__/fenix_payload/' payloads/memfd_oneliners/memfd_payload.pl)
cat payloads/hello_elf/hello | perl -e "$CODE"

# Script file
DIR=$(mktemp -d fenix-memfd-XXXX)
sed 's/__FENIX_MEMFD_SYSCALL__/319/;s/__FENIX_ARGV0__/fenix_payload/' \
  payloads/memfd_oneliners/memfd_payload.py > "$DIR/memfd_payload.py"
cat payloads/hello_elf/hello | python3 "$DIR/memfd_payload.py"
```

## Coverage testing

`fenix run-all` includes perl/python/php one-liner cases (core) plus perl script-file and ruby one-liner (extended). The ruby case is optional and SKIPs when `Fcntl.fchmod` is missing (some distro Rubies). See [LAB_MATRIX.md](LAB_MATRIX.md).

## Cleanup

```bash
fenix cleanup   # removes /tmp/fenix-memfd-* dirs
```
