---
name: Android Gradle
description: 在手机上修复 Android Gradle 构建：AGP/Gradle 兼容性、SDK/build-tools、内存、守护进程、离线模式和常见报错。适用于配置或插件解析失败时。
---

# Android Gradle

## 内置版本

| 组件 | 版本 |
|---|---|
| Gradle | 9.9.0 |
| AGP | 9.5.1（本应用）；项目可用 8.13 或 9.x |
| compileSdk | 35 |
| build-tools | 36.0.0（35.0.2 的二进制改名） |
| JDK | 21（Termux） |
| Java 源码/目标版本 | 17 |

构建技能直接启动 `GradleMain`，因为 `bin/gradle` 在 Android mksh 下会失败
（`Could not find or load main class "-Xmx64m"`）。

## 兼容性

- AGP 9.5.x 需要 Gradle 9.x 和 JDK 17+；本内置包使用 Gradle 9.9.0 可正常构建。
- AGP 9.x 可能需要 Gradle 9.x 和更新的 build-tools；不要假定它一定可用。
- 如果项目通过 wrapper 固定了较旧的 Gradle，设置
  `OC_USE_WRAPPER=1` 并确保对应发行版可用，或把项目升级到 AGP 9.5.1。

## 内存

```properties
org.gradle.jvmargs=-Xmx3g -XX:MaxMetaspaceSize=1g -Dfile.encoding=UTF-8
org.gradle.daemon=false
org.gradle.offline=true
```

如果手机内存不超过 6 GB，用 `-Xmx2g`。Gradle 守护进程被杀掉，常常
表现为一次莫名其妙的构建失败。

## 常见错误

| 错误 | 修复 |
|---|---|
| `Failed to find Build Tools revision 34.0.0` | init 脚本强制 36.0.0；在模块里加 `buildToolsVersion '36.0.0'` |
| `core-lambda-stubs.jar` missing | 用工具链 v5+；该 jar 已内置 |
| `aapt2` format/exec error | 用 16 KB 的 aarch64 aapt2；检查 ABI |
| `java.io.tmpdir ... doesn't exist` | 让 `build.sh` 用 `$HOME/.cache/tmp`；不要手工创建 `$PREFIX/tmp` |
| `Could not resolve ...` | 依赖不在离线缓存；用 `android-lib-cache`，不要直接联网跑 |
| `checkDebugAarMetadata` / AndroidX warning | 在 `gradle.properties` 加 `android.useAndroidX=true` |
| duplicate `kotlin-stdlib` classes | 强制统一 stdlib 版本（1.8+ 已合并 jdk7/jdk8） |
| `Unsupported class file major version` | JDK 与 AGP/Kotlin 版本不匹配（太新或太旧） |
| `SDK location not found` | 缺 `local.properties` 或 `ANDROID_HOME` |

## 调试构建

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug
```

需要更多细节时，用 `--stacktrace --info` 运行同样的 Gradle 命令（改一份
build.sh 副本，或直接调用 GradleMain）。看**第一个**错误，而不是最后那句
"BUILD FAILED"。

## 规则

- 不要修改内置的 Gradle 发行版。
- 不要提交 `local.properties`、`.gradle/` 或 `build/`。
- 保持 `android.aapt2FromMavenOverride` 指向内置的 aapt2。
