# GitHub Actions: Android builds and releases

This repository has two Android product flavors and builds both from the `android/` Gradle project:

- `gameFull`: packages the official SRB2 game data downloaded for the source version, plus the Android port's own assets.
- `gameNoAssets`: removes the official game-data packs and `models.dat`, while retaining the Android port's own required assets.

Before either workflow builds, `.github/scripts/fetch-srb2-assets.py` reads `SRB2VERSION` from `src/version.h`, downloads the matching `SRB2-v<version>-Full.zip` archive from the official [STJr/SRB2 GitHub release](https://github.com/STJr/SRB2/releases), and extracts the required `srb2.pk3`, `zones.pk3`, `characters.pk3`, and `patch.pk3` files into `android/app/src/main/assets`. It also stages `music.pk3` and `models.dat` when they are present in that release archive. The script checks that every required file exists and is non-empty; the build fails rather than silently producing an incomplete `gameFull` APK.

The Android port's own `android.pk3` and `splash.png` remain supplied by this repository. The upstream game-data files are downloaded during CI and are not committed to this repository. The optional `patch_music.pk3` is not fetched from upstream; it is not part of the required Android game-data set.

To test the extraction logic with a previously downloaded official archive, run `python3 .github/scripts/fetch-srb2-assets.py --archive /path/to/SRB2-v2215-Full.zip` from the repository root.

## Workflows

### Android CI

`.github/workflows/android-ci.yml` runs on pushes and pull requests targeting `port`, and can also be started manually. It builds:

- `assembleGameFullDebug`
- `assembleGameNoAssetsDebug`

Both debug APKs are uploaded as the `srb2-android-debug-apks` workflow artifact for 14 days.

### Android Release APKs

`.github/workflows/android-release.yml` runs when a `v*` tag is pushed or when started manually. It builds both release flavors, verifies the APK signatures, generates `SHA256SUMS.txt`, and attaches the APKs to a GitHub Release.

The release workflow uses a GitHub Actions Environment named `release`. Create it under Settings → Environments, then add the following environment secrets to that environment:

| Secret | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64-encoded contents of the release `.jks` keystore |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore password |
| `ANDROID_KEY_ALIAS` | Alias used when creating the signing key |
| `ANDROID_KEY_PASSWORD` | Password for that key |

Create the signing keystore locally and keep the `.jks` file and its passwords private. Example using a local JDK:

```bash
keytool -genkeypair -v \
  -keystore srb2-release.jks \
  -storetype JKS \
  -alias srb2-release \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000

# Linux
base64 -w 0 srb2-release.jks

# macOS
base64 < srb2-release.jks | tr -d '\n'

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("srb2-release.jks")) | Set-Clipboard
```

Paste the resulting Base64 text into the `ANDROID_KEYSTORE_BASE64` environment secret, and put the corresponding values into the other three environment secrets. Do not commit the keystore or passwords to the repository. Keep a secure backup of the keystore: future app updates must use the same signing key.

For a tag-triggered release, push a version tag such as `v2.2.15`. For a manually triggered release, provide the tag name in the workflow input. The release workflow does not create a new signing key; it requires the configured secrets.

## Build tool versions

The Android project currently uses Android Gradle Plugin `8.13.2`, Gradle `8.13`, JDK `21`, compile SDK `36`, SDK Build Tools `35.0.0`, and NDK `28.0.12433566`. The Gradle wrapper and NDK revision are pinned to these compatible SDK package identifiers.
