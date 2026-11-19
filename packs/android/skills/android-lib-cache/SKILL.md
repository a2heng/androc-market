---
name: Android Library Cache
description: 解析、下载并缓存不在随包离线缓存中的 Maven/Gradle 库，放到本机其他项目和工具都能复用的共享缓存里。当构建提示 "Could not resolve"、"No cached version"，或某个库离线缺失时使用。
---

# Android 库缓存

APK 内置了一份**预置（seeded）**的 Gradle/Maven 缓存。它不是通用镜像：
Compose、Hilt、Room、Retrofit、Kotlin 插件和测试库可能不在其中。本技能
把缺失的库**一次性**下载到共享位置，使此后手机上的每个项目和工具都能离线工作。

## 共享位置（不要使用项目本地缓存）

| 路径 | 是什么 | 谁复用它 |
|---|---|---|
| `~/toolchain/gradle-home` | 带 `caches/modules-2` 的 `GRADLE_USER_HOME` | 每个 Gradle 项目 |
| `~/toolchain/m2` | Maven 仓库目录结构（`group/artifact/version`） | Maven、sbt、javac、kotlinc、脚本、Gradle |
| `~/toolchain/m2/.androc-index.tsv` | 坐标、文件、sha256 | 审计 / 去重 |
| `~/.m2/repository` | 指向 `~/toolchain/m2` 的符号链接 | 硬编码 `~/.m2` 的工具 |

`HOME` 是应用私有根目录（`/data/user/0/com.a2heng.androc/files/home`），
因此这些缓存能在应用更新后保留，并被所有项目共享。

哪些是自动的、哪些需要显式启用：

- `~/toolchain/gradle-home` 由 `android-build/scripts/build.sh`
  （`GRADLE_USER_HOME`）自动使用；它是 Gradle 下载的真实共享缓存。
- `~/toolchain/m2` 只在你运行 `export-gradle.sh` 或 `fetch-maven.sh` 时
  才会填充；`~/.m2/repository` 只在运行 `link-m2.sh` 后才存在。它们
  面向 Maven/sbt/javac，Gradle 并不需要。
- 项目的 `build/` 和 `.gradle/` **不是**缓存；它们才是体积增长的主要来源。
  用 `android-build/scripts/clean-caches.sh --builds` 删除它们。

规则：绝不要下载到 `./.gradle`、`./build` 或每个项目各自的
`mavenLocal()`。始终使用上面的共享路径，否则下一个项目会把同样的 40 MB
再下载一遍。

## 工作流程

### 1. 确认缺什么

```sh
bash <skill-dir>/scripts/env.sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug
```

读取第一行 `Could not resolve <group:artifact:version>`。

### 2. 预热共享 Gradle 缓存（对 Android 项目最佳）

```sh
bash <skill-dir>/scripts/warm-gradle.sh /path/to/project assembleDebug
```

它会以 `GRADLE_USER_HOME=~/toolchain/gradle-home` **在线运行一次**常规的
`android-build` 脚本，然后立即**离线**重建，以证明缓存完整。传递依赖由
Gradle 解析，比手工抓取 POM 更可靠。

使用移动数据前先询问用户。此后，使用相同坐标的每个 Gradle 项目都能离线构建。

### 3. 把 Gradle 缓存发布到 Maven 镜像（供非 Gradle 工具使用）

```sh
bash <skill-dir>/scripts/export-gradle.sh
```

它把 `modules-2` 中的 jar/aar/pom 复制到 `~/toolchain/m2`，好让 Maven、sbt、
`javac -cp`、Kotlin 脚本及其他软件也能使用同一批文件。

### 4. 为其他工具抓取单个坐标

```sh
bash <skill-dir>/scripts/fetch-maven.sh com.squareup.okhttp3:okhttp:4.12.0
bash <skill-dir>/scripts/fetch-maven.sh androidx.room:room-runtime:2.6.1 --no-deps
```

该脚本会依次尝试 Google Maven 和 Maven Central，把 POM/JAR/AAR 按 Maven
目录结构存放，在仓库发布 SHA-1 时校验它，并追加记录到
`.androc-index.tsv`。单个文件用 `--no-deps`；传递依赖解析最好交给 Gradle
（第 2 步）。

### 5. 使用镜像

Gradle——把下面一行加入构建脚本（或作为 init 脚本传入）：

```groovy
maven { url = uri("${System.getenv('HOME')}/toolchain/m2") }
```

Maven / sbt / 脚本：

```sh
export MAVEN_OPTS="-Dmaven.repo.local=$HOME/toolchain/m2"
mvn -o ...
```

为只认 `~/.m2` 的工具做一次性符号链接：

```sh
bash <skill-dir>/scripts/link-m2.sh
```

用 `javac` 做无依赖检查：

```sh
javac -cp "$HOME/toolchain/m2/com/squareup/okhttp3/okhttp/4.12.0/okhttp-4.12.0.jar" App.java
```

## 环境

`scripts/env.sh` 导出规范取值；在临时 shell 中 source 它：

```sh
. <skill-dir>/scripts/env.sh
echo "$ANDROC_M2 $GRADLE_USER_HOME"
```

变量：

- `ANDROC_M2` — Maven 镜像（默认 `$HOME/toolchain/m2`）
- `ANDROC_GRADLE_HOME` — 共享 Gradle 主目录（默认 `$HOME/toolchain/gradle-home`）
- `ANDROC_MAVEN_REPOS` — 以逗号分隔的额外仓库基础 URL

## 规则

- 每个坐标只保留一份副本。如果文件已存在且校验和匹配，就不再下载。
- 缓存放在项目之外。`scripts/make-toolchain.py` 负责随包种子；用户缓存
  是运行时新增的一切。
- 不要为了“清理”构建而删除 `~/toolchain/gradle-home` 或 `~/toolchain/m2`。
  只在某个版本目录损坏时删除它。
- 绝不要把 `~/toolchain`、`~/toolchain/m2` 或 `.aar` 提交到 git。
- 优先使用显式版本。`+` 和 `latest.release` 会让缓存变得不确定，
  并在之后破坏离线构建。
- 在计费流量网络上，先询问，再一次性批量下载。

## 故障排查

| 症状 | 修复 |
|---|---|
| `No cached version of ... available for offline mode` | 带上 `OC_BUILD_ONLINE=1` 执行第 2 步 |
| 由 BOM 管理的版本出现 `Could not resolve` | 用 Gradle 预热；不要手工抓取 BOM |
| `Failed to find target with hash string android-36` | 安装 platform 36，见 `android-build` |
| 添加镜像后出现 `Duplicate class` | 删除旧的项目本地缓存并重建 |
| Maven 忽略镜像 | 传入 `-Dmaven.repo.local=$HOME/toolchain/m2` |
| Gradle 仍使用 `~/.gradle` | `export GRADLE_USER_HOME=$HOME/toolchain/gradle-home` |

## 参考

- `references/repositories.md` — 仓库顺序、Google 与 Central、SHA-1。
- `android-build` — 离线构建入口。
- `android-deps` — 版本冲突与依赖分析。
