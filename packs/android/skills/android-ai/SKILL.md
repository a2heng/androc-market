---
name: Android AI
description: 用内置的 Termux 工具链在手机上本地运行 AI 模型——CPU 上的 ONNX Runtime、TFLite 与 llama.cpp，含模型存储、量化、线程、内存/发热限制，以及诚实的 NPU/MNN 现状。当任务提到本地推理、设备端模型、ONNX、TFLite、GGUF、llama.cpp、MNN、embedding、ASR、OCR 或 NPU 时使用。
---

# Android AI（设备端推理）

Androc 在 proot 工具箱内打包了一套小巧、以 CPU 优先的 AI 栈。它的目标是
真正的设备端任务（VAD/ASR、OCR、embedding、小型对话模型），而不是假装手机
能跑 7B 模型。

**每个引擎都单独成文——它们的 API 和模型格式互不通用：**

| 任务 | 引擎 | 参考 |
|---|---|---|
| `.onnx` 模型（ASR、OCR、VAD、embedding、经典 CV/NLP） | ONNX Runtime（Python） | [`references/onnxruntime.md`](references/onnxruntime.md) |
| `.tflite` 模型（MobileNet、小型检测器、MediaPipe 导出） | TFLite runtime（Python） | [`references/tflite.md`](references/tflite.md) |
| 对话 / 补全 / 本地 LLM | llama.cpp（GGUF，CLI + OpenAI 服务器） | [`references/llama-cpp.md`](references/llama-cpp.md) |
| 一套引擎同时覆盖视觉 + LLM，或厂商 NPU | MNN —— **尚未内置**，需要原生集成 | [`references/mnn.md`](references/mnn.md) |

## 已安装的内容

工具箱（`$PREFIX`，真实路径 `/data/data/<pkg>/files/usr`）包含：

| 软件包 | 版本 | 位置 |
|---|---|---|
| `python` | 3.14 | `$PREFIX/bin/python` |
| `python-numpy` | 2.5.4 | `$PREFIX/lib/python3.14/site-packages/numpy` |
| `python-onnxruntime` | 1.31.1 | `.../site-packages/onnxruntime` + `$PREFIX/lib/libonnxruntime.so` |
| `python-tflite-runtime` | 2.21.0 | `.../site-packages/tflite_runtime` |
| `llama-cpp` | 1.0.0 | `$PREFIX/bin/llama-cli`, `llama-server`, `llama-quantize`, … |

验证（在 Androc 的本地终端或任意 proot shell 内）：

```sh
bash ~/.config/opencode/skills/android-ai/scripts/check-ai.sh
```

**不要**用 `pip install onnxruntime` / `pip install
tflite-runtime` 安装这些：PyPI 的 wheel 是 manylinux（glibc）的，在 Android
bionic 上会失败。改用 Termux 内置的软件包（`pkg install …`）。

## 模型存储

把权重放在仓库之外，也放在 `$TMPDIR` 之外：

```text
~/models/
├── onnx/<name>/*.onnx
├── tflite/<name>/*.tflite
└── gguf/<name>/*.gguf
```

`~/models` 与 `$HOME` 在同一块私有存储上，能挺过 APK 更新。
绝不要提交权重；也不要放在 `cache/`（系统会清理它）。

## 性能规则（手机现实）

- **只用 CPU 是可移植的路线。** 大多数手机通过 Termux 没有可用且有文档的 NPU
  API；NNAPI 可能悄悄回退或直接失败。把 NPU 视为实验性，并且始终保留 CPU
  路径。
- **使用 int8/fp16 量化。** 在手机上跑 FP32 LLM 毫无意义。
- **线程：** 用大核，而不是全部核心。从 `-t 4`（llama.cpp）和
  `intra_op_num_threads=4`（ONNX）开始；必要时用 `/proc/cpuinfo` 和 `taskset`
  测量。
- **内存：** 一个 Q4 的 0.5B 模型需要约 0.5–0.8 GB；1.5B 约 1.2–1.8 GB；
  3B 约 2.5 GB。要给 Android、opencode 和 Gradle 守护进程留出余量。
- **不要在 Gradle 构建时运行模型。** 两者都是 CPU 密集型，手机会被降频；
  先运行 `clean-caches.sh`/停掉守护进程。
- **保持模型可 mmap**（GGUF/ONNX 外部数据），而不是在启动时把它们复制进内存。
- **给实验设定时限：** 加载 → 一次推理 → 打印延迟 → 退出。除非用户要求，
  任务结束后不要留着 `llama-server` 在跑。

## 选择引擎

1. 模型是 `.onnx` → ONNX Runtime。从 CPU 开始；只有在 CPU 可用后才尝试
   `NnapiExecutionProvider`。
2. 模型是 `.tflite` → TFLite runtime（CPU；没有捆绑 GPU/NNAPI delegate 的
   `.so`）。
3. 对话/LLM 或 `.gguf` 文件 → llama.cpp。一次性测试优先用 `llama-cli`，只有
   当另一个客户端需要 HTTP API 时才用 `llama-server`。
4. 需要 NPU，或想用一套运行时同时覆盖视觉和 LLM → 见 MNN 说明；在这台设备上
   构建并测试通过之前，不要承诺它。

## 常见故障

| 症状 | 原因 | 修复 |
|---|---|---|
| `ModuleNotFoundError: onnxruntime` | 在 proot 之外运行，或工具箱未安装 | `oc-engine status` / `bash ~/.config/.../check-ai.sh` |
| `ImportError: libonnxruntime.so` | `LD_LIBRARY_PATH` 缺少 `$PREFIX/lib` | 通过 `proot`/`oc-*` 运行，不要直接调用该 ELF |
| ONNX 形状错误 | 模型输入维度是静态的 | 读取 `sess.get_inputs()[0].shape`，严格按其喂数据 |
| NNAPI provider 报错 | 厂商驱动/算子覆盖不足 | 回退到 `CPUExecutionProvider` |
| `llama-cli: model not found` | GGUF 路径错误 / 模型未下载 | 使用 `~/models/gguf/...`，用 `ls -lh` 检查 |
| 加载 GGUF 时被 OOM 杀掉 | 模型太大 / mmap 被禁用 | 换更小的量化（Q4_K_M），关掉 `--no-mmap`，关闭其他应用 |
| `pip install onnxruntime` 失败 | 在 bionic 上用 glibc 的 wheel | 使用 Termux 软件包 |

## 许可证

- ONNX Runtime：MIT。TFLite runtime：Apache-2.0。llama.cpp：MIT。
  MNN：Apache-2.0。
- 模型许可证是另一回事：在再分发权重或把它们打进 APK 之前，先看模型卡。
