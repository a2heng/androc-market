#!/usr/bin/env python3
"""Build a directory pack and merge it into the signed market index.

Pack layout (in this repo):

    packs/<id>/pack.json      metadata (id, name, version, category, ...)
    packs/<id>/**             payload

The payload is packed into a deterministic tar.xz.  `installed` in the index
is the SHA-256 of the *uncompressed tar stream*, so the app can verify the
download and the extraction in one pass.

After the archive is written, the entry is merged into `index.json` and the
exact index bytes are signed with Ed25519 (`index.json.sig`).

Usage:
    python3 scripts/build-pack.py --dir packs/android --out dist
    python3 scripts/build-pack.py --all --out dist
"""
import argparse
import base64
import hashlib
import io
import json
import lzma
import os
import sys
import tarfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "a2heng/androc-market"


def log(*args):
    print(*args, flush=True)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def add_entry(tar, path, arcname, is_dir):
    info = tarfile.TarInfo(arcname)
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    if is_dir:
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        tar.addfile(info)
    else:
        with open(path, "rb") as f:
            data = f.read()
        info.mode = 0o755 if os.access(path, os.X_OK) and not path.endswith(
            (".md", ".json", ".txt", ".sh", ".py", ".kt", ".java")) else 0o644
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def build_tar(src):
    """Deterministic tar of the pack directory (pack.json excluded)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for root, dirs, files in os.walk(src):
            dirs.sort()
            files.sort()
            rel_root = os.path.relpath(root, src)
            if rel_root == ".":
                rel_root = ""
            for d in dirs:
                rel = os.path.join(rel_root, d).replace(os.sep, "/")
                add_entry(tar, os.path.join(root, d), rel, True)
            for f in files:
                if not rel_root and f == "pack.json":
                    continue
                rel = os.path.join(rel_root, f).replace(os.sep, "/")
                add_entry(tar, os.path.join(root, f), rel, False)
    return buf.getvalue()


def sign_index(path, key_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    with open(key_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("signing key is not Ed25519")
    with open(path, "rb") as f:
        payload = f.read()
    sig = key.sign(payload)
    with open(path + ".sig", "w", encoding="utf-8") as f:
        f.write(base64.b64encode(sig).decode() + "\n")


def load_json(path, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pack_dirs():
    base = os.path.join(ROOT, "packs")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if os.path.isfile(os.path.join(d, "pack.json")):
            out.append(d)
    return out


def build_one(src, out_dir, index):
    with open(os.path.join(src, "pack.json"), encoding="utf-8") as f:
        meta = json.load(f)
    pack_id = meta["id"]
    version = meta["version"]
    tar_bytes = build_tar(src)
    installed_sha = sha256_bytes(tar_bytes)
    installed_size = len(tar_bytes)
    xz_bytes = lzma.compress(
        tar_bytes, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME
    )
    archive_name = f"{pack_id}-{version}.tar.xz"
    os.makedirs(out_dir, exist_ok=True)
    archive_path = os.path.join(out_dir, archive_name)
    with open(archive_path, "wb") as f:
        f.write(xz_bytes)
    tag = f"{pack_id}-{version}"
    entry = {
        "id": pack_id,
        "name": meta["name"],
        "category": meta.get("category", "skills"),
        "kind": "tar",
        "version": version,
        "upstreamVersion": meta.get("upstreamVersion", version.split("-")[0]),
        "abi": meta.get("abi", "arm64-v8a"),
        "minAppVersionCode": meta.get("minAppVersionCode", 9),
        "license": meta.get("license", ["MIT"]),
        "licenseUrl": meta.get("licenseUrl", ""),
        "summary": meta.get("summary", ""),
        "installed": {"size": installed_size, "sha256": installed_sha},
        "archive": {
            "url": f"https://github.com/{REPO}/releases/download/{tag}/{archive_name}",
            "size": len(xz_bytes),
            "sha256": sha256_file(archive_path),
            "format": "xz",
        },
        "delta": None,
    }
    packs = [p for p in index.get("packs", []) if p.get("id") != pack_id]
    index["packs"] = [entry] + packs
    log(f"{pack_id}: {installed_size} -> {len(xz_bytes)} bytes, tag {tag}")
    return tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", help="one pack directory (contains pack.json)")
    ap.add_argument("--all", action="store_true", help="build every packs/*/pack.json")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--index", default=os.path.join(ROOT, "index.json"))
    ap.add_argument("--key", default=os.path.join(ROOT, ".keys", "market-signing-key.pem"))
    ap.add_argument("--no-sign", action="store_true", help="local test only")
    args = ap.parse_args()

    dirs = []
    if args.all:
        dirs = pack_dirs()
    elif args.dir:
        dirs = [args.dir if os.path.isabs(args.dir) else os.path.join(ROOT, args.dir)]
    if not dirs:
        raise SystemExit("nothing to build: pass --dir or --all")

    index = load_json(args.index, {"schema": 1, "channel": "stable", "packs": []})
    index["schema"] = 1
    index["channel"] = index.get("channel", "stable")
    index["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tags = [build_one(d, args.out, index) for d in dirs]

    index_path = os.path.join(args.out, "index.json")
    write_json(index_path, index)
    if not args.no_sign:
        sign_index(index_path, args.key)
    log("tags:", " ".join(tags))
    return 0


if __name__ == "__main__":
    sys.exit(main())
