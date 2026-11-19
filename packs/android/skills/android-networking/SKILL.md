---
name: Android Networking
description: 为 Android 应用添加 HTTP/API 调用：OkHttp/Retrofit/Ktor、协程、超时、重试、缓存与安全的错误处理。接入后端或下载数据时使用。
---

# Android 网络

## 依赖

优先选用满足需求的最小技术栈：

```groovy
implementation 'com.squareup.okhttp3:okhttp:4.12.0'
// or
implementation 'com.squareup.retrofit2:retrofit:2.11.0'
implementation 'com.squareup.retrofit2:converter-gson:2.11.0'
```

先检查离线缓存（`android-deps`）；这些库可能没有随包提供。

## 规则

- 绝不在主线程做网络 I/O。
- 使用 `suspend` 函数和 `Dispatchers.IO`。
- 显式设置连接/读取/调用超时。
- 只重试幂等请求，使用退避并设置上限。
- 处理 HTTP 错误和畸形 JSON；不要因空响应体崩溃。
- 不要记录令牌或完整的 Authorization 头。
- 使用 HTTPS；不要关闭证书校验。
- 只缓存安全的内容；遵守 `Cache-Control`。

## 最小的 OkHttp 示例

```kotlin
val client = OkHttpClient.Builder()
    .connectTimeout(15, TimeUnit.SECONDS)
    .readTimeout(30, TimeUnit.SECONDS)
    .build()

suspend fun get(url: String): String = withContext(Dispatchers.IO) {
    client.newCall(Request.Builder().url(url).build()).execute().use { r ->
        if (!r.isSuccessful) error("HTTP ${r.code}")
        r.body?.string().orEmpty()
    }
}
```

## Android 清单

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

仅当你确实要检查连接状态时才添加 `ACCESS_NETWORK_STATE`。

## 在手机上测试

- 手机可能连着热点或移动数据；用 `adb shell dumpsys connectivity` 检查。
- 本地回环（`127.0.0.1`）在多数版本上不需要明文流量许可，但
  `networkSecurityConfig` 仍可能拦截它；把例外范围限制在 `localhost`。
- 测试离线和飞行模式以及慢速网络，不要只测 Wi-Fi。
