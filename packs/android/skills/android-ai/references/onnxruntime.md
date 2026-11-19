# ONNX Runtime（Termux Python）

内置软件包：`python-onnxruntime 1.31.1` + `python-numpy 2.5.4`
（Python 3.14）。安装在 `$PREFIX/lib/python3.14/site-packages/onnxruntime`；
C++ 运行时是 `$PREFIX/lib/libonnxruntime.so`。

## 已验证的冒烟测试

Python 包自带两个极小的模型（`mul_1.onnx`、`logreg_iris.onnx`），因此不用下载
任何东西就能验证运行时：

```sh
python ~/.config/opencode/skills/android-ai/scripts/onnx_smoke.py
```

预期输出（已测试）：

```text
onnxruntime 1.31.1
providers   [...]
input       X [3, 2] tensor(float)
input data  [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
output      [[1.0, 4.0], [9.0, 16.0], [25.0, 36.0]]
OK
```

## 最小推理

```python
import numpy as np
import onnxruntime as ort

sess = ort.InferenceSession("~/models/onnx/foo/model.onnx",
                            providers=["CPUExecutionProvider"])
for i in sess.get_inputs():
    print(i.name, i.shape, i.type)          # static dims must match exactly

x = np.zeros((1, 3, 224, 224), dtype=np.float32)
y = sess.run(None, {sess.get_inputs()[0].name: x})[0]
print(y.shape, y.dtype)
```

## 执行提供程序

Termux 构建编译时包含 **CPU**、**XNNPACK** 和 **NNAPI** provider
（已在 `libonnxruntime.so` 中确认）。实际能用什么取决于手机：

```python
print(ort.get_available_providers())
```

- 从 `CPUExecutionProvider` 开始。
- 此构建中有 `XnnpackExecutionProvider`；当 CPU 路径太慢且模型是浮点模型时，
  显式加上它（`providers=["XnnpackExecutionProvider", "CPUExecutionProvider"]`）。
- `NnapiExecutionProvider` 可能用到厂商 NPU，但算子覆盖有限且驱动差异很大。
  始终在列表里保留 `CPUExecutionProvider`，以便不支持的节点可以回退：

```python
sess = ort.InferenceSession(model, providers=[
    "NnapiExecutionProvider", "CPUExecutionProvider",
])
```

如果创建会话或第一次 `run()` 失败，就放弃 NNAPI，改用 CPU。

## 线程与内存

```python
so = ort.SessionOptions()
so.intra_op_num_threads = 4       # big cores; do not use all 8
so.inter_op_num_threads = 1
so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
```

- CPU 上优先用 int8 量化的 `.onnx`；fp16 在大多数手机 CPU 上并不会更快。
- 仅在诊断时运行 `onnxruntime_test`（随 `$PREFIX/bin` 提供）。
- C++ 库有 22 MB；模型是分开的，应放在 `~/models/onnx/`。

## 转换模型

转换通常在 PC 上完成（`torch.onnx.export` / `onnxsim`），而不是在手机上。把
生成的 `.onnx`（以及外部数据文件）复制到 `~/models/onnx/<name>/`。保持
opset ≤ 运行时版本（1.31 支持较新的 opset；用 `onnxruntime.__version__` 确认）。

## 不要做

- `pip install onnxruntime`（manylinux/glibc 的 wheel——在 bionic 上会失败）。
- 把 `~` 直接传给 `InferenceSession`；先展开它（`os.path.expanduser`）。
- 对静态模型喂入与 `get_inputs()[0].shape` 不同的形状。
