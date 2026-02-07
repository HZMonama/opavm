from __future__ import annotations

import os
import shutil
import tempfile
import hashlib
from pathlib import Path
from typing import Callable

import httpx

from opavm.errors import DownloadError


def download_binary(
    url: str,
    destination: Path,
    timeout: float = 120.0,
    on_progress: Callable[[int | None, int], None] | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(dir=str(destination.parent), prefix="opa.", suffix=".tmp")
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
            response.raise_for_status()
            total_header = response.headers.get("Content-Length")
            total_bytes = int(total_header) if total_header and total_header.isdigit() else None
            downloaded_bytes = 0
            if on_progress is not None:
                on_progress(total_bytes, downloaded_bytes)
            with temp_path.open("wb") as fh:
                for chunk in response.iter_bytes():
                    if chunk:
                        fh.write(chunk)
                        downloaded_bytes += len(chunk)
                        if on_progress is not None:
                            on_progress(total_bytes, downloaded_bytes)
                fh.flush()
                os.fsync(fh.fileno())

        temp_path.chmod(temp_path.stat().st_mode | 0o111)
        os.replace(temp_path, destination)
    except httpx.HTTPError as exc:
        raise DownloadError("Download failed.", f"Could not fetch: {url}") from exc
    except OSError as exc:
        raise DownloadError("Install failed.", "Could not place downloaded binary.") from exc
    finally:
        if temp_path.exists():
            temp_path.unlink()


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def fetch_text(url: str, timeout: float = 30.0) -> str:
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        raise DownloadError("Checksum fetch failed.", f"Could not fetch: {url}") from exc


def parse_checksum_text(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        token = line.split()[0]
        if len(token) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in token):
            return token.lower()
    raise DownloadError("Invalid checksum file.", "No SHA256 value found.")
