---
name: Android Install
description: 用内置 adb、PackageInstaller 或 Shizuku 在这台手机上安装、启动、卸载 Android 应用或授予权限。构建完成后，或用户要求运行 APK 时使用。
---

# Android 安装

## 用 adb 安装

```sh
adb install -r -t /path/to/app-debug.apk
```

两个 adb 二进制（Termux 的 `$PREFIX/bin/adb` 和
`$HOME/toolchain/platform-tools/adb`）都能正常工作：`auto` 会在 proot 内运行
整条命令。不需要 `oc-proot` 包装。

`-r` 替换已安装的版本；`-t` 允许仅测试用的 APK。遇到签名不匹配时：先卸载，
再安装：

```sh
adb uninstall com.example.app
adb install /path/to/app.apk
```

## 启动

```sh
adb shell monkey -p com.example.app -c android.intent.category.LAUNCHER 1
# or, if the activity is known:
adb shell am start -n com.example.app/.MainActivity
```

获取可启动的 activity：

```sh
adb shell cmd package resolve-activity --brief com.example.app | tail -n 1
```

## 权限

```sh
adb shell pm grant com.example.app android.permission.POST_NOTIFICATIONS
adb shell appops set com.example.app MANAGE_EXTERNAL_STORAGE allow
```

在某些厂商 ROM（OPPO/ColorOS、Xiaomi/HyperOS）上，以 shell 用户执行
`pm grant`/`appops` 会受到限制。不要把失败当成应用 bug；引导用户在设置中
手动授予。

## Shizuku / PackageInstaller

如果 adb 不可用，应用可以使用 Android 的 PackageInstaller intent 或
Shizuku（如果已安装）。它们通常会弹出确认对话框；需要用户点击安装。

## 验证

```sh
adb shell dumpsys package com.example.app | grep -E "versionName|versionCode|firstInstallTime"
adb shell pidof com.example.app
```

## 注意

- APK 必须已签名（debug 签名即可）。
- 不要覆盖安装签名不同的应用；先卸载。
- 在同一台手机上，adb 需要无线调试配对；参见 `android-debug`。
