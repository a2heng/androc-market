---
name: Android Project
description: 在这台手机上创建或修复 Android Gradle 项目：模块、AGP/Gradle 版本、manifest、包名和首次构建。适用于新建应用或项目结构损坏时。
---

# Android Project

## 本机默认配置

- AGP **9.5.1**、Gradle **9.9.0**（内置）
- `compileSdk 36`, `buildToolsVersion "36.0.0"`
- `minSdk 24`, `targetSdk 34`
- Java 17
- 仅 arm64

构建技能会通过 init 脚本强制 `buildToolsVersion 36.0.0`，但把它写进
`app/build.gradle` 能让项目更可移植。

## 项目放在哪里

项目建在 `~/workspace/<Name>` 下，不要直接放在 `~`，也不要放在 Android
文件系统根目录。`~/workspace` 是应用管理的项目根目录；项目选择器的 `~` 和
`/` 按钮都解析到这里。

```sh
mkdir -p "$HOME/workspace/MyApp"
```

## 最小结构

```text
~/workspace/MyApp/
├─ settings.gradle
├─ build.gradle
├─ gradlew                  # empty placeholder is enough for the build skill
└─ app/
   ├─ build.gradle
   └─ src/main/
      ├─ AndroidManifest.xml
      ├─ java/com/example/myapp/MainActivity.java
      └─ res/values/styles.xml
```

`settings.gradle`：

```groovy
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories { google(); mavenCentral() }
}
rootProject.name = "MyApp"
include ":app"
```

根 `build.gradle`：

```groovy
plugins { id 'com.android.application' version '9.5.1' apply false }
```

`gradle.properties`（任何 AndroidX 依赖都需要）：

```properties
android.useAndroidX=true
android.enableJetifier=true
org.gradle.jvmargs=-Xmx3g -XX:MaxMetaspaceSize=1g -Dfile.encoding=UTF-8
org.gradle.daemon=false
```

`app/build.gradle`：

```groovy
plugins { id 'com.android.application' }
android {
    namespace 'com.example.myapp'
    compileSdk 36
    buildToolsVersion '36.0.0'
    defaultConfig {
        applicationId 'com.example.myapp'
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName '1.0'
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}
```

## 工作流

1. 创建上面的目录和文件。
2. 用 `android-build` 技能构建：
   `bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug`
3. 如果 Gradle 需要的依赖不在缓存里，用 `android-lib-cache`（`warm-gradle.sh`），
   让下载结果可以被所有项目复用。使用移动数据前先询问用户。
4. 用 `android-install` 或 `android-debug` 技能安装。

## 规则

- 不要在 `/sdcard`（`noexec`）上直接运行 `./gradlew`；构建技能用的是
  `sh` 和内置的 Gradle 启动器。
- 使用唯一的 `applicationId`；正经项目不要复用 `com.example.hello`。
- 除非离线缓存里已有，否则不要添加 Compose 依赖；见 `android-deps`。
- 添加 `.gitignore`，包含 `.gradle/`、`build/`、`local.properties`、`*.apk`。
