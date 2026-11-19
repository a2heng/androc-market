---
name: Android Test
description: 编写并运行 Android 单元测试与真机仪器化/UI 测试。适用于用户要求测试、覆盖率，或在手机上验证某个界面/流程时。
---

# Android Test

## 单元测试（JVM，无需设备）

测试放在 `app/src/test/java/...`，运行：

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug testDebugUnitTest
```

JUnit 4 通常已可直接解析；如果不行，添加：

```groovy
testImplementation 'junit:junit:4.13.2'
```

逻辑、解析以及不依赖 Android 的 ViewModel，优先改用纯 JVM 测试。

## 仪器化测试（真机）

测试放在 `app/src/androidTest/java/...`，运行：

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh . debug connectedDebugAndroidTest
```

这需要已连接的 adb 设备。在这台手机上，用 `android-debug`
技能配对无线调试，并把 `adb` 连到 `127.0.0.1`。

依赖：

```groovy
androidTestImplementation 'androidx.test.ext:junit:1.2.1'
androidTestImplementation 'androidx.test.espresso:espresso-core:3.6.1'
```

这些构件可能不在离线缓存里；承诺能跑测试之前，先用一次构建确认。

## 不写测试也能做的 UI 检查

- 启动：`adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1`
- 截图：`adb exec-out screencap -p > /tmp/screen.png`
- 崩溃/ANR：`android-debug/scripts/crash.sh <pkg>`
- UI 层级：`adb shell uiautomator dump /sdcard/window.xml`，然后把它拉出来

## 规则

- 没有 Gradle 任务输出和测试报告，就不要声称测试通过。
- 报告：`app/build/reports/tests/testDebugUnitTest/index.html` 和
  `app/build/reports/androidTests/connected/`。
- 仪器化测试保持精简；手机比桌面慢。
