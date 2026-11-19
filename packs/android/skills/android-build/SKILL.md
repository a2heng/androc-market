---
name: Android Build
description: 在这台手机上用 Gradle、JDK 21 和端侧 Android SDK 本地构建、签名并定位 Android APK。适用于用户要求在设备上编译、重新构建、打包或安装 Android 项目时。
---

# Android Build（设备上）

这台手机就是构建机。下面的一切都在本地运行；不需要 PC，也不需要云。

**先看 16 KB：** 构建脚本会审核产出的 APK 并打印 16 KB 对齐报告。设置
`ANDROC_16KB_STRICT=1` 可让原生库仅有 4 KB 对齐时直接构建失败。**改 Gradle
开关或 `zipalign -P 16` 并不能解决这个问题**：对齐信息在每个预编译的 64 位
`.so` 内部。当检查报告 `libonnxruntime`、`libopencv_java4`、`libc++_shared`
等时，把依赖升级到提供 16 KB 对齐 Android 预编译库的版本（ONNX/OpenCV 的
例子见 `android-16kb`）。

## 适用场景

用户想要以下操作时使用本技能：

- 在本机构建 Gradle/AGP 项目的 APK
- 修改 Java/Kotlin/XML/资源后重新构建
- 产出 debug 或 release APK 并报告其路径

## 缓存清理

内置的 Gradle 缓存位于 `$HOME/toolchain/gradle-home`，由所有项目共享
（`GRADLE_USER_HOME`）；构建脚本会打印 `cache` 行，可据此确认没有在用
`~/.gradle`。真正的体积膨胀通常不是依赖，而是项目的 `build/` 和 `.gradle/`
目录。可用：

```sh
bash <skill-dir>/scripts/clean-caches.sh            # transient files only
bash <skill-dir>/scripts/clean-caches.sh --builds   # also workspace/*/build + .gradle
bash <skill-dir>/scripts/clean-caches.sh --all      # also shared dependency caches
```

Androc 启动时还会清理旧的临时文件、Gradle 守护进程日志和已下载的 `.deb`
文件。它从不会自动删除项目的 `build/` 目录。

## 前置条件

- arm64 Android 设备（工具链仅支持 arm64）
- 根目录带 `gradlew` wrapper 的 Gradle 项目
- 首次构建需要网络（Gradle 发行版 + Maven 依赖）
- 至少约 4 GB 可用存储和约 2 GB 可用内存

## 工作流

> 所有操作本来就跑在 proot 里。直接运行
> `bash <skill-dir>/scripts/build.sh /path debug` 即可。
> 脚本以 `#!/data/data/com.termux/files/usr/bin/bash` 开头；调用者的
> `$PWD` 是可靠的。不要再用 `oc-proot` 包一层。

### 1. 一次性工具链配置

每次安装应用后运行一次（幂等）：

```sh
bash <skill-dir>/scripts/setup-toolchain.sh
```

如果 APK 是用离线包构建的，这一步只会校验 JDK（从内置 Termux `.deb`
安装）和 `$HOME/toolchain` 下已解压的 SDK/Gradle 目录树。不使用网络。

不带内置包的源码构建时，脚本会退回到安装 `openjdk-21`，并下载 Android
platform 36 以及 arm64 `aapt2`（打包为 build-tools 36.0.0）。

### 2. 构建

```sh
bash <skill-dir>/scripts/build.sh /path/to/project debug
```

第二个参数是 `debug` 或 `release`（默认 `debug`）。脚本会：

- 设置 `JAVA_HOME`、`ANDROID_HOME`、`ANDROID_SDK_ROOT`、`PATH`
- 执行 `sh ./gradlew --no-daemon --console=plain assembleDebug`
- 传入 `-Pandroid.aapt2FromMavenOverride=<arm64 aapt2>`，避免 AGP 试图
  下载 x86_64 的 aapt2
- 以 `APK=/absolute/path.apk` 的形式打印产出的 APK 路径

绝不要直接执行 `./gradlew`：项目文件位于 `noexec` 挂载点。
`sh ./gradlew` 是读取脚本执行，可以正常工作。

### 3. 汇报

把 APK 路径和构建结果告诉用户。不要自己编路径：用脚本打印的
`APK=` 那一行。

## 不要绕过脚本

代理的 shell 本来就在 proot 内。`PREFIX` 是
`/data/data/com.termux/files/usr`；`$PWD` 是项目/会话目录。
绝不要手工导出 Termux 前缀，也绝不要从零重拼 Gradle 命令：那会导致
"tmpdir does not exist" 和 "`PREFIX/tmp` cannot be created" 这类失败。
脚本自己会解析一切。

如果脚本失败，就修**项目**再重跑。只有在万不得已时才用
`OC_USE_WRAPPER=1` 或裸 Gradle，并且保持
`GRADLE_USER_HOME=$HOME/toolchain/gradle-home` 和
`-Djava.io.tmpdir=$HOME/.cache/tmp`。

## 排查

| 错误 | 修复 |
|---|---|
| `checkDebugAarMetadata` / "AndroidX dependencies" | 在 `gradle.properties` 加 `android.useAndroidX=true`；只有旧 support 库才加 `android.enableJetifier=true` |
| duplicate `kotlin-stdlib` / `kotlin-stdlib-jdk7` classes | 在 `configurations.all { resolutionStrategy.force ... }` 里强制统一 stdlib 版本 |
| `java.io.tmpdir` / `PREFIX/tmp` missing | 不要手工创建；脚本用的是 `$HOME/.cache/tmp` |
| `Could not resolve` a library | 用 `android-lib-cache`；不要改成直接联网跑 Gradle |
| `SDK location not found` | 脚本会写 `local.properties`；不要指向 Termux 的真实前缀 |
| `aapt2` download / x86_64 error | 脚本会传入内置 arm64 aapt2 的覆盖路径 |

## 说明与限制

- 默认 SDK platform 是 36。`compileSdk 37` 的项目需安装 platform
  37 并使用匹配的 aapt2（见 `scripts/setup-toolchain.sh`）。
- 此版本不支持 NDK/CMake。
- 首次构建可能耗时 10 分钟以上并让手机发热；之后的构建是增量式的。
- 内置 Gradle 发行版/缓存存在时，构建默认走 `--offline`。如果项目
  需要内置缓存里没有的依赖，设置 `OC_BUILD_ONLINE=1`：
  `OC_BUILD_ONLINE=1 bash <skill-dir>/scripts/build.sh ...`
- 想用项目自己的 wrapper 而不是内置 Gradle：
  `OC_USE_WRAPPER=1 bash <skill-dir>/scripts/build.sh ...`
- 如果 Gradle 内存不足，把项目 `gradle.properties` 里的
  `org.gradle.jvmargs` 降到 `-Xmx2g` 或 `-Xmx3g`。
- 如果 AGP 报 SDK 相关错误，检查 `$ANDROID_HOME/platforms/android-36`
  里是否包含 `android.jar` 和 `source.properties`。
