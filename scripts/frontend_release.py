"""Pack a locally built frontend or verify/install it into an empty deployment dist.

No model, database or account access. The source checkout must match the bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def revision():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def pack():
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", "frontend"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    if subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "--", "frontend"], cwd=ROOT):
        raise ValueError("Commit frontend source changes before packing a release.")
    dist = ROOT / "frontend/dist"
    if not (dist / "index.html").is_file():
        raise ValueError("Run the production frontend build first.")
    files = {}
    for path in dist.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed in a release.")
        if path.is_file() and path.name != "release.json":
            files[path.relative_to(dist).as_posix()] = path.read_bytes()
    manifest = {"commit": revision(), "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    target = ROOT / "artifacts/react-release" / f"{manifest['commit']}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("release.json", json.dumps(manifest, sort_keys=True))
    print(json.dumps({"archive": str(target), "commit": manifest["commit"], "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size}))


def install(path, expected):
    if path.stat().st_size > 25_000_000 or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Release size/hash check failed.")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) > 100 or len(names) != len(set(names)) or sum(i.file_size for i in archive.infolist()) > 25_000_000:
            raise ValueError("Release bounds/duplicate check failed.")
        for name in names:
            value = PurePosixPath(name)
            if value.is_absolute() or ".." in value.parts or "\\" in name or ":" in name:
                raise ValueError("Unsafe archive path.")
        manifest = json.loads(archive.read("release.json"))
        if manifest["commit"] != revision() or set(names) != set(manifest["files"]) | {"release.json"}:
            raise ValueError("Bundle does not match this checkout or its file manifest.")
        contents = {name: archive.read(name) for name in names}
        if any(hashlib.sha256(contents[name]).hexdigest() != digest for name, digest in manifest["files"].items()):
            raise ValueError("Asset integrity check failed.")
        if "index.html" not in contents:
            raise ValueError("Release has no entry page.")
    dist = ROOT / "frontend/dist"
    if dist.is_symlink() or not dist.resolve().is_relative_to((ROOT / "frontend").resolve()):
        raise ValueError("Unexpected distribution path.")
    if dist.exists() and any(dist.iterdir()):
        raise ValueError("Target dist is not empty. Preserve the previous build before installing; nothing overwritten.")
    dist.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        target = dist / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(json.dumps({"installed_commit": manifest["commit"], "asset_count": len(contents), "verified": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("pack", "install"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    if args.operation == "pack":
        pack()
    else:
        if not args.archive or not args.sha256:
            parser.error("install requires --archive and --sha256")
        install(args.archive, args.sha256)
