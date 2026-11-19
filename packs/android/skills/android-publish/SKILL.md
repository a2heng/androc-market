---
name: Android Publish
description: 在手机上发布构建好的 Android 应用：GitHub Releases、F-Droid、直接分发 APK、签名、校验和与发布说明。当用户要求发布或分享 APK 时使用。
---

# Android 发布

## 发布到哪里

本项目及它构建的应用使用了侧载类能力（执行下载的代码、
`MANAGE_EXTERNAL_STORAGE`、`REQUEST_INSTALL_PACKAGES`），并且可能面向较旧的
SDK。**不要承诺 Google Play 上架。**

使用：

- GitHub Releases（私有或公开）
- F-Droid / 自建 F-Droid 软件源
- 直接下载 APK / 本地分享

## 发布清单

1. 提升 `versionCode` 和 `versionName`。
2. 用 `android-release` 技能构建 release。
3. 安装并测试 release APK（不要只测 debug）。
4. 生成 SHA-256：
   ```sh
   sha256sum app-release.apk
   ```
5. 写发布说明：新功能、修复、已知限制、设备/ABI。
6. 上传 APK + 校验和。不要把 APK 提交到 git。

## 在手机上发布到 GitHub

如果 `gh` 可用且已认证：

```sh
gh release create v1.0.0 app-release.apk \
  --title "v1.0.0" --notes "Release notes..."
```

如果不可用，通过 GitHub 网页界面上传。私有仓库产生的是私有发布产物。

## F-Droid

- F-Droid 要求可复现构建和自由/开源许可证。
- 应用必须能从源码构建，不依赖专有组件。
- 向 `fdroiddata` 提交合并请求，附带元数据和构建配方。
- 以二进制形式捆绑的 GPL 组件需要满足源码/声明合规。

## 版本管理

- `versionCode` 单调递增。
- `versionName` 是人类可读的（`1.2.3`）。
- 在 git 中给发布打标签（`v1.2.3`）。

## 不要做

- 不要把 debug 签名的 APK 当作正式版本发布。
- 不要上传 keystore 或 `keystore.properties`。
- 没有证据时，不要声称已上架 Play 商店或已成功进入 F-Droid。
