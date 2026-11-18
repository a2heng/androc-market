#!/usr/bin/env python3
"""Build the kernel-opencode pack + delta from the official release.

The pack is a zstd-compressed raw ELF. The index is signed as exact bytes
(detached Ed25519 signature in index.json.sig).
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = "opencode-linux-arm64-musl.tar.gz"
PACK_ID = "kernel-opencode"
UA = "androc-market/1"


def log(*args):
    print(*args, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"User-Agent": UA, "Accept": "application/vnd.github+json"},
    )
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
    versions = [
        r["tag_name"].lstrip("v")
        for r in releases
        if not r.get("prerelease")
        and re.fullmatch(r"v?\d+\.\d+\.\d+", r.get("tag_name", ""))
    ]
    if not versions:
        raise SystemExit("no stable release found")
    return max(versions, key=version_key)


def release_info(upstream, version):
    return api(f"/repos/{upstream}/releases/tags/v{version}")


def download(url, dest, token_ok=True):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        log("cached", dest)
        return dest
    part = dest + ".part"
    headers = {"User-Agent": UA}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token_ok and token:
        headers["Authorization"] = f"Bearer {token}"
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as src, open(part, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
            os.replace(part, dest)
            return dest
        except Exception as exc:  # noqa: BLE001
            last = exc
            log(f"attempt {attempt + 1} failed: {exc}")
            time.sleep(min(2 ** attempt, 10))
    raise SystemExit(f"download failed: {url}: {last}")


def verify_official(release, tar_path):
    asset = next((a for a in release["assets"] if a["name"] == ASSET), None)
    if not asset:
        raise SystemExit(f"{ASSET} not found in release")
    size = os.path.getsize(tar_path)
    if size != asset["size"]:
        raise SystemExit(f"size mismatch: {size} != {asset['size']}")
    digest = asset.get("digest", "")
    if digest.startswith("sha256:"):
        want = digest.split(":", 1)[1]
        got = sha256_file(tar_path)
        if got != want:
            raise SystemExit(f"asset digest mismatch: {got} != {want}")
        log("official digest ok", got)
    sums = next((a for a in release["assets"] if a["name"] == "SHA256SUMS"), None)
    if sums:
        sums_path = os.path.join(os.path.dirname(tar_path), "SHA256SUMS")
        download(sums["browser_download_url"], sums_path)
        with open(sums_path, encoding="utf-8") as f:
            for line in f:
                if line.strip().endswith(ASSET):
                    want = line.split()[0]
                    got = sha256_file(tar_path)
                    if got != want:
                        raise SystemExit(f"SHA256SUMS mismatch: {got} != {want}")
                    log("SHA256SUMS ok")
                    break


def extract_binary(tar_path, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        member = next((m for m in tar.getmembers()
                       if m.isfile() and os.path.basename(m.name) == "opencode"), None)
        if not member:
            raise SystemExit("opencode binary not found in tar")
        with tar.extractfile(member) as src, open(dest, "wb") as out:
            shutil.copyfileobj(src, out, 1 << 20)
    os.chmod(dest, 0o755)
    return dest


def zstd(src, dest, level=19):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.run(
        ["zstd", f"-{level}", "-T0", "-f", "--long=27", src, "-o", dest],
        check=True,
    )
    return dest


def zstd_delta(old, new, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.run(
        ["zstd", "-19", "-T0", "--long=27", f"--patch-from={old}", new, "-o", dest],
        check=True,
    )
    return dest


def sign_index(path, key_path):
    with open(key_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("signing key is not Ed25519")
    with open(path, "rb") as f:
        payload = f.read()
    sig = key.sign(payload)
    with open(path + ".sig", "w", encoding="utf-8") as f:
        f.write(base64.b64encode(sig).decode() + "\n")


def release_url(repo, tag, asset):
    return f"https://github.com/{repo}/releases/download/{tag}/{asset}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default="anomalyco/opencode")
    ap.add_argument("--repo", default="a2heng/androc-market")
    ap.add_argument("--version", default="latest")
    ap.add_argument("--index", default=os.path.join(ROOT, "index.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--key", default=os.path.join(ROOT, ".keys", "market-signing-key.pem"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-delta", action="store_true")
    args = ap.parse_args()

    version = resolve_latest(args.upstream) if args.version == "latest" else args.version
    log("upstream version:", version)

    index = load_json(args.index, {"schema": 1, "channel": "stable", "packs": []})
    old = next((p for p in index.get("packs", []) if p.get("id") == PACK_ID), None)
    if old and old.get("upstreamVersion") == version and not args.force:
        log("NO_UPDATE")
        return 0

    info = release_info(args.upstream, version)
    cache = os.path.join(ROOT, ".cache", "opencode", version)
    tar_path = os.path.join(cache, ASSET)
    download(next(a for a in info["assets"] if a["name"] == ASSET)["browser_download_url"], tar_path)
    verify_official(info, tar_path)

    raw = extract_binary(tar_path, os.path.join(cache, "opencode"))
    raw_sha = sha256_file(raw)
    raw_size = os.path.getsize(raw)
    log("raw:", raw_size, raw_sha)

    pack_version = f"{version}-1"
    tag = f"{PACK_ID}-{pack_version}"
    os.makedirs(args.out, exist_ok=True)
    pack_name = f"{PACK_ID}-{pack_version}.zst"
    pack_path = os.path.join(args.out, pack_name)
    zstd(raw, pack_path)
    log("pack:", os.path.getsize(pack_path), sha256_file(pack_path))

    delta_entry = None
    if old and not args.no_delta and old.get("installed", {}).get("sha256") != raw_sha:
        try:
            old_raw = fetch_old_raw(old)
            if old_raw:
                delta_name = f"{PACK_ID}-{old['version']}-to-{pack_version}.zst"
                delta_path = os.path.join(args.out, delta_name)
                zstd_delta(old_raw, raw, delta_path)
                delta_entry = {
                    "from": old["version"],
                    "fromSha256": old["installed"]["sha256"],
                    "url": release_url(args.repo, tag, delta_name),
                    "size": os.path.getsize(delta_path),
                    "sha256": sha256_file(delta_path),
                    "long": 27,
                }
                log("delta:", delta_entry["size"], delta_entry["sha256"])
        except Exception as exc:  # noqa: BLE001
            log("delta skipped:", exc)

    entry = {
        "id": PACK_ID,
        "name": "OpenCode",
        "category": "kernel",
        "kind": "single-file",
        "version": pack_version,
        "upstreamVersion": version,
        "abi": "arm64-v8a",
        "minAppVersionCode": 9,
        "license": ["MIT"],
        "licenseUrl": "https://github.com/anomalyco/opencode/blob/dev/LICENSE",
        "installed": {"size": raw_size, "sha256": raw_sha},
        "archive": {
            "url": release_url(args.repo, tag, pack_name),
            "size": os.path.getsize(pack_path),
            "sha256": sha256_file(pack_path),
        },
        "delta": delta_entry,
    }

    packs = [p for p in index.get("packs", []) if p.get("id") != PACK_ID]
    index["schema"] = 1
    index["channel"] = index.get("channel", "stable")
    index["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    index.setdefault("upstream", {})["opencode"] = version
    index["packs"] = [entry] + packs
    index_path = os.path.join(args.out, "index.json")
    write_json(index_path, index)
    sign_index(index_path, args.key)
    log("index:", index_path)
    log("tag:", tag)
    return 0


def fetch_old_raw(old):
    """Return the old raw ELF for delta generation (cache or previous archive)."""
    old_version = old.get("version", "")
    cache = os.path.join(ROOT, ".cache", "opencode", old_version, "opencode")
    if os.path.isfile(cache):
        if sha256_file(cache) == old.get("installed", {}).get("sha256"):
            return cache
    url = old.get("archive", {}).get("url")
    if not url:
        return None
    archive = os.path.join(ROOT, ".cache", "opencode", old_version, "pack.zst")
    download(url, archive)
    out = os.path.join(ROOT, ".cache", "opencode", old_version, "opencode")
    subprocess.run(["zstd", "-d", "-f", "--long=27", archive, "-o", out], check=True)
    if sha256_file(out) != old.get("installed", {}).get("sha256"):
        raise SystemExit("previous pack hash mismatch")
    return out


if __name__ == "__main__":
    sys.exit(main())
