#!/usr/bin/env python3
"""Export one file from a Zeabur volume and verify a compressed SQLite backup."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile


CHUNK_BYTES = 512 * 1024
BASE64_LINE = re.compile(r"^[A-Za-z0-9+/=]+$")


def _run_remote(service_id: str, environment_id: str, command: str) -> str:
    result = subprocess.run(
        [
            "zeabur", "service", "exec",
            "--id", service_id,
            "--env-id", environment_id,
            "--", "sh", "-c", command,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _remote_metadata(service_id: str, environment_id: str, remote_path: str) -> tuple[int, str]:
    quoted = shlex.quote(remote_path)
    output = _run_remote(
        service_id,
        environment_id,
        f"stat -c %s {quoted}; sha256sum {quoted}",
    )
    size_match = re.search(r"(?m)^(\d+)$", output)
    hash_match = re.search(r"(?m)^([0-9a-f]{64})\s", output)
    if not size_match or not hash_match:
        raise RuntimeError("Zeabur did not return valid file metadata")
    return int(size_match.group(1)), hash_match.group(1)


def _decode_chunk_output(output: str) -> bytes:
    encoded = "".join(
        line.strip()
        for line in output.splitlines()
        if BASE64_LINE.fullmatch(line.strip())
    )
    if not encoded:
        raise RuntimeError("Zeabur returned an empty backup chunk")
    return base64.b64decode(encoded, validate=True)


def _download_chunk(
    service_id: str,
    environment_id: str,
    remote_path: str,
    index: int,
    expected_size: int,
) -> tuple[int, bytes]:
    quoted = shlex.quote(remote_path)
    output = _run_remote(
        service_id,
        environment_id,
        f"dd if={quoted} bs={CHUNK_BYTES} skip={index} count=1 status=none | base64",
    )
    data = _decode_chunk_output(output)
    if len(data) != expected_size:
        raise RuntimeError(
            f"Backup chunk {index} has {len(data)} bytes; expected {expected_size}"
        )
    return index, data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_sqlite_gzip(path: Path) -> str:
    with tempfile.NamedTemporaryFile(suffix=".db") as restored:
        with gzip.open(path, "rb") as source:
            shutil.copyfileobj(source, restored)
        restored.flush()
        connection = sqlite3.connect(f"file:{restored.name}?mode=ro", uri=True)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
    if result != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {result}")
    return result


def export_file(
    service_id: str,
    environment_id: str,
    remote_path: str,
    output_path: Path,
    workers: int = 8,
) -> dict:
    if not remote_path.startswith("/"):
        raise ValueError("remote path must be absolute")
    size, remote_hash = _remote_metadata(service_id, environment_id, remote_path)
    chunk_count = (size + CHUNK_BYTES - 1) // CHUNK_BYTES
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="zhihuiti-export-") as temporary:
        part_dir = Path(temporary)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = []
            for index in range(chunk_count):
                expected = min(CHUNK_BYTES, size - index * CHUNK_BYTES)
                futures.append(pool.submit(
                    _download_chunk,
                    service_id,
                    environment_id,
                    remote_path,
                    index,
                    expected,
                ))
            for future in concurrent.futures.as_completed(futures):
                index, data = future.result()
                (part_dir / f"{index:08d}.part").write_bytes(data)

        temporary_output = output_path.with_suffix(output_path.suffix + ".partial")
        with temporary_output.open("wb") as destination:
            for index in range(chunk_count):
                with (part_dir / f"{index:08d}.part").open("rb") as part:
                    shutil.copyfileobj(part, destination)
        local_hash = _sha256(temporary_output)
        if local_hash != remote_hash:
            temporary_output.unlink(missing_ok=True)
            raise RuntimeError("Downloaded backup checksum does not match production")
        temporary_output.replace(output_path)

    integrity = _verify_sqlite_gzip(output_path)
    return {
        "path": str(output_path),
        "size_bytes": size,
        "sha256": remote_hash,
        "sqlite_integrity": integrity,
        "chunks": chunk_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--remote-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    result = export_file(
        args.service_id,
        args.environment_id,
        args.remote_path,
        args.output,
        args.workers,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
