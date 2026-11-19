#!/usr/bin/env python3
"""Build the built-in runtime-core rootfs (aarch64 musl).

This is the OpenCode runtime payload: the same default set the old full build
shipped (bash/coreutils/git/python/node/openssh/make/curl/wget). It travels
with the OC component, so installing OC also gives you the terminal and the
MCP launchers. The android toolchain stays in its own pack.

It is consumed two ways:
  * the APK build fetches this pack and extracts it into assets/runtime/
  * `LocalRuntime` uses it as the proot `-r` root; the android pack overlays
    the toolchain on top.

Runs inside an Alpine container (x86_64) with cross-install support.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALPINE = "3.20.9"
ALPINE_URL = ("https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/aarch64/"
              f"alpine-minirootfs-{ALPINE}-aarch64.tar.gz")

PACKAGES = [
    # shell / terminal（旧 full 的默认集）
    "bash",
    "busybox",
    "coreutils",
    "ncurses",
    "readline",
    "util-linux",
    "tzdata",
    # TLS + 旧默认工具
    "ca-certificates",
    "git",
    "python3",
    "py3-pip",
    "nodejs",
    "npm",
    "openssh",
    "make",
    "curl",
    "wget",
    "tar",
    "xz",
    "unzip",
    "zlib",
    "libstdc++",
    "libgcc",
    "gcompat",
]


def log(*args):
    print(*args, flush=True)


def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        log("cached", dest)
        return dest
    part = dest + ".part"
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "androc"})
            with urllib.request.urlopen(req, timeout=300) as src, open(part, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
            os.replace(part, dest)
            return dest
        except Exception as exc:  # noqa: BLE001
            last = exc
            log(f"attempt {attempt + 1} failed: {exc}")
            time.sleep(min(2 ** attempt, 10))
    if shutil.which("curl"):
        subprocess.run(["curl", "-fL", "--retry", "10", "--retry-all-errors",
                        "-A", "androc", "-o", dest, url], check=True)
        return dest
    raise SystemExit(f"download failed: {url}: {last}")


def run(cmd, **kwargs):
    log("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "packs", "runtime-core", "rootfs"))
    ap.add_argument("--cache", default=os.path.join(ROOT, ".cache", "runtime-core"))
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    cache = os.path.abspath(args.cache)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)

    mini = download(ALPINE_URL, os.path.join(cache, os.path.basename(ALPINE_URL)))
    log("extract", mini)
    with tarfile.open(mini, "r:gz") as tar:
        tar.extractall(out)

    with open(os.path.join(out, "etc/apk/repositories"), "w", encoding="utf-8") as f:
        f.write("https://dl-cdn.alpinelinux.org/alpine/v3.20/main\n")
        f.write("https://dl-cdn.alpinelinux.org/alpine/v3.20/community\n")

    run(["apk", "--root", out, "--arch", "aarch64", "--initdb",
         "--allow-untrusted", "--no-scripts", "add"] + PACKAGES)

    total = 0
    for root_dir, _, files in os.walk(out):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root_dir, name))
            except OSError:
                pass
    log("runtime-core:", out, "size:", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
