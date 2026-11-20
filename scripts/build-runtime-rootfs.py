#!/usr/bin/env python3
"""构建 bundle 内置的 musl rootfs（构建输入，不进市场索引）。

输出 dist/runtime-rootfs.tar.xz，内容只有 `rootfs/`。bundle APK 构建时下载它
放进 assets/runtime/，首次启动解压到 files/runtime-core/。
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--cache", default=os.path.join(ROOT, ".cache", "runtime-core"))
    args = ap.parse_args()

    rootfs = os.path.join(args.cache, "rootfs")
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build-runtime-core.py"),
                    "--out", rootfs, "--cache", args.cache], check=True)
    for probe in ("bin/sh", "usr/bin/python3", "usr/bin/node", "usr/bin/git"):
        if not os.path.exists(os.path.join(rootfs, probe)):
            raise SystemExit(f"rootfs missing {probe}")

    os.makedirs(args.out, exist_ok=True)
    dest = os.path.join(args.out, "runtime-rootfs.tar.xz")
    part = dest + ".part"
    subprocess.run(["tar", "-cJf", part, "-C", args.cache, "rootfs"], check=True)
    os.replace(part, dest)
    print("wrote", dest, os.path.getsize(dest), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
