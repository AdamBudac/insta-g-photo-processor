# Insta G Photo Processor

**Version 1.0.0** · Windows desktop application · Python / PySide6

[English](./README.md) · [Slovenčina](./README-sk.md) · [Čeština](./README-cz.md)

Prepare photos for Instagram on your own computer. Crop a photo without changing its source, split a panorama into adjoining carousel tiles, or extend a portrait with a blurred or solid background. The app preserves the original foreground pixel scale during export and requires no account, cloud service or Instagram connection.

**Just want to use the EXE?** Read the user guide: [English](./README-user.md), [Slovenčina](./README-user-sk.md), [Čeština](./README-user-cz.md). Download `InstaGPhotoProcessor.exe` from this repository's Releases assets. Python and separate HEIC codecs are bundled. The same guides appear in the app's scrollable Help window and on the [presentation website](https://adambudac.github.io/insta-g-photo-processor/).

## Features

- **Carousel / Split:** 2–20 adjoining tiles ordered left to right, with aspect ratios from 3:4 to 16:9 and an automatic ratio option.
- **Expand canvas:** one photo with padding, a blurred background, or a solid RGB color. An eyedropper and up to five distinct dominant colors help choose a background.
- **Direct crop handles:** crop on the photo's edges and corners. The full original remains visible beneath a dark overlay; restore excluded pixels by dragging outward or using Reset crop.
- **Fit / Padding and Fill / Crop:** Fit keeps the entire chosen input; Fill explicitly permits additional cropping. Neither resizes foreground pixels.
- **Responsive preview:** preview zoom, panning, composition guides and native source detail rendered for the visible viewport and display scaling.
- **Batch workflow:** independent checkboxes, per-photo settings, clear imported/prepared/exported/failed states, cancellable export and a result summary.
- **JPEG, PNG and HEIC/HEIF input**, including supported HDR sources. Preview is always SDR; compatible HDR input can retain HDR or be converted to SDR.
- **English, Slovak and Czech**, plus System, Light and Dark appearance. All processing and saved state stay local.

## Requirements and dependencies

The packaged application targets **Windows x64**. The tested environment is **Windows 11 x64 with Python 3.13**; Windows 10 and a clean Windows virtual machine have not been separately verified. Developing from source requires **Python 3.12+** and a project-local virtual environment.

| Package | Declared range | Purpose |
| --- | --- | --- |
| PySide6 | `>=6.8,<7` | Qt desktop interface |
| Pillow | `>=11,<13` | SDR image processing and JPEG/PNG |
| pillow-heif | `>=1,<2` | HEIC/HEIF support |
| NumPy | `>=2.2,<3` | Pixel arrays and HDR processing |
| imagecodecs | `>=2026.10.10` | HDR JPEG and color codecs |
| PyInstaller | `>=6.11,<7` | Windows one-file build; development dependency |
| pytest / pytest-qt / Ruff | See project configuration | Tests and lint; development dependencies |

Dependencies are declared in [pyproject.toml](./pyproject.toml) and [requirements.txt](./requirements.txt); [requirements-dev.txt](./requirements-dev.txt) adds the development tools. [requirements-lock.txt](./requirements-lock.txt) records the exact verified environment and [uv.lock](./uv.lock) is available for uv. Native codec availability can constrain which Python versions have usable wheels.

## Install and run from source

Clone the repository, open PowerShell in its root folder, then run:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe run_app.py --data-dir .dev-data
```

The explicit development data directory keeps your normal saved session separate. Without `--data-dir`, the app uses the actual Windows Documents folder. You can also pass image paths on the command line. The installed entry point is `insta-g-photo-processor`; the Python module remains `insta_g`.

Open [insta-g-photo-processor.code-workspace](./insta-g-photo-processor.code-workspace) in VS Code for the configured interpreter and the Run application, Run tests and Build Windows EXE [tasks](./.vscode/tasks.json).

## Test and lint

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check insta_g scripts tests run_app.py
.\.venv\Scripts\python.exe run_app.py --smoke-test .test-artifacts/source-smoke.json
```

Tests use generated images, temporary directories, real HEIC encoding/decoding and a licensed small HDR fixture. They do not alter personal photos or the normal Documents session. Separate simultaneous pytest processes must use different `--basetemp` directories.

The optional large-image test is disabled by default:

```powershell
$env:INSTA_G_TEST_LARGE = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_large_images.py -q
Remove-Item Env:INSTA_G_TEST_LARGE
```

Smoke tests write a JSON report and a screenshot without opening normal saved state. Success requires exit code 0 and `"ok": true`. `--smoke-hdr-dir` optionally checks additional HDR fixtures read-only.

## Build a Windows EXE

Run the build **on Windows** and close an older copy of the target EXE first:

```powershell
.\.venv\Scripts\python.exe scripts/build.py
Start-Process -FilePath .\dist\InstaGPhotoProcessor.exe -ArgumentList '--smoke-test','.test-artifacts/frozen-smoke.json' -WindowStyle Hidden -Wait
```

[scripts/build.py](./scripts/build.py) creates `dist/InstaGPhotoProcessor.exe` with Qt's platform plugin, native HEIF DLLs, HDR/color codecs and all three user guides. `--console` enables a debugging console; `--dist-dir` selects another output directory. The packaged smoke report must also contain `"frozen": true`; a successful build alone does not prove that HEIC import works. Bit-identical builds are not guaranteed.

## Data and safety

A new installation stores `session.json` and `preferences.json` under `<actual Windows Documents>/insta-g-photo-processor/`. The default `Export` subfolder is created during first-run setup only. A deleted configured export destination must be chosen again in Preferences.

Each photo keeps its own settings. Session schema 6 includes the crop, readiness, export snapshot and paths, not copies of the source images. Writes run serially off the GUI thread and use atomic replacement; closing waits for pending writes. Read/write errors are shown. Older session schemas 1–5 migrate with a backup of the original bytes, and damaged saved state is preserved before recovery.

Source images are never overwritten. Existing export files receive unique names instead of being replaced. Failure or cancellation removes only newly created files from the unfinished photo's series; completed series remain. Removing a library entry does not delete disk files. Blue Imported photos are skipped by both export actions until their current preview has been shown successfully.

## Image behavior and limits

- Export keeps foreground pixels at **1:1 scale**. Fit adds canvas; Fill crops. There is no output resize control. Whole-pixel rounding can change the canvas or crop by a few pixels.
- Crop coordinates refer to oriented original pixels. The crop is the input for geometry, positioning and background sampling. Retained percentage compares the visible foreground with the **full original**, including input crop and Fill cropping.
- SDR export is **sRGB JPEG quality 99**, with no original EXIF/GPS metadata. Quality 99 is an encoder setting, not a percentage of retained data. PNG transparency is flattened and EXIF orientation is respected.
- Supported HDR includes valid Ultra HDR/Apple HDR JPEG gain maps, supported Apple/ISO HEIC gain maps and 10/12-bit PQ/HLG HEIC with known color metadata. Unsupported or damaged HDR is rejected explicitly. Preview is always SDR.
- HDR-to-SDR files use `_SDR`; retained-HDR files use `_HDR`. HDR JPEG outputs use an ISO gain map; HDR HEIC outputs use 10-bit PQ/BT.2020. Original HDR representation may change during re-encoding.
- There is **no fixed 80 MP limit**. Export renders one tile at a time and checks available RAM. SDR JPEG permits at most **65,500 px per tile edge**; the bundled HDR JPEG codec permits **8,192 px per edge**.
- The quick preview is at most **2048 px** on its longest edge. Native detail is sized for the physical viewport, including device pixel ratio, and uses a memory budget of 40% of currently available RAM. The app reports when only the reduced preview is available.
- Blur backgrounds may use a reduced-resolution raster. Instagram may resize or recompress uploads, and its accepted aspect ratios can change. The app does not upload or promise identical rendering on every HDR device.

Detailed color decisions, measurement conditions and source links are in [technical research](./docs/RESEARCH.md).

## Generated files and cleanup

The ignored `.pytest_cache/` and `.pytest-tmp*/` directories are disposable after tests stop; pytest recreates them. `.dev-data/` is the separate session used by the development launch task: deleting it resets that development session. `.test-artifacts/` holds historical reports, screenshots, benchmarks and optional external HDR samples; it can be removed when those files are no longer needed. Standard tests use their own temporary data and the versioned [HDR fixture](./tests/fixtures/hdr/). None of these directories is needed to run the packaged app.

`insta_g/` is the Python package in the current flat layout. A future src layout would use `src/insta_g/`, retaining the package name and imports.

## Project layout and website

| Location | Responsibility |
| --- | --- |
| [insta_g/core/](./insta_g/core/) | Models, geometry, codecs, processing and export; no GUI dependency |
| [insta_g/gui/](./insta_g/gui/) | Main window, widgets and workers |
| [persistence.py](./insta_g/persistence.py), [preferences.py](./insta_g/preferences.py) | Versioned session and global preferences |
| [i18n.py](./insta_g/i18n.py) | Application translations |
| [index.html](./index.html), [docs/assets/](./docs/assets/) | Static presentation website; no build step |
| [README-user.md](./README-user.md), [README-user-sk.md](./README-user-sk.md), [README-user-cz.md](./README-user-cz.md) | Canonical user guides shared by the app and website |

The website switches EN/SK/CS instantly in JavaScript without reloading, supports System/Light/Dark appearance, and loads the selected user guide directly from these Markdown files.

## Status, contributions and licensing

Verification of the website and documentation delivery, completed 12 November 2026: **651 passed, 1 skipped** in the application suite; **14 browser scenarios passed**, including instant language changes, shared guides, themes, keyboard access and responsive layouts from 320 to 1440 px. Source and the rebuilt Windows EXE passed **13/13 smoke checks**. The optional 84 MP test was not repeated for this delivery. Detailed evidence and limits are in the [implementation plan](./docs/IMPLEMENTATION_PLAN.md); delivered changes are in the [changelog](./CHANGELOG.md).

For a bug report, include the app version, Windows version, reproduction steps, expected behavior and the visible error. Use generated or shareable sample images. See [AGENTS.md](./AGENTS.md) for contributor automation rules. The project is intended for public open-source development; a project-wide license has not yet been selected, so this repository currently makes no additional license grant.
