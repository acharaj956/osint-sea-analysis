"""Data integrity helpers.

Open-source investigations require demonstrable data integrity: the ability
to show that an artifact has not changed since collection. These helpers
produce SHA-256 digests for files and byte streams, aligned with the
preservation principles of the Berkeley Protocol on Digital Open Source
Investigations (UN Human Rights, 2022).
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path, chunk_size: int = 8192) -> str:
    """Return the SHA-256 hex digest of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of an in-memory byte string."""
    return hashlib.sha256(data).hexdigest()
