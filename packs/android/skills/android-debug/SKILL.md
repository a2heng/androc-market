---
name: Android Debug
description: 在这台手机上用 logcat、崩溃/ANR 分析、安装并启动，以及构建失败分诊来调试 Android 应用。适用于在设备上构建的应用崩溃、黑屏、ANR，或用户要求调试时。
---

# Android Debug（设备上）

一切都在手机上运行。直接正常跑 `adb` 即可：`auto` 会把整条命令
放进 proot 执行，adb 二进制和它依赖的库在那里都可用。
不需要额外包一层，也不需要给命令分类。

优先用 16 KB 的 Termux `adb`（`$PREFIX/bin/adb`）；它是匹配的
aarch64 构建。`$HOME/toolchain/platform-tools/adb` 是备选。

## 适用场景

- 应用能安装但一启动就崩溃或黑屏
- ANR / 界面卡死
- 构建成功但应用跑不起来
- 需要某个包的 logcat
- 需要安装并启动刚构建好的 APK

## 1. 让 adb 连到本机

最干净的方式是 Android 的**无线调试**：

1. 开发者选项 → 无线调试 → 打开。
2. 点“使用配对码配对设备”。
3. 在手机上（在一个 shell 里）：

```sh
adb pair 127.0.0.1:<pair-port> <6-digit-code>
adb connect 127.0.0.1:<connect-port>
adb devices
```

变量和复合命令也可以；`auto` 会把整行发给 proot：

```sh
ADB="$HOME/toolchain/platform-tools/adb"; "$ADB" devices
```

不需要任何 wrapper；整个 shell 已经在 proot 里。

如果 `adb devices` 列出了设备，就继续。如果没有，请用户重做配对步骤；
不要猜端口。

## 2. 安装并启动

```sh
bash <skill-dir>/scripts/install-run.sh /path/to/app-debug.apk com.example.app
```

脚本会安装、清空 logcat、启动 launcher activity、等几秒，
然后打印过滤后的日志。

## 3. 抓崩溃

```sh
bash <skill-dir>/scripts/logcat.sh com.example.app 15
bash <skill-dir>/scripts/crash.sh com.example.app
```

重点关注：

- `FATAL EXCEPTION` / `AndroidRuntime`
- `Process: com.example.app`
- `Caused by:` —— 真正的根因通常是最后一个 `Caused by`
- `ANR in com.example.app`
- native 层：`DEBUG`、`libc`、`signal 11 (SIGSEGV)`、`tombstone`

## 4. 构建失败

运行构建脚本，看第一个错误，而不是最后一行：

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh <project> debug
```

本环境里的常见原因：

- `Failed to find Build Tools revision` → init 脚本强制 36.0.0；检查
  `$HOME/toolchain/android-sdk/build-tools/36.0.0/source.properties`
- `core-lambda-stubs.jar` missing → 工具链包不完整
- `aapt2` exec/format error → ABI 不对，或在 16 KB 设备上用了仅 4 KB 的 aapt2
- `java.io.tmpdir` missing → `$PREFIX/tmp` 没有被创建
- 依赖不在离线缓存 → 用 `OC_BUILD_ONLINE=1` 重试

## 5. 修复并验证

1. 读相关源码和完整堆栈。
2. 做最小改动。
3. 用 `android-build` 技能重新构建。
4. 重装，并重跑本技能的 logcat/crash 脚本。
5. 汇报根因、修复和所用命令；没有干净的 logcat/启动结果，
   就不要声称成功。

## 说明

- Android 10+ 限制应用读取其他应用的日志。通过无线调试使用内置 `adb`
  是受支持的路径；不要试图从应用沙箱里读
  `/dev/log/*`。
- logcat 抓取保持短小且带过滤；完整缓冲区非常大。
- 绝不要把日志里的 API key 或 token 贴出来。对 `sk-`、`ghp_`、`Bearer` 做脱敏。
