---
name: Android i18n
description: 本地化 Android 应用：字符串资源、中文/英文/西班牙文、复数、RTL 与语言区域测试。当用户要求中文界面或多语言时使用。
---

# Android i18n

## 把所有用户可见的字符串放进资源

`app/src/main/res/values/strings.xml`：

```xml
<resources>
    <string name="app_name">My App</string>
    <string name="welcome">Welcome</string>
</resources>
```

`app/src/main/res/values-zh/strings.xml`：

```xml
<resources>
    <string name="app_name">我的应用</string>
    <string name="welcome">欢迎</string>
</resources>
```

XML 中用 `@string/welcome`，代码中用 `getString(R.string.welcome)`。
绝不要在布局里硬编码中文/英文。

## 复数与格式化

```xml
<plurals name="files">
    <item quantity="one">%d file</item>
    <item quantity="other">%d files</item>
</plurals>
```

`getResources().getQuantityString(R.plurals.files, n, n)`。

## RTL

- 用 `start`/`end` 代替 `left`/`right`。
- 用 `android:layout_marginStart`、`paddingStart`。
- 如果应用支持阿拉伯语/希伯来语，用伪 RTL 语言区域测试。

## 语言区域测试

```sh
adb shell am start -a android.settings.LOCALE_SETTINGS
```

`auto` 在 proot 内运行 adb；不需要额外包装。

或者在 Android 13+ 上使用按应用设置的语言（设置 → 应用 → My App → 语言）。
切换语言区域后，重新启动应用并截图。

## 中文要点

- 用 `values-zh` 作为简体/繁体回退；如果措辞不同，再加 `values-zh-rCN` /
  `values-zh-rTW`。
- 中文字符串保留中文标点（，。！？）；不要沿用英文标点。
- 不要翻译品牌名、文件路径、模型 ID、代码标识符。
- 此启动器的原生界面使用 `Zh.java`；opencode Web 界面跟随浏览器/服务器的
  语言。

## 验证

1. 用 `android-build` 构建。
2. 用 `android-debug/scripts/install-run.sh` 安装/启动。
3. 至少截取中文和英文两张截图。
4. 检查文字被裁切和缺少翻译的问题（`MissingTranslation` lint）。
