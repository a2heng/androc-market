---
name: Android Release
description: 在手机上产出已签名的 release APK/AAB：keystore、签名配置、R8/minify、版本号、验证与校验和。当用户要求 release 构建或可发布的 APK 时使用。
---

# Android 发布构建

## 1. 创建 keystore（只需一次）

在应用沙箱内运行：

```sh
keytool -genkeypair -v \
  -keystore "$HOME/keys/release.jks" \
  -alias release -keyalg RSA -keysize 4096 -validity 10000 \
  -storepass "$STORE_PASS" -keypass "$KEY_PASS" \
  -dname "CN=MyApp, OU=Mobile, O=Example, L=City, S=State, C=CN"
```

绝不要提交 keystore 或密码。把它们放在 `$HOME/keys` 和被 gitignore 的本地
`keystore.properties` 中。

## 2. 签名配置

`app/build.gradle`：

```groovy
def props = new Properties()
def f = rootProject.file('keystore.properties')
if (f.exists()) props.load(new FileInputStream(f))
android {
    signingConfigs {
        release {
            storeFile rootProject.file(props['storeFile'])
            storePassword props['storePassword']
            keyAlias props['keyAlias']
            keyPassword props['keyPassword']
        }
    }
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'),
                          'proguard-rules.pro'
            signingConfig signingConfigs.release
        }
    }
}
```

`keystore.properties`：

```properties
storeFile=../keys/release.jks
storePassword=...
keyAlias=release
keyPassword=...
```

## 3. 构建并验证

```sh
bash ~/.config/opencode/skills/android-build/scripts/build.sh . release
```

然后：

```sh
APK=app/build/outputs/apk/release/app-release.apk
$HOME/toolchain/android-sdk/build-tools/36.0.0/apksigner verify --print-certs "$APK" || true
sha256sum "$APK"
```

`apksigner` 可能不在精简的 build-tools 包中；如果是这样，就用 Gradle 的签名
输出，并报告 SHA-256，而不是编造一个验证结果。

## 4. 规则

- 每次发布都要提升 `versionCode` 和 `versionName`。
- debug 和 release 的签名密钥要保持分开。
- 测试 release APK，而不只是 debug：安装它并运行 `android-debug` 技能。
- AAB 只对应用商店有意义；本项目直接分发 APK。
- 不要承诺 Google Play 上架：此应用/工具链使用侧载类能力以及较旧的
  target-SDK 行为。
