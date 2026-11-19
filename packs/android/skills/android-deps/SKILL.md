---
name: Android Dependencies
description: 管理本机构建的 Gradle/Maven 依赖，包括离线缓存行为、版本冲突、仓库与依赖分析。构建无法解析某个库时使用。
---

# Android 依赖

## 仓库

`settings.gradle`：

```groovy
dependencyResolutionManagement {
    repositories { google(); mavenCentral() }
}
```

开发期间把 `repositoriesMode` 保持为宽松模式；
`FAIL_ON_PROJECT_REPOS` 会拒绝模块构建文件中声明的仓库。

## 默认离线

`android-build` 技能以 `--offline` 运行 Gradle，并使用随包提供的
`$HOME/toolchain/gradle-home/caches/modules-2`。如果有依赖缺失：

```sh
OC_BUILD_ONLINE=1 bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug
```

仅在得到用户许可后才这样做。手机可能处于计费流量网络。

若需要可复用的下载（所有项目和其他工具共用一份副本），
改用 `android-lib-cache` 技能：

```sh
bash ~/.config/opencode/skills/android-lib-cache/scripts/warm-gradle.sh . assembleDebug
bash ~/.config/opencode/skills/android-lib-cache/scripts/export-gradle.sh
```

它会写入 `$HOME/toolchain/gradle-home`，并在 `$HOME/toolchain/m2`
发布一份 Maven 目录结构的镜像。绝不要预热项目本地的 `~/.gradle` 或
`./.gradle`：下一个项目会把所有内容重新下载一遍。

## 诊断解析失败

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug \
  :app:dependencies --configuration debugRuntimeClasspath
```

或者：

```sh
# inside proot, with the same env as build.sh
"$JAVA_HOME/bin/java" -classpath "$HOME/toolchain/gradle/gradle-9.9.0/lib/gradle-gradle-cli-main-9.9.0.jar" \
  org.gradle.launcher.GradleMain --offline :app:dependencyInsight \
  --dependency androidx.core --configuration debugRuntimeClasspath
```

## 版本冲突

- 优先使用显式版本，而不是 `+` 或 `latest.release`。
- 多模块项目使用版本目录（`gradle/libs.versions.toml`）。
- 仅在必要时强制版本：

```groovy
configurations.all {
    resolutionStrategy.force 'androidx.core:core:1.13.1'
}
```

## 缓存说明

- 随包缓存以本应用自身构建（AGP 9.5.1、appcompat、
  material、AndroidX core）作为种子数据。它**不是**通用 Maven 镜像。
- Compose、Hilt、Room、Retrofit、Kotlin 插件和测试库可能
  缺失。在承诺可离线构建之前先确认。
- 运行时下载写入共享的 `$HOME/toolchain/gradle-home`；
  `android-lib-cache` 技能还会提供 `$HOME/toolchain/m2`，
  供 Maven、sbt、javac 和脚本使用。
- 不要删除 `$HOME/toolchain/gradle-home` 或 `$HOME/toolchain/m2`；
  它们包含离线缓存。只删除损坏的版本目录。
- 绝不要提交缓存；种子由 `scripts/make-toolchain.py` 生成。
