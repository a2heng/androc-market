# fixexec

LD_PRELOAD shim for JVM on Android/proot: Android 只允许匿名 `mmap` 直接 RWX，`mprotect(RW -> RWX)` 会被拒绝。
该 shim 在原地址重映射为 RWX，JVM 即可正常启动。

- Upstream: https://github.com/lidanthedev/Acode-fixexec
- License: GPL-3.0-or-later (see `LICENSE`); source vendored here.
- Built in CI for `aarch64-linux-musl` with `zig cc` into
  `/usr/local/lib/fixexec.so`.
