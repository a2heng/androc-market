# Androc Market

Signed index + release assets for Androc components.

- `index.json` — current stable index (detached Ed25519 signature in `index.json.sig`)
- `keys/` — public key(s)
- `schema/index.schema.json`
- `scripts/build-opencode-pack.py` — build the OpenCode pack + delta from the official release
- `.github/workflows/opencode.yml` — daily official-release check

## Contract

The app downloads `index.json` and `index.json.sig`, verifies the signature over
the **exact file bytes**, then parses JSON. It never trusts an unsigned index.

Pack types:

| id | kind | install |
|---|---|---|
| `kernel-opencode` | single-file | `files/runtime/<version>/opencode` |
| `android` | tar | `files/packs/android/<version>/` (skills + Termux bionic rootfs) |
| `runtime-core` (planned) | tar | musl/Alpine rootfs for language & writing plugins |
| future `lang-*` / `writing` | tar | `files/packs/<id>/<version>/` |

Directory packs live under `packs/<id>/`:

```text
packs/android/
├─ pack.json        # id / name / version / category / summary
└─ skills/          # android-* skills
```

`scripts/build-pack.py --all --out dist` builds every directory pack into a
deterministic `tar.xz`, merges the entries into `index.json`, and signs the
exact bytes. `.github/workflows/packs.yml` publishes the archives and commits
the signed index.

For `kernel-opencode`:

- `archive` is an xz-compressed raw ELF (`xz -9`) for pure-Java, all-device decoding.
- `installed.sha256` is the SHA-256 of the **raw** ELF.
- `delta` is temporarily disabled: zstd patches need a native decoder. A pure-Java block delta is the next step.
- The app always verifies the resulting raw SHA-256 before switching versions.

## Publishing flow

1. `scripts/build-opencode-pack.py` resolves the latest stable
   `anomalyco/opencode` release, verifies the official `SHA256SUMS`/API digest,
   extracts `opencode`, and writes `dist/*.zst`.
2. It writes `index.json`, signs the exact bytes with Ed25519, and writes
   `index.json.sig`.
3. CI creates the release `kernel-opencode-<version>-1` with the pack, delta,
   index and signature, then commits the index.

## Local build

```sh
python3 -m pip install cryptography
python3 scripts/build-opencode-pack.py --version latest --out dist
```

The signing key is `.keys/market-signing-key.pem` (gitignored). CI supplies it
as the `MARKET_SIGNING_KEY` secret.
