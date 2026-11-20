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
| `kernel-opencode` | tar | `files/runtime/<version>/`（opencode + rootfs） |
| `android` | tar | `files/packs/android/<version>/` (skills + musl rootfs) |
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

- OC 默认自带 runtime：tar 里包含 `opencode` 和 `rootfs/`（Alpine musl + bash/git/python/node）。
- `archive` 是 tar.xz；`installed.sha256` 是**未压缩 tar** 的 SHA-256。
- 不做增量：`delta` 始终为 null，App 每次下载全量包。

## Publishing flow

1. `scripts/build-opencode-bundle.py` resolves the latest stable
   `anomalyco/opencode` release, builds the musl rootfs, and writes one
   `dist/*.tar.xz` (binary + rootfs) — there is no separate runtime pack.
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
