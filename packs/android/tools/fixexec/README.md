# fixexec

LD_PRELOAD shim for JVM on Android/proot: Android denies `mprotect(RW -> RWX)`,
so HotSpot dies with "Failed to mark memory page as executable". The shim
remaps the region in place as RWX (anonymous RWX `mmap` is allowed).

- Upstream: https://github.com/lidanthedev/Acode-fixexec
- License: GPL-3.0-or-later (see `LICENSE`); source vendored here.
- Built in CI for `aarch64-linux-musl` with `zig cc` into
  `/usr/local/lib/fixexec.so`.
