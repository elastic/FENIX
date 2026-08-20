"""Payload transformation helpers (decode / decompress)."""

from __future__ import annotations

import base64
import gzip
import io
import tarfile
from typing import Literal, Optional

DecodeOption = Literal["none", "base64", "xor"]
DecompressOption = Literal["none", "gzip", "tar"]


def _xor_decode(data: bytes, key: str) -> bytes:
    if not key:
        raise ValueError("XOR decode requires xor_key")
    key_bytes = key.encode()
    return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))


def _extract_tar_member(data: bytes, member: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        try:
            entry = archive.getmember(member)
        except KeyError as exc:
            raise ValueError(f"Tar member not found: {member}") from exc
        extracted = archive.extractfile(entry)
        if extracted is None:
            raise ValueError(f"Could not extract tar member: {member}")
        return extracted.read()


def apply_transforms(
    data: bytes,
    *,
    decode: DecodeOption = "none",
    decompress: DecompressOption = "none",
    xor_key: Optional[str] = None,
    tar_member: Optional[str] = None,
) -> bytes:
    """Apply configured transforms: decode, decompress/extract tar, optional xor."""
    result = data

    if decode == "base64":
        try:
            result = base64.b64decode(result, validate=True)
        except Exception as exc:
            raise ValueError(f"Base64 decode failed: {exc}") from exc
    elif decode == "xor":
        result = _xor_decode(result, xor_key or "")
    elif decode != "none":
        raise ValueError(f"Unsupported decode option: {decode}")

    if decompress == "gzip":
        try:
            result = gzip.decompress(result)
        except Exception as exc:
            raise ValueError(f"Gzip decompress failed: {exc}") from exc
    elif decompress == "tar":
        if not tar_member:
            raise ValueError("decompress tar requires tar_member")
        result = _extract_tar_member(result, tar_member)
    elif decompress != "none":
        raise ValueError(f"Unsupported decompress option: {decompress}")

    return result
