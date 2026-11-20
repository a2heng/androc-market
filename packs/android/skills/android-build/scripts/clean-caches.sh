#!/bin/sh
# 清理 Androc 构建缓存。
#   clean-caches.sh            只清临时文件
#   clean-caches.sh --builds   再清 workspace/*/build 和 .gradle
#   clean-caches.sh --all      再清共享依赖缓存
set -eu
: "${HOME:?HOME is not set}"
BUILDS=0
ALL=0
for arg in "$@"; do
  case "$arg" in
    --builds) BUILDS=1 ;;
    --all) ALL=1; BUILDS=1 ;;
    -h|--help) echo "usage: $0 [--builds] [--all]"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

show() {
  echo "== sizes"
  for p in "$HOME/.gradle" "$HOME/.cache" "$HOME/.local/share/opencode" "$HOME/workspace"; do
    [ -e "$p" ] && du -sh "$p" 2>/dev/null || true
  done
}

show
rm -rf "$HOME/.cache/tmp"/* 2>/dev/null || true
rm -rf "$HOME/.gradle/daemon" "$HOME/.gradle/.tmp" 2>/dev/null || true

if [ "$BUILDS" = 1 ]; then
  echo "== removing project build outputs under $HOME/workspace"
  find "$HOME/workspace" -maxdepth 4 -type d \( -name build -o -name .gradle \) \
    -prune -exec rm -rf {} + 2>/dev/null || true
fi

if [ "$ALL" = 1 ]; then
  echo "== removing shared dependency caches (re-downloaded on next build)"
  rm -rf "$HOME/.gradle/caches" 2>/dev/null || true
fi

echo
show
