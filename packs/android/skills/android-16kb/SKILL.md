---
name: Android 16 KB
description: 理解并修复 Android 16 KB 页大小的兼容性问题。当 APK 检查报告 4KB/UNALIGNED、添加原生 AAR（ONNX、OpenCV 等）、或需要判断 Gradle 开关/zipalign 是否足够时使用。
---

# Android 16 KB 页大小

**16 KB 问题不是一个构建开关，而是 APK 内预制 64 位 `.so` 文件的 ELF
`PT_LOAD` 对齐。** 任何 Gradle 标志、`useLegacyPackaging`、`zipalign -P 16`
都无法改变一个按 4 KB 页编译的 ELF 内部的对齐。解决办法是交付上游已经为
16 KB 构建好的 64 位原生库（或用 `-Wl,-z,max-page-size=16384` 重新编译）。

策略：遵循官方建议，而不是“4 KB 被禁止”。4 KB 对齐的应用仍能在 4 KB 设备
上运行（这台手机就是）。目标是准备好迎接 16 KB 设备，并让取舍清晰可见。

## 第一步：找出谁真正没有对齐

```sh
python3 <skills>/android-build/scripts/check-16kb.py app/build/outputs/apk/debug/app-debug.apk
```

报告会逐个 64 位库显示 `min_align=0x1000`（4 KB，有问题）或 `0x4000`
（16 KB，正常）。典型的元凶来自原生 AAR：

- `libonnxruntime.so` / `libonnxruntime4j_jni.so`（ONNX Runtime）
- `libopencv_java4.so`（OpenCV）
- `libc++_shared.so`（常被这些 AAR 重新打包）

32 位 ABI（`armeabi-v7a`、`x86`）是 `SKIP`；只有 64 位 ELF
（`arm64-v8a`、`x86_64`）才算数。

## 哪些做法不能解决问题

- **`zipalign -P 16` / `useLegacyPackaging`**：它们对齐的是 *APK zip 内部*
  的 `.so`。它们不会触碰 ELF 的 `PT_LOAD` 段。运行时加载器看到的仍是 4 KB
  的 ELF 对齐。
- **`ANDROC_16KB_STRICT=0`**：只是跳过检查。应用在 16 KB 设备上仍然无法
  加载该库。
- **Gradle 的“16 KB 开关”**：AGP 没有任何开关能重新编译第三方预制的 `.so`
  文件。
- **降级到 32 位（`armeabi-v7a`）**：能通过检查，因为 32 位被跳过，但会丢掉
  64 位支持，不算真正的修复。

## 真正能解决的办法：升级依赖

把 AAR 换成其 Android 预制产物已经 16 KB 对齐的版本。真实示例（RapidOCR，
来自一个设备端 OCR 项目）：

```gradle
configurations.all {
    resolutionStrategy {
        force 'com.microsoft.onnxruntime:onnxruntime-android:1.23.2'
        force 'org.opencv:opencv:4.12.0'
    }
}

dependencies {
    implementation 'io.github.hzkitty:rapidocr4j-android:1.0.0'
    implementation 'org.opencv:opencv:4.12.0'   // 16 KB-aligned prebuilt
}
```

为什么有效：

- ONNX Runtime 1.18.0（RapidOCR 1.0.0 拉取的版本）交付的是 4 KB 的
  `arm64-v8a` 库。1.23.2 交付的是 16 KB 的版本。
- OpenCV 4.9.0 是 4 KB；4.12.0（NDK 27+）已 16 KB 对齐，并且还带来一个
  16 KB 的 `libc++_shared.so`。
- 不需要在手机上从源码重新编译 ONNX/OpenCV，并且保留了 64 位。

重新构建后，检查结果应显示所有 64 位库都是 `16KB OK`：

```text
arm64-v8a: 8/8 16KB OK
x86_64:    8/8 16KB OK
armeabi-v7a/x86: SKIP
```

风险：包装库是针对旧的原生版本测试的。仅编译和安装还不够——在宣布成功前要
运行实际功能（例如拍一张照并跑 OCR）。如果新 ABI 表现异常，就把包装库固定
到官方使用较新原生库的版本，或者自行重新编译。

## 如果没有可用的 16 KB 构建

- 当你能控制源码时，优先使用 NDK r28+ 与
  `-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON` +
  `-Wl,-z,max-page-size=16384`。
- 对于无法替换的仅 4 KB 依赖，在文档中说明，并在该次构建中设置
  `ANDROC_16KB_STRICT=0`。这是已知限制，不是修复。
- 绝不要退回到 4 KB 的 `aapt2`：`aapt2` 在设备上执行，是关键工具之一。

## 内置工具链状态

| 组件 | 状态 |
|---|---|
| opencode 2.3.2 musl | 16 KB |
| musl loader, proot, libc++/libstdc++/libgcc, librg, libandroid-shmem | 16 KB |
| Termux JDK（`libjvm.so`、`libjava.so`） | 16 KB |
| Termux `bash`/`git`/`node`/`python3` | 16 KB |
| `aapt2`（16 KB 构建） | 16 KB |
| `aidl`（Termux 软件包，已预装） | 16 KB |
| `adb`（Termux `android-tools`，已预装） | 16 KB |
| `aapt`、`dexdump`、`split-select`、`zipalign`（lzhiyong 静态版） | 4 KB，可选 |

`make-toolchain.py` 在打包前会审计关键工具（`aapt2`、`aidl`）和 Termux 的
`adb`；一旦退化，工具链构建就会失败。上面那几个 4 KB 工具在正常构建中不会被
AGP 8.5 执行。

## 已知限制

- 测试设备是 4 KB（`getconf PAGE_SIZE` = 4096）；16 KB 是通过静态 ELF 对齐
  验证的，尚未在 16 KB 内核上验证。
- 始终要对最终的 release APK 重新运行检查器，而不要只检查 debug 构建。
