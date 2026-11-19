---
name: Android UI
description: 在手机上构建或改进 Android UI（Compose 或 XML/Views）、Material 3 主题、响应式布局、边缘到边缘、深色模式与无障碍。适用于界面、布局、主题和视觉打磨。
---

# Android UI

## 选择技术栈

- **XML/Views + Material Components**：离线最稳妥；Gradle 缓存里已有本应用
  自身构建产生的 `appcompat` 和 `material`。
- **Jetpack Compose**：效果更好，但 Gradle 缓存里需要有 Compose 构件。
  先用一个小构建验证；如果解析失败，仅在用户同意时使用 `OC_BUILD_ONLINE=1`，
  或继续用 XML。

## Material 3 主题

`res/values/themes.xml`：

```xml
<style name="Theme.MyApp" parent="Theme.Material3.DayNight.NoActionBar">
    <item name="colorPrimary">#4F46E5</item>
    <item name="colorSecondary">#0EA5E9</item>
</style>
```

使用 `?attr/colorSurface`、`?attr/colorOnSurface`、`?attr/colorPrimary`，而不是
硬编码颜色，这样深色模式才能生效。

## 手机布局规则

- 每个界面只有一个主操作；触摸目标最小 48dp。
- 用带 weight 的 `ConstraintLayout` 或 `LinearLayout`；避免固定宽度。
- 内边距：设置 `android:fitsSystemWindows="true"` 或 Compose 的
  `WindowInsets.safeDrawing`，避免内容被状态栏/导航栏遮挡。
- 长文本：`maxLines`、`ellipsize`，以及可滚动容器。
- 横屏/平板：使用 `-land` 资源或 `SlidingPaneLayout`；不要假定是竖屏。

## 无障碍

- 每个 `ImageView` 都需要 `contentDescription`（或 `importantForAccessibility="no"`）。
- 正文字号对比度 >= 4.5:1。
- 支持字体缩放：文本用 `sp`，不要用 `dp`。
- 条件允许时用 TalkBack 测试。

## Compose 注意事项

- 状态上提；让 composable 保持小巧。
- UI 状态用 `rememberSaveable`。
- 不要在组合阶段做重活；用 `LaunchedEffect`。
- 用 `@Preview` 预览，但要记住预览不在真机上运行。
- Compose 编译器/Kotlin 版本必须与 AGP/Kotlin 插件匹配。

## 验证

1. 用 `android-build` 技能构建。
2. 用 `android-debug/scripts/install-run.sh` 安装并启动。
3. 截图：`adb exec-out screencap -p > /tmp/screen.png`。
4. 检查竖屏、横屏、深色模式和放大字体。
