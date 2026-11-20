#!/usr/bin/env python3
"""Build kernel-opencode = opencode binary + runtime-core rootfs in one tar pack.

The runtime used to be a separate pack; it now travels with OpenCode so
installing the single `kernel-opencode` component gives a working local OC
(binary + musl rootfs). No delta; the app always downloads the full pack.
"""
import argparse
import hashlib
import io
import json
import lzma
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = "opencode-linux-arm64-musl.tar.gz"
PACK_ID = "kernel-opencode"
REPO = "a2heng/androc-market"
UA = "androc-market/1"


def log(*args):
    print(*args, flush=True)


def run(cmd):
    log("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


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


def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return dest
    part = dest + ".part"
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as src, open(part, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
            os.replace(part, dest)
            return dest
        except Exception as exc:  # noqa: BLE001
            last = exc
            log(f"attempt {attempt + 1} failed: {exc}")
            time.sleep(min(2 ** attempt, 10))
    raise SystemExit(f"download failed: {url}: {last}")


def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"User-Agent": UA,
                                          "Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def version_key(tag):
    core = tag.lstrip("v").split("-")[0]
    nums = [int(x) for x in core.split(".") if x.isdigit()]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def resolve_latest(upstream):
    releases = api(f"/repos/{upstream}/releases?per_page=100")
    versions = [r["tag_name"].lstrip("v") for r in releases
                if not r.get("prerelease")
                and re.fullmatch(r"v?\d+\.\d+\.\d+", r.get("tag_name", ""))]
    return max(versions, key=version_key)


def extract_binary(tar_path, dest):
    with tarfile.open(tar_path, "r:gz") as tar:
        member = next((m for m in tar.getmembers()
                       if m.isfile() and os.path.basename(m.name) == "opencode"), None)
        if not member:
            raise SystemExit("opencode binary not found in official tar")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with tar.extractfile(member) as src, open(dest, "wb") as out:
            shutil.copyfileobj(src, out, 1 << 20)
    os.chmod(dest, 0o755)


def add_entry(tar, path, arcname, is_dir):
    info = tarfile.TarInfo(arcname)
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    if os.path.islink(path):
        info.type = tarfile.SYMTYPE
        info.linkname = os.readlink(path)
        info.mode = 0o777
        tar.addfile(info)
        return
    if is_dir:
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        tar.addfile(info)
        return
    if not os.path.isfile(path):
        return
    with open(path, "rb") as f:
        data = f.read()
    info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def build_tar(src, path):
    with tarfile.open(path, mode="w", format=tarfile.PAX_FORMAT) as tar:
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
                rel = os.path.join(rel_root, f).replace(os.sep, "/")
                add_entry(tar, os.path.join(root, f), rel, False)
    return os.path.getsize(path), sha256_file(path)


def compress_xz(src, dest):
    with open(dest, "wb") as out:
        subprocess.run(["xz", "-9", "-T0", "-c", src], stdout=out, check=True)


def sign_index(path, key_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    with open(key_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("signing key is not Ed25519")
    with open(path, "rb") as f:
        payload = f.read()
    import base64
    with open(path + ".sig", "w", encoding="utf-8") as f:
        f.write(base64.b64encode(key.sign(payload)).decode() + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default="anomalyco/opencode")
    ap.add_argument("--version", default="latest")
    ap.add_argument("--index", default=os.path.join(ROOT, "index.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--key", default=os.path.join(ROOT, ".keys", "market-signing-key.pem"))
    ap.add_argument("--no-sign", action="store_true")
    args = ap.parse_args()

    version = resolve_latest(args.upstream) if args.version == "latest" else args.version
    cache = os.path.join(ROOT, ".cache", "opencode", version)
    tar_gz = download(
        f"https://github.com/{args.upstream}/releases/download/v{version}/{ASSET}",
        os.path.join(cache, ASSET))
    stage = os.path.join(cache, "stage")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage, exist_ok=True)

    log("extract opencode binary")
    extract_binary(tar_gz, os.path.join(stage, "opencode"))

    log("build runtime rootfs")
    # rootfs 只属于 OC 包：不再发布独立的 runtime-core 包。
    rootfs = os.path.join(cache, "rootfs")
    if not os.path.isdir(os.path.join(rootfs, "bin")):
        run([sys.executable, os.path.join(ROOT, "scripts", "build-runtime-core.py"),
             "--out", rootfs, "--cache", os.path.join(ROOT, ".cache", "runtime-core")])
    shutil.copytree(rootfs, os.path.join(stage, "rootfs"), symlinks=True,
                    dirs_exist_ok=True)

    tar_path = os.path.join(args.out, f"{PACK_ID}-{version}-2.tar")
    os.makedirs(args.out, exist_ok=True)
    installed_size, installed_sha = build_tar(stage, tar_path)
    archive_path = os.path.join(args.out, f"{PACK_ID}-{version}-2.tar.xz")
    compress_xz(tar_path, archive_path)
    os.remove(tar_path)

    index = {}
    if os.path.isfile(args.index):
        with open(args.index, encoding="utf-8") as f:
            index = json.load(f)
    tag = f"{PACK_ID}-{version}-2"
    entry = {
        "id": PACK_ID,
        "name": "OpenCode",
        "category": "kernel",
        "kind": "tar",
        "version": f"{version}-2",
        "upstreamVersion": version,
        "abi": "arm64-v8a",
        "minAppVersionCode": 9,
        "license": ["MIT"],
        "licenseUrl": "https://github.com/anomalyco/opencode/blob/dev/LICENSE",
        "summary": "opencode binary + musl runtime (bash/git/python/node)",
        "installed": {"size": installed_size, "sha256": installed_sha},
        "archive": {
            "url": f"https://github.com/{REPO}/releases/download/{tag}/"
                   f"{os.path.basename(archive_path)}",
            "size": os.path.getsize(archive_path),
            "sha256": sha256_file(archive_path),
            "format": "xz",
        },
        "delta": None,
    }
    index["schema"] = 1
    index["channel"] = index.get("channel", "stable")
    index.setdefault("upstream", {})["opencode"] = version
    index["packs"] = [entry] + [p for p in index.get("packs", []) if p.get("id") != PACK_ID]
    index_path = os.path.join(args.out, "index.json")
    write_json(index_path, index)
    if not args.no_sign:
        sign_index(index_path, args.key)
    log("tag:", tag, "installed:", installed_size, "archive:", entry["archive"]["size"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
