---
name: Android Background
description: 在 Android 上正确地执行后台工作：WorkManager、前台服务、闹钟、唤醒锁以及电池/Doze 限制。用于同步、上传、长时间构建或通知。
---

# Android 后台任务

## 选择正确的机制

| 需求 | 使用 |
|---|---|
| 可延迟、有保证的同步 | WorkManager |
| 用户可见的长时间任务（构建、下载） | 前台服务 |
| 精确时间（闹钟） | `AlarmManager` 精确闹钟 |
| 周期性轻量检查 | WorkManager 周期任务（最少 15 分钟） |
| 应用可见时的即时短任务 | 协程/`lifecycleScope` |

不要用裸后台线程或 `Service` 做必须存活的工作；Android 会杀掉它。

## WorkManager

```groovy
implementation 'androidx.work:work-runtime:2.9.1'
```

```kotlin
val request = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES).build()
WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "sync", ExistingPeriodicWorkPolicy.KEEP, request)
```

约束：网络、电量不低、充电中。Worker 必须是幂等的。

## 前台服务

- 在清单中声明服务以及 `foregroundServiceType`（例如 `dataSync`、
  `specialUse`）。
- 用 `ContextCompat.startForegroundService` 启动。
- 在几秒内调用 `startForeground`。
- 发出一条清晰、常驻的通知，并带停止操作。
- 在 Android 13+ 上请求 `POST_NOTIFICATIONS`。
- 在 `finally` 中释放唤醒锁。

## Doze 与厂商清理机制

- 除非功能确实需要，不要用精确闹钟对抗 Doze。
- 对长时间运行的开发工具，请用户关闭电池优化。
- OPPO/ColorOS、小米/HyperOS 等会激进地杀掉后台进程；
  在真机上测试并记录加入白名单的步骤。

## 本项目

opencode 服务使用一个前台服务和一个看门狗。如果它在后台停止，
检查通知、电池优化，以及选项里的看门狗间隔。
