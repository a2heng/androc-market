---
name: Termux Toolbox
description: 使用这台手机上内置的 Termux 用户空间（bash、git、python、node、clang、cmake、ninja、ssh、pkg/apt、adb），并避开 Android 与 Termux 之间的路径陷阱。当任务需要在设备上使用 Linux 工具、命令报 “not found” 或 “CANNOT LINK EXECUTABLE”、或需要安装软件包时使用。
---

# Androc 上的 Termux 工具箱

Androc 在 APK 内打包了一套 Termux 风格的用户空间。它不是 Termux 应用：
没有单独的 Termux 安装，你也不需要装。工具箱已在 `PATH` 上，但**它的二进制
只能在 proot 内工作**（release 引擎会强制这一点；见下文）。

## 原生与 proot（先读这段）

手机上存在两类二进制：

1. **Android 系统二进制** —— `/system/bin/sh`、`am`、`pm`、`dumpsys`、
   `logcat`、`input`、`screencap`。它们可以直接运行。
2. **Termux/工具链二进制** —— `bash`、`git`、`python`、`node`、`clang`、
   `cmake`、`ninja`、`ssh`、`curl`、`pkg`、`apt`、`adb`……以及
   `$HOME/toolchain` 下的一切。它们位于应用私有存储中；如果原生进程试图
   `execve` 它们，Android 会返回 `Permission denied`（EACCES）。

**一切都已经运行在 proot 内**：opencode 服务器、这个 shell、终端以及每个子
进程都是。没有模式（`auto`/`fast`/`native`），也没有命令白名单。代理只需写
命令，不需要包装。

```sh
pwd
ls -la
git status
python3 app.py
bash scripts/build.sh
adb devices
pkg install -y jq
am start -n com.example/.MainActivity
```

变量、`cd`、管道和复合命令也能直接使用：

```sh
ADB="$HOME/toolchain/platform-tools/adb"; "$ADB" devices
cd "$HOME/workspace/App" && ./gradlew assembleDebug
```

规则：

- 命令的工作目录是会话目录（`/api/location`），不是 HOME。
- 优先使用 `$PREFIX/bin/adb` 处的 Termux `adb`（与 aarch64 构建匹配），
  而不是 `$HOME/toolchain/platform-tools/adb`。
- 系统命令（`am`、`pm`、`dumpsys`……）在 `$PREFIX/bin` 里有包装脚本，它们
  在 exec `/system/bin/*` 之前会先清除 Termux 的库变量。
- 绝不要从 Java/`ProcessBuilder` 里 `chmod +x` 并执行应用私有目录下的二进制；
  Android 会拒绝。改用 shell。
- 如果出现路径/库错误，先运行 `oc-doctor`，再运行 `oc-repair`。
  两者都记录在 `docs/commands.md` 和 `docs/paths.md` 里。

不要混用它们的库：Android 二进制不得继承 Termux 的 `LD_LIBRARY_PATH`，
Termux 二进制也不得手工用 Android 的 linker 启动。

## 路径

| 内容 | 路径 |
|---|---|
| 代理看到的 Home | `$HOME` = 应用私有 home（`/data/data/<pkg>/files/home`；始终使用 `$HOME`） |
| 项目根目录 | `$HOME/workspace`；会话当前目录通常是它下面的某个目录 |
| Termux 前缀 | `$PREFIX` = `/data/data/com.termux/files/usr` |
| JDK 21 | `$PREFIX/lib/jvm/java-21-openjdk`（不是 `$HOME/toolchain`） |
| Android SDK | `$HOME/toolchain/android-sdk`（SDK 36，build-tools 36.0.0） |
| Gradle | `$HOME/toolchain/gradle`（9.9.0 发行版） |
| Gradle 缓存 | `$HOME/toolchain/gradle-home`（`GRADLE_USER_HOME`） |
| Maven 镜像 | `$HOME/toolchain/m2` |
| 运行时数据 | `$HOME/.local/share/opencode`（数据库、日志、shell 记录） |
| 默认配置 | `$HOME/.config/opencode` |
| 原生配置 | `$HOME/.config/opencode-android`（技能也会复制到这里） |
| 临时目录 | proot 内的 `/tmp`，映射到 `$TMPDIR`（`cache/tmp`） |
| 共享存储 | 仅在手机已 root 且 bind mount 存在时才有 `$HOME/sdcard` |

`/` 和 `/tmp/opencode` 在 Androc 的文件浏览器中**不可用**：应用无法读取
Android 根目录，而 `/tmp/opencode` 并不是真实目录。

规则：

- 始终使用 `$HOME`、`$PREFIX`、`$TMPDIR`；绝不要在脚本里硬编码
  `/data/data/com.a2heng.androc/...` 或 `/data/data/com.termux/...`。
- 用 `#!/data/data/com.termux/files/usr/bin/bash` 的脚本能工作，因为该路径在
  沙箱内存在。当 `bash` 在 `PATH` 上时，`#!/usr/bin/env bash` 也能工作。
- 除非用户配置了存储，否则不要写入 `/sdcard`；它默认没有挂载。

## 软件包

APK 已经包含常用软件包（见下面的列表）。用 Termux 包管理器安装更多：

```sh
pkg update
pkg install <name>
# or
apt-get update && apt-get install -y <name>
```

说明：

- `pkg` 是 Androc 提供的薄壳；它带着正确的 `PREFIX` 和非交互标志转发给 `apt`。
- 第一次在线安装需要网络。镜像已经配置好；除非某个镜像确实宕机，否则不要
  改写 `sources.list`。
