"""Opt-in remote upload for fileless-staging (operator names the host)."""

from __future__ import annotations

import base64
import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from fenix.core.staging import DEFAULT_HEADERS

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 35
UPLOAD_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)
PASTEBIN_API = "https://pastebin.com/api/api_post.php"
CATBOX_API = "https://catbox.moe/user/api.php"
TMPFILES_API = "https://tmpfiles.org/api/v1/upload"
UGUU_API = "https://uguu.se/upload"

# Named third-party adapters — used only when the operator names them.
THIRD_PARTY_BACKENDS = frozenset({"uguu", "tmpfiles", "catbox", "pastebin"})
HTTP_BACKENDS = frozenset({"put", "post"})

PLACEHOLDER_URL_MARKERS = (
    "YOUR-LAB-HOST",
    "your-lab-host",
    "YOUR_LAB_HOST",
    "change-me.example",
    "CHANGE-ME",
)

PLACEHOLDER_REFUSAL = """
************************************************************************
FENIX REFUSED TO RUN THIS REMOTE STAGING EXAMPLE

The URL still contains a placeholder (YOUR-LAB-HOST).
This YAML/command is a TEMPLATE. Nothing is uploaded until YOU edit it.

  1. Put a host you control in remote_upload_url / --remote-upload-url
     e.g. https://files.your-lab.example/fenix-hello.bin
  2. Or opt in to a named adapter you choose:
     --remote-backend uguu   (also: tmpfiles, catbox, pastebin)

See docs/STAGING_REMOTE.md
************************************************************************
""".strip()


def _reject_placeholder_url(*urls: str | None) -> None:
    for url in urls:
        if not url:
            continue
        lowered = url.lower()
        for marker in PLACEHOLDER_URL_MARKERS:
            if marker.lower() in lowered:
                print(PLACEHOLDER_REFUSAL, flush=True)
                raise ValueError(
                    "Replace YOUR-LAB-HOST (or equivalent placeholder) before --remote. "
                    "See docs/STAGING_REMOTE.md."
                )


REMOTE_HINT = """--remote does not pick a host. Name one yourself (CLI, YAML, or env).

  Host you control (recommended):
    --remote-backend put --remote-upload-url https://YOUR-LAB-HOST/fenix-hello.bin
    --remote-backend post --remote-upload-url https://YOUR-LAB-HOST/upload

  Named adapter (opt-in; FENIX will not choose one for you):
    --remote-backend uguu | tmpfiles | catbox | pastebin

  Environment:
    FENIX_REMOTE_BACKEND, FENIX_REMOTE_UPLOAD_URL, FENIX_REMOTE_DOWNLOAD_URL
"""


def list_remote_backends() -> list[str]:
    return sorted({*THIRD_PARTY_BACKENDS, *HTTP_BACKENDS})


def _backend(name: str) -> str:
    key = (name or "").lower().strip()
    if key not in THIRD_PARTY_BACKENDS and key not in HTTP_BACKENDS:
        known = ", ".join(list_remote_backends())
        raise ValueError(
            f"Unknown remote backend '{name}'. Choose: {known}\n\n{REMOTE_HINT}"
        )
    return key


def _lab_filename(filename: str) -> str:
    """Hosts like tmpfiles reject extensionless names (e.g. 'hello')."""
    path = Path(filename or "fenix-payload")
    if path.suffix:
        return f"fenix-{secrets.token_hex(4)}{path.suffix}"
    return f"fenix-{secrets.token_hex(4)}.bin"


def _pastebin_api_key() -> str:
    for env in ("FENIX_PASTEBIN_API_KEY", "PASTEBIN_API_KEY"):
        value = os.environ.get(env, "").strip()
        if value:
            return value
    raise ValueError(
        "Pastebin upload requires FENIX_PASTEBIN_API_KEY (get one at https://pastebin.com/doc_api)"
    )


def _parse_upload_url(response: requests.Response, *, service: str) -> str:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip()[:200] if response.text else ""
        msg = f"{service} upload failed ({exc})"
        if detail:
            msg += f": {detail}"
        raise RuntimeError(msg) from exc
    url = response.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"{service} unexpected response: {url[:200]}")
    return url


