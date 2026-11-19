#!/data/data/com.termux/files/usr/bin/bash
# Shared cache paths for Androc. Source it: . env.sh
# HOME is the app-private root, so these survive app updates.

: "${HOME:?HOME is not set}"

export ANDROC_TOOLCHAIN="${ANDROC_TOOLCHAIN:-$HOME/toolchain}"
export ANDROC_GRADLE_HOME="${ANDROC_GRADLE_HOME:-$ANDROC_TOOLCHAIN/gradle-home}"
export ANDROC_M2="${ANDROC_M2:-$ANDROC_TOOLCHAIN/m2}"

# Gradle, Maven and common JVM tools all read these.
export GRADLE_USER_HOME="$ANDROC_GRADLE_HOME"
case " ${MAVEN_OPTS:-} " in
  *" -Dmaven.repo.local="*) ;;
  *) export MAVEN_OPTS="${MAVEN_OPTS:-} -Dmaven.repo.local=$ANDROC_M2" ;;
esac

mkdir -p "$ANDROC_M2" "$ANDROC_GRADLE_HOME" 2>/dev/null || true

# Print once so the agent can see the canonical paths.
if [ "${ANDROC_QUIET:-0}" != "1" ]; then
  echo "[lib-cache] HOME=$HOME"
  echo "[lib-cache] GRADLE_USER_HOME=$GRADLE_USER_HOME"
  echo "[lib-cache] ANDROC_M2=$ANDROC_M2"
fi