- 安装的文件位于 `$PREFIX` 下，并能挺过应用更新（因为它们在应用私有 home 里）。
- 在猜包名之前，先用 `pkg search <name>` / `apt-cache search <name>`。

内置的亮点包：`bash`、`coreutils`、`findutils`、`grep`、`sed`、`gawk`、
`diffutils`、`tar`、`gzip`、`bzip2`、`xz-utils`、`zstd`、`curl`、`wget`、
`git`、`openssh`、`python`、`python-pip`、`nodejs`、`clang`、`lld`、`llvm`、
`cmake`、`ninja`、`make`、`pkg-config`、`binutils`、`gdb`、`procps`、`psmisc`、
`util-linux`、`termux-tools`、`termux-am`、`pulseaudio`、`openjdk-21`、
`android-tools`（adb）、`aidl`。

## Python

```sh
python --version
python -m venv .venv
. .venv/bin/activate
pip install <pkg>
```

- `pip` 使用已配置的索引；如果它很慢，改用项目的 `android-lib-cache`/镜像约定，
  而不是随便添加索引。
- 对于原生 wheel，优先用 `manylinux aarch64`；从源码构建需要
  `clang`/`cmake`/`ninja`，在手机上可能很慢。
- 把虚拟环境放在项目内（`./.venv`），不要放在 `$HOME` 根目录。

## Node

```sh
node --version
npm --version
npm install
```

- `nodejs` 自带 npm。使用项目本地的 `node_modules`；除非任务需要一个 CLI，
  否则不要安装全局包。
- 如果 `npm` 不见了，重新 `pkg install nodejs`，或使用 `corepack`。

## C/C++ 与 NDK

```sh
clang --version
cmake --version
ninja --version
```

- NDK sysroot 和 Android 平台库位于内置工具链下；请使用项目自带的
  Gradle/CMake 配置，而不是手写交叉编译标志。
- 为兼容 16 KB 页大小，编译时加 `-Wl,-z,max-page-size=16384`（NDK r28+ 还支持
  `-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON`）。参见 `android-16kb` 技能：
  通常的元凶是预制的 `.so` 文件，而不是 Gradle 开关。

## Git 与 SSH

```sh
git status
git clone <url>
ssh-keygen -t ed25519
```

- Git 在沙箱内工作；HTTPS 使用内置的 CA 文件。如果需要公司代理，为那条命令
  导出 `https_proxy`/`http_proxy`。
- `ssh`/`sftp-server` 可用。密钥位于 `$HOME/.ssh`，并能挺过应用更新。
- 不要运行需要 GUI 的 `git` 辅助程序；只用 CLI。

## Android 集成

```sh
adb devices                 # adb is preinstalled (Termux android-tools)
adb shell am start -n ...
am start -n ...             # termux-am / Android am
termux-am start ...
```

- 做 UI 自动化时，优先用 `adb shell input`、`uiautomator dump`、`screencap`
  （系统二进制），而不是 Termux 的 GUI 包。
- `am`/`pm`/`dumpsys` 是 Android 二进制；Androc 在 `$PREFIX/bin` 里包装了它们，
  让它们在 proot 内工作且不继承 Termux 的库。
- 如果手机已 root，`su -c '<cmd>'` 可用，且 `$HOME/sdcard` 可能是共享存储的
  bind mount。

## 常见陷阱

- **`CANNOT LINK EXECUTABLE … library "libX.so" not found`** —— prefix 缺少
  某个库（经典的是 `libreadline.so.8`）。先运行 `oc-doctor`，再运行 `oc-repair`。
  Androc 里的一切都已经在 proot 内；不要绕过它。
- **`Permission denied` / `inaccessible or not found` / `exec format error`** ——
  某个 ELF 或脚本被 Android 进程直接从应用私有存储执行，绕过了 Androc。改用
  Androc 的终端/代理；不要 `chmod +x` 并从 Java `ProcessBuilder` 里执行它。
- **内置工具报 `command not found`** —— 检查 `echo $PATH`；prefix 必须在最前面。
  一切都在 proot 内运行，所以不需要额外包装。
- **`/tmp` 不是 Android 的 `/tmp`** —— 它绑定到应用缓存。里面的文件随时会被
  清掉；不要把结果放在那里。
- **长时间运行的任务** —— 用 `setsid`/`nohup` 放到后台，并把日志写到 `$HOME`
  下（如果需要保留，就不要放 `/tmp`）。服务器重启时应用可能杀掉沙箱。
- **存储权限** —— Androc 不申请 `MANAGE_EXTERNAL_STORAGE`。要读取共享存储，
  使用应用的文件选择器/分享流程，或 root 后的 bind mount；不要假设 `/sdcard`
  可写。
- **假定存在 Termux 应用的包脚本** —— `termux-setup-storage`、
  `termux-reload-settings`、`termux-services` 以垫片形式存在，但有些需要真正的
  Termux 应用。优先使用普通文件和 `nohup`。

## 常用配方

```sh
# Check the environment
echo "$HOME"; echo "$PREFIX"; command -v bash git python node clang

# Install a missing CLI
pkg install -y jq

# Python one-off
python - <<'PY'
print("hello from the phone")
PY

# Build a native project (CMake)
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"

# Keep a job alive and log it
setsid nohup ./job.sh >"$HOME/job.log" 2>&1 &
tail -f "$HOME/job.log"
```