def _curl_form_upload(
    url: str,
    *,
    form_fields: list[tuple[str, str]],
    file_field: str,
    body: bytes,
    filename: str,
    timeout: int = READ_TIMEOUT,
) -> str:
    """Upload via curl (often more reliable than requests for catbox)."""
    tmp_path = None
    try:
        suffix = Path(filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(body)
            tmp_path = tmp.name

        cmd = ["curl", "-fsSL", "--max-time", str(timeout)]
        for key, value in form_fields:
            cmd.extend(["-F", f"{key}={value}"])
        cmd.extend(["-F", f"{file_field}=@{tmp_path};filename={filename}"])
        cmd.append(url)

        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            err = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"curl upload failed: {err or f'exit {completed.returncode}'}")
        result = completed.stdout.strip()
        if not result.startswith("http"):
            raise RuntimeError(f"curl upload unexpected response: {result[:200]}")
        return result
    except FileNotFoundError as exc:
        raise RuntimeError("curl not found on PATH (install curl or use another --remote-backend)") from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def _upload_pastebin(body: bytes, *, filename: str) -> str:
    api_key = _pastebin_api_key()
    try:
        text = body.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "Pastebin only accepts text; use --decode base64 on download or pick backend uguu/tmpfiles"
        ) from exc

    response = requests.post(
        PASTEBIN_API,
        data={
            "api_dev_key": api_key,
            "api_option": "paste",
            "api_paste_code": text,
            "api_paste_private": "1",
            "api_paste_expire_date": "1D",
            "api_paste_name": f"fenix-lab-{filename}",
        },
        timeout=UPLOAD_TIMEOUT,
        headers=DEFAULT_HEADERS,
    )
    paste_url = _parse_upload_url(response, service="Pastebin")
    paste_id = paste_url.rsplit("/", 1)[-1]
    return f"https://pastebin.com/raw/{paste_id}"


def _upload_catbox_requests(body: bytes, *, filename: str) -> str:
    response = requests.post(
        CATBOX_API,
        data={"reqtype": "fileupload"},
        files={"fileToUpload": (filename, body)},
        timeout=UPLOAD_TIMEOUT,
        headers=DEFAULT_HEADERS,
    )
    return _parse_upload_url(response, service="catbox.moe")


def _upload_catbox(body: bytes, *, filename: str) -> str:
    """Permanent catbox; curl first (fewer 412/WAF issues), requests as fallback."""
    name = _lab_filename(filename)
    try:
        return _curl_form_upload(
            CATBOX_API,
            form_fields=[("reqtype", "fileupload")],
            file_field="fileToUpload",
            body=body,
            filename=name,
        )
    except RuntimeError:
        return _upload_catbox_requests(body, filename=name)


def _upload_uguu(body: bytes, *, filename: str) -> str:
    name = _lab_filename(filename)
    response = requests.post(
        UGUU_API,
        files={"files[]": (name, body)},
        timeout=UPLOAD_TIMEOUT,
        headers=DEFAULT_HEADERS,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"uguu.se upload failed ({exc})") from exc
    data = response.json()
    files = data.get("files") or []
    if not files or not files[0].get("url"):
        raise RuntimeError(f"uguu.se unexpected response: {response.text[:200]}")
    return str(files[0]["url"]).replace("\\/", "/")


def _tmpfiles_direct_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    path = parsed.path.lstrip("/")
    if path.startswith("dl/"):
        return page_url
    return f"{parsed.scheme}://{parsed.netloc}/dl/{path}"


def _upload_tmpfiles(body: bytes, *, filename: str) -> str:
    name = _lab_filename(filename)
    response = requests.post(
        TMPFILES_API,
        files={"file": (name, body)},
        timeout=UPLOAD_TIMEOUT,
        headers=DEFAULT_HEADERS,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip()[:200]
        raise RuntimeError(f"tmpfiles.org upload failed ({exc}): {detail}") from exc
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"tmpfiles.org upload failed: {json.dumps(payload)[:200]}")
    page_url = (payload.get("data") or {}).get("url")
    if not page_url:
        raise RuntimeError(f"tmpfiles.org missing URL: {response.text[:200]}")
    return _tmpfiles_direct_url(str(page_url))


