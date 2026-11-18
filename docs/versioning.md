# 版本管理（App / 契约 / 市场 / 组件）

> 原则：**每个东西只跟自己的上游走，不互相绑版本。**
> 兼容性用显式字段判断，不靠“版本号看起来差不多”。

## 1. 四条版本轴

| 对象 | 版本形态 | 例子 | 谁决定 |
|---|---|---|---|
| App（基础 UI） | SemVer + `versionCode` | `0.6.0` / `9` | 主仓库 CI |
| 契约 `:contracts` | SemVer | `1.0.0` | 主仓库，破坏性改动升 major |
| 市场索引 schema | 整数 | `1` | 市场仓库，字段不兼容时 +1 |
| 组件 pack | `<上游版本>-<修订>` | `2.3.2-1` | 各组件发布流程 |
| 市场快照 | 日期-序号 | `2026.11.19-1` | 市场 CI，仅标识索引生成批次 |

**不要**把 App 版本塞进 pack 版本，也不要用市场快照当兼容性判断。

## 2. 组件版本规则

| 组件 | 版本 | 上游变化时 | 只改打包/签名时 |
|---|---|---|---|
| `kernel-opencode` | `2.3.2-1` | `2.3.3-1` | `2.3.2-2` |
| `runtime-core` | `3.24.4-1` | Alpine 升级 | 重建 rootfs |
| `lang-python` | `3.14.10-1` | CPython 升级 | 重新打包 |
| `build-t1` | `36.0.0-1` | SDK/build-tools 升级 | 修构建脚本 |
| `build-rust` | `1.100.0-1` | rustc 升级 | 修脚本 |

- **上游版本在前，修订号在后**；修订号只在“上游没变、我们重新打包/签名/修 bug”时 +1。
- 每个组件只有一个**当前稳定版**；旧版本保留用于回滚，不并行安装多个同 id 版本。
- 组件的 `version` 是给人看的；排序/比较用 `upstreamVersion` + `revision`，不要字符串比较。

## 3. 兼容性字段（取舍依据）

市场索引里每个 pack 至少带：

```json
{
  "version": "2.3.2-1",
  "upstreamVersion": "2.3.2",
  "abi": "arm64-v8a",
  "minAppVersionCode": 9,
  "minContracts": "1.0.0",
  "requires": [
    { "id": "runtime-core", "min": "3.24.4-1", "optional": true }
  ],
  "schema": 1
}
```

安装决策顺序：

1. **硬条件**：`abi`、`minAppVersionCode`、`minContracts`、索引 `schema` 必须匹配；
2. **依赖**：`requires` 里非 optional 的组件必须已安装且版本 ≥ `min`；
3. **取高**：所有满足硬条件的版本里，取 `upstreamVersion` 最高、同版本取 `revision` 最高；
4. **无解**：提示升级 App 或先装依赖，不“试试看能不能跑”。

App 只拒绝“比自己新”的 pack；**旧 pack 可以装在更新的 App 上**。

## 4. 跨多个组件怎么取舍

### 场景 A：OpenCode 发新版，UI 没变
只发 `kernel-opencode`；App 不动。用户增量 7.6 MB。

### 场景 B：App 发了新契约
App `0.6.0/9`，契约 `1.1.0`；旧 pack 的 `minContracts` 仍满足就继续可用。
只有真正依赖新契约的 pack 才写 `minContracts: 1.1.0`。

### 场景 C：构建包依赖运行工具
`build-t1` 声明 `requires runtime-core >= 3.24.4-1`。
市场安装时先装/升级 runtime，再装 build；卸载 build 不影响 runtime。

### 场景 D：上游破坏性变化
OpenCode `3.0` 与旧 UI 不兼容：新 pack 写 `minAppVersionCode: 10`。
旧 App 看到硬条件不满足，**只能升级 App**，不会装一个半坏的 pack。

### 场景 E：用户跨了好几个版本
增量只允许 **上一版 → 当前版** 且旧二进制 sha256 精确匹配。
跳版（2.3.0 → 2.3.2）没有匹配的 delta，直接下全量包；不要串多个 delta。

### 场景 F：两个包提供同一能力
同一 `id` 只保留一个激活版本；索引只给最新稳定版。
旧版本留在本机用于回滚，不作为“可同时启用”的第二份安装。

## 5. 回滚

- 安装前保留 `previous` 指针（版本 + sha256）；
- 新版本健康检查失败 → 自动切回 previous；
- 回滚只换 `current` 指针，不重新下载；
- 索引里的旧版本仍可手动“安装此版本”（降级），但需要显式确认。

## 6. 发布顺序

```text
1. 组件上游发版
2. 市场 CI: 下载 → 官方 sha256 → zstd → delta → 签名 index
3. 市场 release: pack / delta / index / index.sig
4. 提交 index.json（App 读 raw 或 release 资产）
5. App 刷新索引 → 比较版本 → 增量或全量安装
```

市场快照号（`generated` / `2026.11.19-1`）只是索引批次，**不参与**兼容判断。

## 7. 当前实际值（2026-11-19）

| 对象 | 值 |
|---|---|
| App | `0.5.0` / `versionCode 8`（thin 开发包） |
| 契约 | `1.0.0` |
| 索引 schema | `1` |
| `kernel-opencode` | `2.3.2-1`（官方 2.3.2；全量 xz 88.6 MB；差量待接入） |
| delta 基线 | 暂时停用（zstd patch 需要原生解码；下一步纯 Java 块差量） |
