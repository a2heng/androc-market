---
name: Android Library Cache
description: 解析、下载并复用 Gradle/Maven 依赖；构建提示 "Could not resolve" 或离线缺少某个库时使用。
---

# Android 库缓存

## 共享位置

| 路径 | 是什么 | 谁用 |
|---|---|---|
| `$HOME/.gradle` | Gradle 依赖缓存（`caches/modules-2`） | 每个 Gradle 项目 |
| `$HOME/.androc/m2` | 可选 Maven 目录镜像 | Maven/sbt/javac 脚本 |
| `$HOME/.androc/m2/.androc-index.tsv` | 坐标、文件、sha256 | 审计 |

`HOME` 是应用私有目录（`files/home`），应用更新后缓存保留。

## 构建与依赖

`android-build/scripts/build.sh` 使用 `$HOME/.gradle`，首次联网解析、之后复用。
要离线构建：

```sh
OC_BUILD_ONLINE=0 bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug
```

缺少依赖时联网构建一次即可补齐。

## 单独预热

```sh
bash ~/.config/opencode/skills/android-lib-cache/scripts/warm-gradle.sh . assembleDebug
```

`warm-gradle.sh` 用共享的 `GRADLE_USER_HOME` 跑一次真实构建；之后所有项目复用。

## 清理

```sh
bash ~/.config/opencode/skills/android-build/scripts/clean-caches.sh --builds
```

只清项目里的 `build/` 和 `.gradle/`；依赖缓存用 `--all`。
