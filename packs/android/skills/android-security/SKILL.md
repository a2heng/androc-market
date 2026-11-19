---
name: Android Security
description: 应用 Android 安全基础：最小权限、导出组件、网络安全、keystore/密钥、WebView 和备份规则。发布前或审查涉及安全的代码时使用。
---

# Android 安全

## 权限

- 只申请功能实际用到的东西。优先在使用点申请运行时权限。
- 除非应用是文件管理器/IDE，否则避免 `MANAGE_EXTERNAL_STORAGE`；它会触发
  商店审核和用户不信任。
- `REQUEST_INSTALL_PACKAGES` 风险很高；本项目需要它在设备上构建，但要说明
  原因。

## 组件

- 每个带 intent filter 的 activity/service/receiver 都必须显式设置
  `android:exported`。
- 不需要对外公开的组件就不要导出。
- 校验所有从外部 intent/URI 收到的数据。
- 除非确实需要可变性，否则使用 `PendingIntent.FLAG_IMMUTABLE`。

## 网络

`res/xml/network_security_config.xml`：

```xml
<network-security-config>
    <base-config cleartextTrafficPermitted="false" />
</network-security-config>
```

在 manifest 中引用它：

```xml
<application android:networkSecurityConfig="@xml/network_security_config" ...>
```

不要禁用证书校验。不要记录 token 或 Authorization 头。

## 密钥

- 绝不要在 Java/Kotlin 或 `BuildConfig` 中硬编码 API key。
- 本地密钥使用 `EncryptedSharedPreferences` 或 Android Keystore。
- provider token 放在 opencode 配置里，不要放在应用源码里。
- 分享日志时脱敏 `sk-`、`ghp_`、`Bearer`。

## WebView

- 除非必须，否则禁用 JavaScript；确实需要时，把导航限制到受信任的主机。
- 不要为不受信任的内容添加 `addJavascriptInterface`。
- 尽可能设置 `setAllowFileAccess(false)`、`setAllowContentAccess(false)`。
- 此启动器为 opencode 使用本地 WebView；保持它绑定 `127.0.0.1` 并通过
  认证。

## 备份与调试

- 含 token/会话的应用设置 `android:allowBackup="false"`。
- 从 release 构建中移除 `android:debuggable`。
- 除非本地回环服务器需要，否则关闭 `android:usesCleartextTraffic`；
  尽可能缩小其作用范围。

## 审查清单

1. 权限与功能匹配。
2. 导出组件已最小化并经过校验。
3. 源码和日志中没有密钥。
4. 网络配置拒绝明文传输。
5. Release 构建启用 R8 且没有调试标志。
