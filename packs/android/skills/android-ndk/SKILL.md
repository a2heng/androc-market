---
name: Android NDK
description: 在 Android 项目中添加或调试原生 C/C++ 代码（CMake/NDK）、ABI 过滤与 16 KB 页对齐。仅在项目确实需要原生代码时使用。
---

# Android NDK

## 检查已安装内容

离线包**不**包含完整的 NDK。检查：

```sh
ls "$HOME/toolchain/android-sdk/ndk" 2>/dev/null || echo "no NDK"
```

如果项目需要原生代码，必须单独安装 NDK/CMake（例如使用 Termux Studio 的
`studio ndk install`，或一个按 16 KB 对齐的 NDK 包）。NDK 不存在时不要
声称支持 NDK。

## Gradle 配置

```groovy
android {
    ndkVersion "27.2.12479018"
    defaultConfig {
        ndk { abiFilters 'arm64-v8a' }
    }
    externalNativeBuild {
        cmake { path file('src/main/cpp/CMakeLists.txt') }
    }
}
```

`CMakeLists.txt`：

```cmake
cmake_minimum_required(VERSION 3.22)
project(native-lib C)
add_library(native-lib SHARED native-lib.c)
target_link_libraries(native-lib log)
```

## 16 KB 页大小

Android 15+ 设备可能使用 16 KB 页。这样构建原生库：

```cmake
target_link_options(native-lib PRIVATE "-Wl,-z,max-page-size=16384")
```

或写在 `build.gradle` 中：

```groovy
android { defaultConfig { externalNativeBuild { cmake { arguments "-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON" } } } }
```

用 `scripts/check-elf-align.py` 验证；所有 `PT_LOAD` 段都必须按
`0x4000` 对齐。

## 调试原生崩溃

- `logcat` 会显示 `DEBUG`、`libc`、`signal 11 (SIGSEGV)`、`backtrace`。
- `adb shell debuggerd -b <pid>` 在 adb/无线调试下可能可用。
- 保持 `libc++_shared.so` 的打包方式一致；不要混用不同 STL 变体。
- 只用 `arm64-v8a`；应用和工具链都是 arm64。

## 规则

- 原生代码是最后手段；优先用 Java/Kotlin。
- 不要为你无法测试的 ABI 启用 `abiFilters`。
- 每次改原生代码后都要重建并重装；Gradle 缓存可能藏住过期的
  `.so` 文件。
