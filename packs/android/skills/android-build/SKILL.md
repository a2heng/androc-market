---
name: Android Build
description: 在这台手机上用 Gradle、JDK 21 和端侧 Android SDK 本地构建、签名并定位 Android APK。适用于用户要求在设备上编译、重新构建、打包或安装 Android 项目时。
---

# Android Build（设备上）

这台手机就是构建机：JDK、SDK、Gradle、aapt2 全在 android 包里，构建在本地完成。

## 一次构建

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh <项目目录> debug
```

脚本会设置 `JAVA_HOME`、`ANDROID_HOME`、`PATH`、`LD_PRELOAD`，强制
`buildToolsVersion 36.0.0` 和包内 `aapt2`，然后用包内 Gradle 直接启动
GradleMain；项目不需要 `gradlew`。

产物：`<项目>/app/build/outputs/apk/debug/app-debug.apk`。

## 环境

| 项 | 路径 |
|---|---|
| JDK 21 | `/usr/lib/jvm/java-21-openjdk` |
| SDK | `/opt/android-sdk`（platform 36、build-tools 36.0.0） |
| Gradle 9.9.0 | `/opt/gradle/gradle-9.9.0` |
| 环境脚本 | `/opt/androc/env.sh`（`PATH`、`JAVA_HOME`、`LD_PRELOAD=fixexec.so`） |
| Gradle 缓存 | `$HOME/.gradle`，所有项目共享 |

AGP 9 从 Maven 取自己的 x86_64 aapt2；脚本已用
`-Pandroid.aapt2FromMavenOverride` 指向包内静态 aarch64 `aapt2`。

## 依赖缓存

首次构建联网解析依赖，之后走缓存。要离线构建：

```sh
OC_BUILD_ONLINE=0 bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug
```

缓存目录较大时：

```sh
bash <skill-dir>/scripts/clean-caches.sh            # 临时文件
bash <skill-dir>/scripts/clean-caches.sh --builds   # 再清项目 build/.gradle
bash <skill-dir>/scripts/clean-caches.sh --all      # 再清依赖缓存
```

## 16 KB 对齐

构建脚本会调用 `check-16kb.py` 审核产物。native `.so` 的对齐由依赖本身决定；
最终 APK 用 `zipalign -P 16` 对齐。严格模式：`ANDROC_16KB_STRICT=1`。

## 常见错误

| 现象 | 处理 |
|---|---|
| `Failed to find target android-36` | 确认 `/opt/android-sdk/platforms/android-36` 下有 `android.jar`、`source.properties`、`build.prop`、`core-for-system-modules.jar` |
| `Failed to find Build Tools revision 36.0.0` | 确认 build-tools 目录里有 `source.properties` |
| `Installed Build Tools ... corrupted` | 确认 `core-lambda-stubs.jar` 存在 |
| `Failed to mark memory page as executable` | 确认 `LD_PRELOAD=/usr/local/lib/fixexec.so`（`env.sh` 已导出） |
| `SDK location not found` | 脚本会写 `local.properties`；删掉项目里旧的 `sdk.dir` |
| `AAPT2 Daemon startup failed` | 用脚本的 `-Pandroid.aapt2FromMavenOverride`，不要手拼 Gradle 命令 |
| Gradle 被系统杀掉 | 降低 `-Xmx`、关掉其它重负载应用后重试 |
