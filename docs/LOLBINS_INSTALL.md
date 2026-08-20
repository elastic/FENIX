# Installing optional LoLbins for `lolbin-fd-exec`

`ld-linux` and `busybox` are usually available on Ubuntu lab VMs without extra repos. **Julia** and **Erlang** use distro-specific package names.

Check status:

```bash
fenix list lolbins
```

Optional LoLbins are exercised by `fenix run-all --with-lolbin` or `--full` when binaries are on `PATH` ([LAB_MATRIX.md](LAB_MATRIX.md)).

## Ubuntu / Debian

### busybox

```bash
sudo apt update
sudo apt install -y busybox
```

### Erlang (`escript`) — FENIX `--lolbin erlang`

There is **no** apt package named `escript`. Install **Erlang**:

```bash
sudo apt install -y erlang
which escript    # → /usr/bin/escript
fenix run lolbin-fd-exec --lolbin erlang
```

### Julia

Many Ubuntu releases **do not** ship `julia` in default apt.

**Option A — snap (common on Ubuntu VMs):**

```bash
sudo snap install julia --classic
```

**Option B — official binaries:**

https://julialang.org/downloads/

**Option C — enable universe and retry apt** (only if your release lists the package):

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update
sudo apt install -y julia
```

## What you can run without Julia/Erlang

These work on a minimal glibc system:

```bash
fenix run lolbin-fd-exec --lolbin ld-linux --payload payloads/hello_elf/hello
fenix run lolbin-fd-exec --lolbin busybox --payload payloads/scripts/hello_shebang.sh
```

## Verify after install

```bash
fenix list lolbins
fenix run -c examples/lolbin_erlang.yaml
fenix run -c examples/lolbin_julia.yaml
```
