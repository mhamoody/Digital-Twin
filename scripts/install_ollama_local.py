"""Install an official Ollama Linux release inside ignored var/tools, without sudo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import tarfile
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", help="Official release tag, e.g. vX.Y.Z; defaults to latest release"
    )
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
        parser.error("This installer is for the x86-64 Linux Lobot allocation only.")
    if args.version and not re.fullmatch(
        r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", args.version
    ):
        parser.error("Use an official version tag")
    import zstandard

    os.umask(0o077)
    root = Path(__file__).resolve().parents[1]
    release_path = f"tags/{args.version}" if args.version else "latest"
    with httpx.Client(
        follow_redirects=True, timeout=120, headers={"User-Agent": "course-digital-twin-setup"}
    ) as client:
        reply = client.get(f"https://api.github.com/repos/ollama/ollama/releases/{release_path}")
        reply.raise_for_status()
        release = reply.json()
        tag = release["tag_name"]
        if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", tag):
            raise SystemExit("Unrecognized release tag; installation stopped.")
        asset = next(
            (a for a in release["assets"] if a["name"] == "ollama-linux-amd64.tar.zst"), None
        )
        if asset is None:
            raise SystemExit("This release has no expected Linux archive; installation stopped.")
        url = asset["browser_download_url"]
        if not url.startswith(f"https://github.com/ollama/ollama/releases/download/{tag}/"):
            raise SystemExit("Unexpected download source; installation stopped.")
        archive = root / "var" / "downloads" / f"ollama-{tag}.tar.zst"
        install = root / "var" / "tools" / f"ollama-{tag}"
        archive.parent.mkdir(parents=True, exist_ok=True)
        if (install / "bin" / "ollama").is_file() and (install / "release.json").is_file():
            print(f"Release already installed: {tag}")
        else:
            print(f"Downloading official Ollama {tag}; this may take several minutes.", flush=True)
            checksum = hashlib.sha256()
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with archive.open("wb") as handle:
                    for chunk in response.iter_bytes(1024 * 1024):
                        handle.write(chunk)
                        checksum.update(chunk)
            actual = checksum.hexdigest()
            expected = asset.get("digest")
            if expected and expected != "sha256:" + actual:
                raise SystemExit("Archive digest verification failed; nothing was extracted.")
            install.mkdir(parents=True, exist_ok=True)
            with (
                archive.open("rb") as source,
                zstandard.ZstdDecompressor().stream_reader(source) as reader,
            ):
                with tarfile.open(fileobj=reader, mode="r|") as package:
                    package.extractall(install, filter="data")
            (install / "release.json").write_text(
                json.dumps(
                    {
                        "tag": tag,
                        "url": url,
                        "sha256": actual,
                        "publisher_digest_verified": bool(expected),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
    binary = install / "bin" / "ollama"
    if not binary.is_file():
        raise SystemExit("Expected binary not found; no active runtime was changed.")
    binary.chmod(0o700)
    (root / "var" / "tools" / "ollama-path.txt").write_text(str(binary), encoding="utf-8")
    print("Local runtime installed. No system service or GPU driver was modified.")


if __name__ == "__main__":
    main()
