---
name: Android Performance
description: 在手机上测量并改善 Android 应用性能：启动时间、卡顿、内存、基线配置文件、R8 与主线程工作。应用感觉变慢或用户要求优化时使用。
---

# Android 性能

## 先测量

```sh
adb shell am force-stop com.example.app
adb shell am start -W -n com.example.app/.MainActivity
```

`auto` 在 proot 内运行 adb（以及变量/复合命令行）；无需包装脚本。

`TotalTime`/`WaitTime` 就是启动耗时。运行 3 次，报告中位数，
而不是最好的一次。

卡顿与帧：

```sh
adb shell dumpsys gfxinfo com.example.app framestats
adb shell dumpsys gfxinfo com.example.app | grep -E "Janky|percentile"
```

内存：

```sh
adb shell dumpsys meminfo com.example.app
```

## 常见修复

- 把磁盘/网络/JSON 工作移出主线程。
- 避免在 `onDraw`/组合（composition）中分配对象；缓存对象。
- 列表使用 `RecyclerView`/`LazyColumn`，不要用嵌套滚动视图。
- 减少过度绘制；避免图片背后的整块不透明背景。
- release 构建启用 R8 和资源压缩。
- Compose：使用稳定参数、列表中的 `key`，避免在组合中读取
  频繁变化的状态。
- 为启动关键代码添加基线配置文件（需要 `androidx.profileinstaller`
  依赖和一个 benchmark 模块）。

## 基线配置文件（可选）

添加 `androidx.profileinstaller:profileinstaller` 和一个 `baseline-prof.txt`。
这需要依赖；先检查离线缓存，否则在使用 `OC_BUILD_ONLINE=1` 前先询问。

## 规则

- 没有前后测量的优化不要做。
- 报告设备、构建类型（debug/release）和确切命令。
- debug 构建慢得多；绝不要把 debug 启动与 release 相比。
- 手机的降频（热节流）是真实存在的：两次测量之间让设备冷却。
