#!/bin/sh
# Build an Android project inside the musl/Alpine android pack.
#
# Usage: build.sh <project-dir> [debug|release] [gradle-task]
#
# Layout comes from the pack, not from Termux:
#   /opt/android-sdk, /opt/gradle/gradle-9.9.0, /usr/lib/jvm/java-21-openjdk
# The JVM needs the fixexec LD_PRELOAD shim; /opt/androc/env.sh exports it.
set -eu

PROJECT="${1:-$PWD}"
VARIANT="${2:-debug}"
TASK="${3:-}"

: "${HOME:?HOME is not set}"

if [ -f /opt/androc/env.sh ]; then
  . /opt/androc/env.sh
fi

SDK="${ANDROID_HOME:-/opt/android-sdk}"
BT_VERSION="36.0.0"
JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk}"
AAPT2="$SDK/build-tools/$BT_VERSION/aapt2"
GRADLE_HOME="/opt/gradle/gradle-9.9.0"
GRADLE_MAIN="$GRADLE_HOME/lib/gradle-gradle-cli-main-9.9.0.jar"

if [ -z "$TASK" ]; then
  case "$VARIANT" in
    debug|Debug) TASK="assembleDebug" ;;
    release|Release) TASK="assembleRelease" ;;
    *) TASK="assemble$(printf '%s' "$VARIANT" | cut -c1 | tr '[:lower:]' '[:upper:]')$(printf '%s' "$VARIANT" | cut -c2-)" ;;
  esac
fi

if [ ! -x "$JAVA_HOME/bin/java" ]; then
  echo "[android-build] JDK missing at $JAVA_HOME" >&2
  exit 2
fi
if [ ! -x "$AAPT2" ]; then
  echo "[android-build] aapt2 missing at $AAPT2" >&2
  exit 2
fi
if [ ! -f "$SDK/platforms/android-36/android.jar" ]; then
  echo "[android-build] platform android-36 missing under $SDK/platforms" >&2
  exit 2
fi
if [ ! -f "$GRADLE_MAIN" ]; then
  echo "[android-build] Gradle 9.9.0 missing at $GRADLE_HOME" >&2
  exit 2
fi

GRADLE_TMP="$HOME/.cache/tmp"
mkdir -p "$GRADLE_TMP" "$HOME/.cache" 2>/dev/null || true
export TMPDIR="$GRADLE_TMP"

cd "$PROJECT"
# 用包内 Gradle 直接启动 GradleMain，不需要项目的 gradlew。

# AGP only needs this when the project has no local.properties of its own.
if [ ! -f ./local.properties ]; then
  printf 'sdk.dir=%s\n' "$SDK" > ./local.properties
fi

# AGP 9 pulls its own x86_64 aapt2 from Maven: force the pack's binary.
INIT="$HOME/.cache/androc-init.gradle"
cat > "$INIT" <<'EOF'
allprojects { p ->
    ['com.android.application', 'com.android.library'].each { id ->
        p.plugins.withId(id) {
            def a = p.extensions.findByName('android')
            if (a != null) {
                a.buildToolsVersion = '36.0.0'
            }
        }
    }
}
EOF

OFFLINE=""
if [ "${OC_BUILD_ONLINE:-1}" = "0" ]; then
  OFFLINE="--offline"
fi

echo "[android-build] project : $PWD"
echo "[android-build] task    : $TASK"
echo "[android-build] java    : $JAVA_HOME"
echo "[android-build] sdk     : $SDK"
echo "[android-build] aapt2   : $AAPT2"
echo "[android-build] gradle  : $GRADLE_HOME ${OFFLINE:-online}"

BUILD_LOG="$HOME/.cache/androc-build.log"
mkdir -p "$HOME/.cache" 2>/dev/null || true
set +e
"$JAVA_HOME/bin/java" \
  -Djava.io.tmpdir="$GRADLE_TMP" \
  -classpath "$GRADLE_MAIN" \
  org.gradle.launcher.GradleMain \
  --no-daemon --console=plain $OFFLINE \
  -I "$INIT" \
  -Dorg.gradle.jvmargs="-Xmx3g -XX:MaxMetaspaceSize=1g -Dfile.encoding=UTF-8 -Djava.io.tmpdir=$GRADLE_TMP" \
  -Pandroid.suppressUnsupportedCompileSdk=36 \
  -Pandroid.aapt2FromMavenOverride="$AAPT2" \
  "$TASK" 2>&1 | tee "$BUILD_LOG"
RC=$?
set -e
exit $RC
