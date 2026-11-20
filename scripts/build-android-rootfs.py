#!/usr/bin/env python3
"""Assemble the aarch64 musl rootfs for the Android plugin.

Runs inside an Alpine container (x86_64). It cross-installs aarch64 packages
into an Alpine minirootfs, then adds the static aarch64 Android build-tools,
the platform android.jar, Gradle and the android-* skills.

The result is `packs/android/rootfs/` plus a small `env.sh`; the normal
`build-pack.py --dir packs/android` then packs skills + rootfs into the
signed market entry.

Tested layout inside the pack:

    packs/android/
    ├─ pack.json
    ├─ skills/...
    └─ rootfs/
       ├─ bin/sh, usr/lib/jvm/java-21-openjdk/...
       └─ opt/android-sdk/{build-tools,platforms}
       └─ opt/gradle/gradle-9.9.0
       └─ opt/androc/env.sh
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALPINE = "3.20.9"
ALPINE_URL = ("https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/aarch64/"
              f"alpine-minirootfs-{ALPINE}-aarch64.tar.gz")
TOOLS_URL = ("https://github.com/lzhiyong/android-sdk-tools/releases/download/"
             "35.0.2/android-sdk-tools-static-aarch64.zip")
PLATFORM_URL = "https://dl.google.com/android/repository/platform-36_r01.zip"
GRADLE_VERSION = "9.9.0"
GRADLE_URL = ("https://services.gradle.org/distributions/"
              f"gradle-{GRADLE_VERSION}-bin.zip")
BT_VERSION = "36.0.0"
PLATFORM_VERSION = "36"

PACKAGES = [
    "openjdk21",
    "bash",
    "busybox",
    "coreutils",
    "zip",
    "unzip",
    "ca-certificates",
    "fontconfig",
    "freetype",
    "libstdc++",
    "libgcc",
    "zlib",
    "gcompat",
    "ncurses",
    "readline",
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
    ap.add_argument("--out", default=os.path.join(ROOT, "packs", "android", "rootfs"))
    ap.add_argument("--cache", default=os.path.join(ROOT, ".cache", "rootfs"))
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    cache = os.path.abspath(args.cache)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)

    # 1. Alpine minirootfs
    mini = download(ALPINE_URL, os.path.join(cache, os.path.basename(ALPINE_URL)))
    log("extract", mini)
    with tarfile.open(mini, "r:gz") as tar:
        tar.extractall(out)

    # 2. aarch64 repositories
    with open(os.path.join(out, "etc/apk/repositories"), "w", encoding="utf-8") as f:
        f.write("https://dl-cdn.alpinelinux.org/alpine/v3.20/main\n")
        f.write("https://dl-cdn.alpinelinux.org/alpine/v3.20/community\n")

    # 3. Cross-install aarch64 packages into the rootfs
    run(["apk", "--root", out, "--arch", "aarch64", "--initdb",
         "--allow-untrusted", "--no-scripts", "add"] + PACKAGES)

    sdk = os.path.join(out, "opt", "android-sdk")
    bt = os.path.join(sdk, "build-tools", BT_VERSION)
    os.makedirs(bt, exist_ok=True)

    # 4. Static aarch64 build-tools (run on musl without bionic)
    tools_zip = download(TOOLS_URL, os.path.join(cache, "android-sdk-tools-aarch64.zip"))
    tmp = os.path.join(cache, "tools")
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(tools_zip) as z:
        z.extractall(tmp)
    src_bt = os.path.join(tmp, "build-tools")
    for name in os.listdir(src_bt):
        src = os.path.join(src_bt, name)
        if os.path.isfile(src):
            dst = os.path.join(bt, name)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
    adb = os.path.join(tmp, "platform-tools", "adb")
    if os.path.isfile(adb):
        os.makedirs(os.path.join(out, "opt", "platform-tools"), exist_ok=True)
        shutil.copy2(adb, os.path.join(out, "opt", "platform-tools", "adb"))
        os.chmod(os.path.join(out, "opt", "platform-tools", "adb"), 0o755)

    # 5. aapt2 / adb 采用 zip 里的静态 aarch64 版本，直接在 musl rootfs 里执行。
    with open(os.path.join(bt, "source.properties"), "w", encoding="utf-8") as f:
        f.write(f"Pkg.Revision={BT_VERSION}
")
        f.write("Pkg.Desc=Android SDK Build-Tools
")
    stubs = os.path.join(ROOT, "packs", "android", "tools", "core-lambda-stubs.jar")
    if os.path.isfile(stubs):
        shutil.copy2(stubs, os.path.join(bt, "core-lambda-stubs.jar"))
    else:
        log("warning: missing", stubs)

    # 6. Platform android.jar
    platform_zip = download(PLATFORM_URL, os.path.join(cache, "platform.zip"))
    platforms = os.path.join(sdk, "platforms")
    os.makedirs(platforms, exist_ok=True)
    with zipfile.ZipFile(platform_zip) as z:
        z.extractall(platforms)
    plat = os.path.join(platforms, f"android-{PLATFORM_VERSION}")
    # AGP 读取这四样来识别 platform。
    for name in ("android.jar", "source.properties", "build.prop",
                 "core-for-system-modules.jar"):
        if not os.path.isfile(os.path.join(plat, name)):
            raise SystemExit(f"platform android-{PLATFORM_VERSION} missing {name}")

    # 7. Gradle
    gradle_zip = download(GRADLE_URL, os.path.join(cache,
                                                   f"gradle-{GRADLE_VERSION}-bin.zip"))
    gradle_dir = os.path.join(out, "opt", "gradle")
    os.makedirs(gradle_dir, exist_ok=True)
    with zipfile.ZipFile(gradle_zip) as z:
        members = [m for m in z.namelist() if m.startswith(f"gradle-{GRADLE_VERSION}/")]
        z.extractall(gradle_dir, members)
    # zip 不解出可执行位：gradle 启动脚本必须 755。
    for name in os.listdir(os.path.join(gradle_dir, f"gradle-{GRADLE_VERSION}", "bin")):
        os.chmod(os.path.join(gradle_dir, f"gradle-{GRADLE_VERSION}", "bin", name), 0o755)

    # 8. JVM 需要 RW -> RWX mprotect，Android 拒绝；用 LD_PRELOAD 的 shim 兼容。
    fixexec_src = os.path.join(ROOT, "packs", "android", "tools", "fixexec", "fixexec.c")
    fixexec_lib = os.path.join(out, "usr", "local", "lib", "fixexec.so")
    if os.path.isfile(fixexec_src) and shutil.which("zig"):
        os.makedirs(os.path.dirname(fixexec_lib), exist_ok=True)
        run(["zig", "cc", "-target", "aarch64-linux-musl", "-shared", "-fPIC",
             "-O2", "-o", fixexec_lib, fixexec_src])
        os.chmod(fixexec_lib, 0o755)
    else:
        log("warning: fixexec not built (need zig + source)")

    # 9. Skills

    skills_src = os.path.join(ROOT, "packs", "android", "skills")
    skills_dst = os.path.join(out, "opt", "androc", "skills")
    if os.path.isdir(skills_src):
        shutil.copytree(skills_src, skills_dst, dirs_exist_ok=True)

    # 9. env.sh for the proot shell
    env = os.path.join(out, "opt", "androc", "env.sh")
    with open(env, "w", encoding="utf-8") as f:
        f.write("export ANDROID_HOME=/opt/android-sdk\n")
        f.write("export ANDROID_SDK_ROOT=/opt/android-sdk\n")
        f.write("export JAVA_HOME=/usr/lib/jvm/java-21-openjdk\n")
        f.write("export PATH=/opt/android-sdk/build-tools/%s:"
                "/opt/android-sdk/platform-tools:"
                "/opt/gradle/gradle-%s/bin:"
                "$JAVA_HOME/bin:$PATH\n" % (BT_VERSION, GRADLE_VERSION))

    # 11. Sanity check
    for path in ["bin/sh", "usr/lib/jvm", "opt/android-sdk/build-tools",
                 "opt/android-sdk/platforms"]:
        if not os.path.exists(os.path.join(out, path)):
            log("warning: missing", path)

    total = 0
    for root_dir, _, files in os.walk(out):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root_dir, name))
            except OSError:
                pass
    log("rootfs:", out, "size:", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
