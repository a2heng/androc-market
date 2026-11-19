# 仓库与缓存行为

## 顺序

`resolve_maven.py` 按以下顺序尝试仓库：

1. `ANDROC_MAVEN_REPOS`（逗号分隔，可选）
2. Google Maven — `https://dl.google.com/dl/android/maven2`
   （AndroidX、Material、AGP、Google Play 相关库）
3. Maven Central — `https://repo1.maven.org/maven2`
   （Kotlin、OkHttp、Retrofit、Gson、JUnit 以及大多数 JVM 库）

对 `androidx.*`、`com.android.*`、`com.google.android.*` 而言，Google 优先很重要。
Central 通常没有 AndroidX 构建产物。

无需改代码即可添加镜像：

```sh
export ANDROC_MAVEN_REPOS="https://maven.aliyun.com/repository/public"
bash scripts/fetch-maven.sh com.squareup.okhttp3:okhttp:4.12.0
```

## 校验

每个下载的 POM/JAR/AAR 都会连其 SHA-256 一起记录在
`$ANDROC_M2/.androc-index.tsv` 中。当仓库发布 `<file>.sha1` 时，脚本会比对
它并在不匹配时告警。已存在的文件不会重复下载；仅在某个版本目录损坏时
删除它。

## 传递依赖

Android 项目应使用 `warm-gradle.sh`：Gradle 能正确解析版本、BOM、变体属性
和 AAR 元数据，然后把所有内容存进 `~/toolchain/gradle-home`。
`export-gradle.sh` 再把这些文件发布到 Maven 镜像。

`resolve_maven.py` 也会遍历 POM 中的 `compile`/`runtime` 依赖，但它不会导入
BOM（`scope=import`）或 Gradle 模块元数据。对使用 BOM 的项目，用 Gradle
预热，不要手工抓取。

## 不要缓存什么

- 不要把凭据、`settings.xml` 或 `.netrc` 缓存进镜像。
- 不要提交镜像；它是 `HOME` 下的运行时状态。
- 不要把项目本地 `.gradle` 缓存与共享缓存混用。
