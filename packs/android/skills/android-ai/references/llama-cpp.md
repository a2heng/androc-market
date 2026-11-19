# llama.cpp / GGUF（Termux，CPU）

内置软件包：`llama-cpp 1.0.0`。二进制位于 `$PREFIX/bin`，真正的代码在
`$PREFIX/lib/libllama*.so`、`libggml*.so`。模型格式：**GGUF**。

CPU 后端始终可用（ARM NEON + int8 点积）。
`llama-cpp-backend-opencl` / `llama-cpp-backend-vulkan` 包**没有**内置；只有你
明确想要 GPU 卸载时才安装：

```sh
pkg install llama-cpp-backend-opencl     # Adreno / Mali, experimental
pkg install llama-cpp-backend-vulkan
```

## 一次性对话（测试推荐）

```sh
llama-cli \
  -m ~/models/gguf/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf \
  -p "用一句话解释什么是 proot" \
  -n 128 -t 4 -c 2048 --jinja
```

- `-m` 模型，`-p` 提示词，`-n` 最大新 token 数，`-t` 线程数，`-c` 上下文。
- `--jinja` 使用模型自带的对话模板（instruct 模型必需）。
- 如果该构建支持，加上 `-no-cnv` / `--single-turn` 得到非交互式回答；
  否则用管道传入提示词，让它由 `-n` 停止。
- 设定时限：0.5B Q4 模型在大核上应几秒内作答；3B 模型要慢好几倍，还会让手机
  发热。

## OpenAI 兼容服务器

```sh
llama-server \
  -m ~/models/gguf/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 \
  -t 4 -c 4096 --jinja
```

然后：

```sh
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"local","messages":[{"role":"user","content":"hi"}],"max_tokens":64}'
```

当另一个应用/技能期望 OpenAI API 时，这很有用。绑定到 `127.0.0.1`，绝不要用
`0.0.0.0`，并在结束后停止服务器。

## 模型大小 / 内存预算（Q4_K_M）

| 参数量 | 文件大小 | 加载 + 上下文（粗略） |
|---|---:|---:|
| 0.5–0.6B | 0.4–0.5 GB | 0.7–0.9 GB |
| 1.5–1.7B | 1.0–1.2 GB | 1.5–2.0 GB |
| 3–4B | 2.0–2.6 GB | 3.0–3.8 GB |
| 7–8B | 4.5–5.0 GB | 手机上不推荐 |

始终为 Android + opencode 留出余量。如果进程被 OOM 杀掉，就换更小的模型或更小的
上下文（`-c 1024`）。

## 测量与转换

```sh
llama-bench -m <model.gguf> -t 4          # prompt/gen tok/s
llama-quantize <in.gguf> <out.gguf> Q4_K_M
```

`llama-quantize` 能在手机上跑，但很吃 CPU/内存；可能的话优先在 PC 上转换。

## 下载模型

使用模型的官方 Hugging Face 仓库。在此环境中 `HF_ENDPOINT` 可能指向
`https://hf-mirror.com`；用 `hf download`（配合 `hf_transfer`）而不是 `curl`，
这样中断的下载可以续传。存放在 `~/models/gguf/<name>/` 下，绝不要放在
`$TMPDIR` 或 `cache/`。

## 不要做

- 为了“看看能不能跑”而运行 7B 模型——它会被 OOM/降频，纯属浪费时间。
- 测试后仍留着 `llama-server` 在跑（它占着 CPU/内存和一个端口）。
- 在没有安装 OpenCL/Vulkan 后端包的情况下指望 `-ngl` 有用。
- 直接使用 `.safetensors`/`.bin`；先转换成 GGUF（在 PC 上用
  `convert_hf_to_gguf.py`）。
