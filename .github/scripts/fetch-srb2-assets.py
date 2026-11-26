#!/usr/bin/env python3
"""Fetch the matching official SRB2 game-data archive and stage Android assets."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
VERSION_HEADER = ROOT / "src" / "version.h"
ASSET_DIRECTORY = ROOT / "android" / "app" / "src" / "main" / "assets"
REQUIRED_ASSETS = ("srb2.pk3", "zones.pk3", "characters.pk3", "music.pk3")
OPTIONAL_ASSETS = ("models.dat")
CHUNK_SIZE = 1024 * 1024


def read_game_version() -> str:
    text = VERSION_HEADER.read_text(encoding="utf-8")
    match = re.search(r'^\s*#define\s+SRB2VERSION\s+"([0-9]+(?:\.[0-9]+)+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not read SRB2VERSION from {VERSION_HEADER}")
    return match.group(1)


def download_archive(version: str, destination: Path) -> None:
    compact_version = version.replace(".", "")
    release_tag = f"SRB2_release_{version}"
    filename = f"SRB2-v{compact_version}-Full.zip"
    url = f"https://github.com/STJr/SRB2/releases/download/{release_tag}/{filename}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SRB2-Android-GitHub-Actions", "Accept": "application/octet-stream"},
    )

    print(f"Downloading official SRB2 {version} game data:")
    print(url)
    try:
        with urllib.request.urlopen(request, timeout=90) as response, destination.open("wb") as output:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                output.write(chunk)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"Could not download the official SRB2 {version} full-data archive "
            f"(HTTP {error.code}). Check that this version has a matching upstream release."
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not download official SRB2 game data: {error.reason}") from error

    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("The official game-data download was empty.")


def extract_assets(archive_path: Path) -> None:
    ASSET_DIRECTORY.mkdir(parents=True, exist_ok=True)
    # Avoid retaining stale optional assets if the upstream archive changes.
    for asset_name in REQUIRED_ASSETS + OPTIONAL_ASSETS:
        (ASSET_DIRECTORY / asset_name).unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = REQUIRED_ASSETS + OPTIONAL_ASSETS
            staged = []
            for asset_name in names:
                matches = [
                    info for info in archive.infolist()
                    if not info.is_dir() and PurePosixPath(info.filename).name.lower() == asset_name.lower()
                ]
                if not matches:
                    if asset_name in REQUIRED_ASSETS:
                        raise RuntimeError(f"Official SRB2 archive is missing required file: {asset_name}")
                    print(f"Optional upstream asset not present: {asset_name}")
                    continue
                if len(matches) != 1:
                    raise RuntimeError(
                        f"Expected one {asset_name} in the official archive, found {len(matches)}."
                    )

                info = matches[0]
                destination = ASSET_DIRECTORY / asset_name
                with archive.open(info, "r") as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output, length=CHUNK_SIZE)
                if destination.stat().st_size != info.file_size or destination.stat().st_size == 0:
                    raise RuntimeError(f"Extracted {asset_name} is incomplete or empty.")
                staged.append(asset_name)

    except zipfile.BadZipFile as error:
        raise RuntimeError("The downloaded SRB2 game-data file is not a valid ZIP archive.") from error

    print("Staged Android game data:")
    for asset_name in staged:
        print(f"  - {asset_name}")
    print("The Android port's android.pk3 and splash.png remain supplied by this repository.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        help="Use an already-downloaded Full.zip instead of downloading the official release.",
    )
    args = parser.parse_args()

    try:
        version = read_game_version()
        if args.archive:
            archive_path = args.archive.resolve()
            if not archive_path.is_file():
                raise RuntimeError(f"Archive does not exist: {archive_path}")
            print(f"Using supplied SRB2 asset archive for version {version}: {archive_path}")
            extract_assets(archive_path)
        else:
            with tempfile.TemporaryDirectory(prefix="srb2-assets-") as temporary_directory:
                archive_path = Path(temporary_directory) / "srb2-full.zip"
                download_archive(version, archive_path)
                extract_assets(archive_path)
    except (OSError, RuntimeError, zipfile.LargeZipFile) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