def _upload_put(body: bytes, *, filename: str, upload_url: str) -> str:
    """HTTP PUT bytes to an operator-supplied URL; GET that URL (or response body) back."""
    del filename
    response = requests.put(
        upload_url,
        data=body,
        timeout=UPLOAD_TIMEOUT,
        headers={**DEFAULT_HEADERS, "Content-Type": "application/octet-stream"},
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip()[:200] if response.text else ""
        msg = f"PUT {upload_url} failed ({exc})"
        if detail:
            msg += f": {detail}"
        raise RuntimeError(msg) from exc
    text = response.text.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text.split()[0]
    return upload_url


def _upload_post(body: bytes, *, filename: str, upload_url: str) -> str:
    """HTTP POST multipart file= to an operator-supplied URL; response body must be a download URL."""
    name = _lab_filename(filename)
    response = requests.post(
        upload_url,
        files={"file": (name, body)},
        timeout=UPLOAD_TIMEOUT,
        headers=DEFAULT_HEADERS,
    )
    return _parse_upload_url(response, service=f"POST {upload_url}")


REMOTE_BACKENDS: dict[str, Callable[..., str]] = {
    "uguu": _upload_uguu,
    "tmpfiles": _upload_tmpfiles,
    "catbox": _upload_catbox,
    "pastebin": _upload_pastebin,
}


def upload_bytes(
    body: bytes,
    *,
    backend: str,
    filename: str = "fenix-payload",
    upload_url: str | None = None,
) -> str:
    """Upload bytes; return a direct HTTP(S) download URL."""
    key = _backend(backend)
    print(f"[fenix] remote upload: sending via '{key}'…", flush=True)
    if key in HTTP_BACKENDS:
        if not upload_url:
            raise ValueError(
                f"--remote-backend {key} requires --remote-upload-url "
                "(or FENIX_REMOTE_UPLOAD_URL)."
            )
        if key == "put":
            return _upload_put(body, filename=filename, upload_url=upload_url)
        return _upload_post(body, filename=filename, upload_url=upload_url)
    fn = REMOTE_BACKENDS[key]
    return fn(body, filename=filename)


def _prepare_upload_body(
    raw: bytes,
    *,
    backend: str,
    decode: str | None,
    remote_encode: str | None,
) -> tuple[bytes, str | None]:
    """
    Return (upload_body, decode_after_download).
    decode_after_download is set when we base64-encode for text-only hosts.
    """
    encode = (remote_encode or "auto").lower()
    if encode == "none":
        return raw, decode
    if encode == "base64":
        return base64.b64encode(raw), decode or "base64"

    if decode in ("base64", "xor"):
        return raw, decode

    text_backend = backend == "pastebin"
    try:
        raw.decode("utf-8")
        return raw, decode
    except UnicodeDecodeError:
        if text_backend:
            return base64.b64encode(raw), decode or "base64"
        return raw, decode


def _opt(options: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = options.get(key)
        if value is not None and value is not False and value != "":
            return value
    return None


def _resolve_remote_backend(options: dict[str, Any], remote_flag: Any) -> tuple[str, str | None]:
    """
    Return (backend, upload_url). Backend is required; upload_url only for put/post.
    """
    upload_url = (
        _opt(options, "remote_upload_url", "remote-upload-url")
        or os.environ.get("FENIX_REMOTE_UPLOAD_URL", "").strip()
        or None
    )
    backend = _opt(options, "remote_backend", "remote-backend")
    if isinstance(remote_flag, str) and remote_flag.lower() not in ("true", "1", "yes"):
        backend = backend or remote_flag
    if not backend:
        backend = os.environ.get("FENIX_REMOTE_BACKEND", "").strip() or None
    if not backend and upload_url:
        backend = "put"
    if not backend:
        raise ValueError(REMOTE_HINT)
    return _backend(str(backend)), upload_url


def _announce_remote_plan(
    *,
    path: Path,
    backend: str,
    upload_url: str | None,
    fetch: str,
    execute: str,
    method: str,
) -> None:
    dest = upload_url if backend in HTTP_BACKENDS else f"named adapter '{backend}'"
    print("[fenix] remote staging — opt-in upload, then download, then execute", flush=True)
    print(f"[fenix]   local file : {path}", flush=True)
    print(f"[fenix]   upload     : {backend} → {dest}", flush=True)
    print(f"[fenix]   download   : GET via {fetch} (URL printed after upload)", flush=True)
    print(f"[fenix]   execute    : {execute}" + (f" / {method}" if execute == "memfd" else ""), flush=True)
    if backend in THIRD_PARTY_BACKENDS:
        print(
            "[fenix]   note       : third-party host — used only because you named it; "
            "prefer --remote-backend put and a server you control",
            flush=True,
        )


def apply_remote_upload(options: dict[str, Any]) -> dict[str, Any]:
    """
    --remote: read source_file, upload to an operator-named host, set source_url.
    Mutually exclusive with source_url and lab_remote. No default public host.
    """
    remote = options.get("remote")
    if remote is None or remote is False:
        return options

    if options.get("source_url") or options.get("source-url"):
        raise ValueError("Use either --remote (upload) or --source-url, not both.")
    if options.get("lab_remote") or options.get("lab-remote"):
        raise ValueError("Use either --remote (upload) or --lab-remote (preset URL), not both.")

    source_file = options.get("source_file") or options.get("source-file")
    if not source_file:
        raise ValueError("--remote requires --source-file (local payload to upload).")

    path = Path(source_file).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Remote upload source not found: {path}")

    backend, upload_url = _resolve_remote_backend(options, remote)
    download_override = (
        _opt(options, "remote_download_url", "remote-download-url")
        or os.environ.get("FENIX_REMOTE_DOWNLOAD_URL", "").strip()
        or None
    )
    fetch = (
        _opt(options, "remote_fetch", "remote-fetch")
        or os.environ.get("FENIX_REMOTE_FETCH", "").strip()
        or "requests"
    )
    execute = str(options.get("execute") or "memfd")
    method = str(options.get("method") or "procfs-fd")

    _reject_placeholder_url(upload_url, download_override)

    _announce_remote_plan(
        path=path,
        backend=backend,
        upload_url=upload_url,
        fetch=fetch,
        execute=execute,
        method=method,
    )

    raw = path.read_bytes()
    decode = options.get("decode")
    remote_encode = options.get("remote_encode") or options.get("remote-encode")
    upload_body, decode_after = _prepare_upload_body(
        raw,
        backend=backend,
        decode=decode,
        remote_encode=remote_encode,
    )

    if backend == "pastebin":
        try:
            upload_body.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Pastebin needs text; use --remote-backend put with a binary host, "
                "or --remote-encode base64"
            ) from exc

    url = upload_bytes(
        upload_body,
        backend=backend,
        filename=path.name,
        upload_url=upload_url,
    )
    if download_override:
        url = download_override

    merged = dict(options)
    merged["source_url"] = url
    merged.pop("source_file", None)
    merged.pop("source-file", None)
    merged["remote_uploaded_url"] = url
    merged["remote_backend"] = backend

    if decode_after and merged.get("decode") is None:
        merged["decode"] = decode_after
    merged["remote_fetch"] = fetch

    print(f"[fenix]   download URL: {url}", flush=True)
    if decode_after and decode_after != "none":
        print(f"[fenix]   decode after download: {decode_after}", flush=True)

    merged.pop("remote", None)
    merged.pop("remote_encode", None)
    merged.pop("remote-encode", None)
    merged.pop("remote_upload_url", None)
    merged.pop("remote-upload-url", None)
    merged.pop("remote_download_url", None)
    merged.pop("remote-download-url", None)
    return merged
