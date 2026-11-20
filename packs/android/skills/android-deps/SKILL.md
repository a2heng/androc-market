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

构建默认联网解析依赖，结果缓存在 `$HOME/.gradle`（所有项目共享）。
要让构建只读缓存：

```sh
OC_BUILD_ONLINE=0 bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug
```

依赖缺失时先联网跑一次；移动网络下先征得用户同意。

若需要可复用的下载（所有项目和其他工具共用一份副本），
改用 `android-lib-cache` 技能：

```sh
bash ~/.config/opencode/skills/android-lib-cache/scripts/warm-gradle.sh . assembleDebug
bash ~/.config/opencode/skills/android-lib-cache/scripts/export-gradle.sh
```

多项目共用 `$HOME/.gradle`，不需要复制缓存。

## 诊断解析失败

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug \
  :app:dependencies --configuration debugRuntimeClasspath
```

或者：

```sh
# inside proot, with the same env as build.sh
"$JAVA_HOME/bin/java" -classpath /opt/gradle/gradle-9.9.0/lib/gradle-gradle-cli-main-9.9.0.jar \
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
- 依赖下载写入共享的 `$HOME/.gradle`；
  `android-lib-cache` 技能可以另外维护 `$HOME/.androc/m2`，
  供 Maven、sbt、javac 和脚本使用。
- 保留 `$HOME/.gradle`；清理时只删项目里的 `build/` 和 `.gradle/`；
  它们包含离线缓存。只删除损坏的版本目录。
- 缓存只在本机使用，不进仓库。
