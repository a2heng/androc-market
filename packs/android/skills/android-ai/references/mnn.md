# MNN（原生 Android）— 状态：**未内置**

MNN 是阿里巴巴的推理引擎（Apache-2.0）。当你希望用一套引擎覆盖视觉 + LLM +
NPU 实验时，它很合适，但**它不是 Termux 软件包**，所以无法通过 `pkg install`
或 `pip install` 使用。

## 体积

官方发布 `3.6.2` 提供：

```text
mnn_3.6.2_android_armv7_armv8_cpu_opencl_vulkan.zip   6,746,981 bytes (~6.4 MiB)
```

该 zip 覆盖 **两个 ABI**（armv7 + armv8）和三个后端（CPU、OpenCL、Vulkan），
所以仅 arm64 的子集小于 6.4 MiB。**APK 体积不是阻碍**；阻碍是原生集成和真机
测试。

## 为什么它不在工具箱里

- Termux 软件包是为 Android bionic 构建并用 `pkg` 安装的；MNN 提供的是预制的
  原生库和头文件，不是 Termux 软件包。
- 使用它需要以下之一：
  1. **在 Androc 里做 JNI/AAR** —— 把 arm64 的 `libMNN*.so` 复制到
     `app/src/main/jniLibs/arm64-v8a/`，用 NDK 编译一个小的 JNI 包装层，并把
     它暴露给 UI/代理（例如一个仅监听 localhost 的 HTTP 端点）；
     或者
  2. **交叉编译的 CLI** —— 用 NDK 构建一个极小的 `mnn` 运行器，放进
     `$PREFIX/bin`，再从 proot shell 调用它。
- 模型必须在 PC 上用 `MNNConvert` 转换成 `.mnn`（或由 MNN 工具链导出）。
  `.onnx`/`.tflite`/`.gguf` 不能直接加载。

## NPU / GPU 的实际情况

- MNN 有 **NNAPI** 后端，但 Android 手机能否通过 NNAPI 提供可用的 NPU，取决于
  厂商驱动和算子覆盖。NNAPI 本身在较新的 Android 版本上已被弃用；不要承诺
  NPU 加速。
- MNN 的 **OpenCL** 后端在某些设备上可以用手机 GPU（Adreno/Mali）；
  **Vulkan** 是另一个选择。两者都需要真机基准测试。
- **CPU** 后端（ARM82/NEON，int8）是唯一可预测的路径。在引入第二套引擎之前，
  先和 llama.cpp（LLM）或 ONNX Runtime（小模型）对比。

## 如果我们决定加入它

1. 下载 Android zip，只取 `arm64-v8a` 的库 + 头文件。
2. 对每个 `.so` 运行
   `python app/src/main/assets/skills/android-build/scripts/check-16kb.py`；
   MNN 的发布较新，但仍要验证，因为 `jniLibs` 是按
   `extractNativeLibs=true` 打包的。
3. 构建尽可能小的运行器：
   - 视觉：MobileNet/ResNet `.mnn` → 一张图片 → top-5；
   - LLM：用 0.5B–1.5B 量化模型的 MNN-LLM demo。
4. 在**真机**上做基准测试：加载时间、首 token、tok/s、内存、发热。
5. 只有当它胜过现有路径时才内置（否则只是死重量）。

## 什么时候 MNN 是正确选择

- 你需要一套运行时覆盖**视觉 + LLM + 音频**，并且愿意写原生代码。
- 你明确针对某个厂商 NPU，并且能在该设备上测试。
- 你已经有了来自 PC 流水线的 `.mnn` 模型。

## 什么时候不要用

- 一个 `.onnx` 模型就能用 —— 用 ONNX Runtime（已经内置）。
- 一个 `.gguf` LLM 就能用 —— 用 llama.cpp（已经内置，更简单）。
- 你只需要小模型的 CPU 推理 —— 内置的栈就够了。

## 许可证

MNN 是 Apache-2.0。模型权重有自己的许可证；把权重打进 APK 之前先检查它们。
