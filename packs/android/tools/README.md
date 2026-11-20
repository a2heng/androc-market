# Android build-tools helper jar

`core-lambda-stubs.jar` is taken from Android SDK Build-Tools 34.0.0
(`$ANDROID_HOME/build-tools/34.0.0/core-lambda-stubs.jar`).

Android Gradle Plugin requires this jar when desugaring Java lambdas. The
aarch64 build-tools package from `lzhiyong/android-sdk-tools` ships only the
native binaries, so we vendor this small platform-independent jar and add it to
the offline `build-tools/35.0.2` directory.

It is part of the Android SDK, distributed under the Android SDK License /
Apache-2.0 terms. See the upstream `NOTICE.txt` in the Android SDK build-tools
package.
