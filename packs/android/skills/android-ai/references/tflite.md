# TFLite runtime（Termux Python）

内置软件包：`python-tflite-runtime 2.21.0`（Python 3.14），安装在
`$PREFIX/lib/python3.14/site-packages/tflite_runtime`。

这只是 **CPU** 运行时。该包仅包含
`_pywrap_tensorflow_interpreter_wrapper.so`，别的一无所有——**没有**
`libtensorflowlite_gpu_delegate.so` / NNAPI delegate 随附，所以在这个环境下
不要为 `.tflite` 承诺 GPU/NPU 加速。

## 最小推理

下面的 API 取自该包中精确的 `interpreter.py`（同名接口在 TensorFlow 的
`tf.lite` 中也存在）：

```python
import numpy as np
from tflite_runtime.interpreter import Interpreter

it = Interpreter(
    model_path="/data/data/<pkg>/files/home/models/tflite/foo/model.tflite",
    num_threads=4,                 # big cores, not all 8
)
it.allocate_tensors()

inp = it.get_input_details()[0]
out = it.get_output_details()[0]
print(inp["name"], inp["shape"], inp["dtype"])

x = np.zeros(inp["shape"], dtype=inp["dtype"])
it.set_tensor(inp["index"], x)
it.invoke()
y = it.get_tensor(out["index"])
print(y.shape, y.dtype)
```

说明：

- 路径必须是绝对路径；`~` 需要自行展开。
- `allocate_tensors()` 必须在 `set_tensor`/`invoke` 之前调用。
- 动态形状：在 `allocate_tensors()` 之前调用
  `resize_tensor_input(inp["index"], new_shape)`（或在 resize 之后重新分配）。
- 多输入/多输出：遍历 `get_input_details()` / `get_output_details()`。

## 模型

在 PC 上用 TensorFlow Lite 转换器（`tf.lite.TFLiteConverter`、PyTorch 用
`ai-edge-torch`，或 MediaPipe 导出）转换，然后把 `.tflite` 复制到
`~/models/tflite/<name>/`。

- CPU 上优先用 **dynamic-range int8** 或 **int8 full-integer** 量化。
- 检查 `inp["dtype"]`；量化模型需要 `np.int8`/`np.uint8`，通常还需要
  scale/zero-point（`inp["quantization"]`）。
- 让模型文件保持小巧（<100 MB）并便于 mmap。

## 何时用 TFLite 而不是 ONNX

- 模型只以 `.tflite` 形式存在（MediaPipe / 移动端导出）。
- 极小的视觉/关键词模型，此时 TFLite runtime 更精简。
- 其他情况优先用 ONNX Runtime：Python 工作流相同，而且它的 Termux 构建还带有
  XNNPACK/NNAPI provider。

## 不要做

- `pip install tflite-runtime`（没有 cp314/manylinux wheel；何况是 glibc）。
- 在手机上 `pip install tensorflow`（体积巨大，且不受支持）。
- 指望 `load_delegate("libtensorflowlite_gpu_delegate.so")` 能用——那个库没有
  随包提供。
