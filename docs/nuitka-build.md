# Building gandiva standalone binaries

gandiva uses [Nuitka](https://nuitka.net) to compile standalone binaries. Each platform must be compiled on that platform — no cross-compilation.

## PySide6 migration (2026-03-30)

gandiva was originally built with PyQt6. Nuitka + PyQt6 produces a segfault on macOS (crashes during `sip_api_export_module` → `PyInit_QtWidgets` at dyld initialization). This affects even a minimal `from PyQt6.QtWidgets import QApplication; print("ok")` test binary — confirmed not gandiva-specific.

The fix was migrating from PyQt6 to PySide6. PySide6 is API-compatible with PyQt6. The port involved:

- `from PyQt6.QtWidgets` → `from PySide6.QtWidgets` (and QtCore, QtGui, QtSvg)
- `pyqtSignal` → `Signal`
- `pyqtSlot` → `Slot`
- `pyqtProperty` → `Property`
- `pyproject.toml`: `PyQt6>=6.8` → `PySide6>=6.8`
- `build.py` and `pyproject.toml`: `--enable-plugin=pyqt6` → `--enable-plugin=pyside6`

## libaditya ephemeris path fix

When bundling without Swiss Ephemeris `.se1` files (using Moshier fallback), libaditya's `__init__.py` must not call `swe.set_ephe_path()` on an empty or missing directory. If the path is set but files are missing, swisseph raises an error instead of falling back to Moshier.

The fix in `libaditya/__init__.py`:

```python
# Before (always sets path, breaks if files missing):
swe.set_ephe_path(base_path + "/ephe/")

# After (only sets path if .se1 files exist):
ephe_dir = base_path + "/ephe/"
if os.path.isdir(ephe_dir) and any(f.endswith('.se1') for f in os.listdir(ephe_dir)):
    swe.set_ephe_path(ephe_dir)
```

Without `.se1` files, swisseph uses the Moshier analytical ephemeris automatically. Moshier is less accurate for asteroids and outer planets but fine for traditional planets.

## Nuitka options-nanny PyQt6 error (if using PyQt6)

Nuitka 4.0.7 treats PyQt6 on macOS as a fatal error. If you ever need to build with PyQt6, change `'error'` to `'warning'` in:

```
.venv/lib/python3.13/site-packages/nuitka/plugins/standard/standard.nuitka-package.config.yml
```

Find:
```yaml
- description: 'PyQt6 on macOS is not supported, use PySide6 instead'
  support_info: 'error'
  when: 'macos and use_pyqt6'
```

Change `'error'` to `'warning'`. This resets whenever nuitka is reinstalled.

---

## Linux

### Prerequisites
```bash
sudo pacman -S patchelf    # Arch
# or: sudo apt install patchelf   (Debian/Ubuntu)
# or: sudo dnf install patchelf   (Fedora)
```

### Build
```bash
cd gandiva
source .venv/bin/activate
python build.py
```

Output: `build/app.dist/app`

---

## macOS

### Prerequisites

1. **Xcode Command Line Tools**
   ```bash
   xcode-select --install
   ```

2. **Python 3.13 + uv**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv python install 3.13
   ```

3. **Clone and set up**
   ```bash
   git clone <repo> && cd gandiva
   uv venv && source .venv/bin/activate
   uv add . --dev
   ```

### Build
```bash
python build.py
```

Output: `build/app.app` (a `.app` bundle — `build.py` adds `--macos-create-app-bundle` automatically on Darwin).

### Generating an app icon

Place a source PNG (at least 1024x1024) in `gandiva/assets/`, then:

```bash
mkdir -p /tmp/gandiva.iconset
sips -z 1024 1024 gandiva/assets/prometheus-footer.png --out /tmp/icon_1024.png
for size in 16 32 64 128 256 512; do
  sips -z $size $size /tmp/icon_1024.png --out /tmp/gandiva.iconset/icon_${size}x${size}.png
  sips -z $((size*2)) $((size*2)) /tmp/icon_1024.png --out /tmp/gandiva.iconset/icon_${size}x${size}@2x.png
done
cp /tmp/icon_1024.png /tmp/gandiva.iconset/icon_512x512@2x.png
iconutil -c icns /tmp/gandiva.iconset -o gandiva/assets/gandiva-icon.icns
```

### Delete ephemeris files (optional — use Moshier instead)

If you don't want to bundle the ~60MB of Swiss Ephemeris data files:

```bash
rm -rf build/app.app/Contents/MacOS/libaditya/ephe
```

This only works with the libaditya ephemeris path fix described above.

### Code signing

Requires an Apple Developer account ($99/year) with a "Developer ID Application" certificate installed in your Keychain.

**1. Find your signing identity:**
```bash
security find-identity -v -p codesigning
```
Look for `Developer ID Application: Your Name (TEAMID)`.

**2. Set the identity:**
```bash
export SIGN_ID="Developer ID Application: Your Name (TEAMID)"
```

**3. Sign all Mach-O binaries individually, then the bundle:**

Do NOT use `codesign --deep` — it chokes on non-Mach-O files (like `.se1` ephemeris data) in the `MacOS/` directory.

```bash
# Sign every Mach-O binary inside the bundle
find build/app.app/Contents/MacOS -type f | while read f; do
  if file "$f" | grep -q "Mach-O"; then
    codesign --force --options runtime --timestamp --sign "$SIGN_ID" "$f"
  fi
done

# Sign the bundle itself
codesign --force --options runtime --timestamp --sign "$SIGN_ID" build/app.app

# Verify
codesign -v build/app.app
```

If `.se1` files remain in `MacOS/` and codesign complains, either delete them (see above) or move them to `Contents/Resources/` and symlink back:

```bash
mkdir -p build/app.app/Contents/Resources/ephe
cd build/app.app/Contents
find MacOS/libaditya/ephe -name "*.se1" | while read f; do
  dest="Resources/${f#MacOS/libaditya/}"
  mkdir -p "$(dirname "$dest")"
  mv "$f" "$dest"
  ln -sf "../../../../Resources/${f#MacOS/libaditya/}" "$f"
done
cd -
```

### Notarization

Notarization is Apple's automated malware scan. No human review — usually takes 5-15 minutes. Required for distribution to others (avoids Gatekeeper warnings).

**1. Generate an app-specific password:**
- Go to https://appleid.apple.com
- Sign-In and Security > App-Specific Passwords > Generate
- Use the Apple ID associated with your Developer account

**2. Submit for notarization:**
```bash
ditto -c -k --keepParent build/app.app build/Gandiva.zip

xcrun notarytool submit build/Gandiva.zip \
  --apple-id "your@email.com" \
  --password "<app-specific-password>" \
  --team-id "TEAMID" \
  --wait
```

If it fails, check the log:
```bash
xcrun notarytool log <submission-id> \
  --apple-id "your@email.com" \
  --password "<app-specific-password>" \
  --team-id "TEAMID"
```

Common failure: unsigned binaries inside the bundle. Qt ships framework libraries as bare Mach-O files (no `.dylib` extension) — the `find | file | grep Mach-O` signing loop above handles these.

**3. Staple the notarization ticket:**
```bash
xcrun stapler staple build/app.app
```

**4. Optionally store credentials in Keychain** (avoids pasting passwords):
```bash
xcrun notarytool store-credentials "gandiva-notary" \
  --apple-id "your@email.com" \
  --password "<app-specific-password>" \
  --team-id "TEAMID"

# Then submit with:
xcrun notarytool submit build/Gandiva.zip --keychain-profile "gandiva-notary" --wait
```

### Create and sign the DMG

```bash
hdiutil create -volname Gandiva -srcfolder build/app.app -ov build/Gandiva.dmg
codesign --force --sign "$SIGN_ID" build/Gandiva.dmg
```

### Upload to GitHub Releases

```bash
# Create a new release with the DMG
gh release create v1.0.0 build/Gandiva.dmg \
  --repo your-org/gandiva \
  --title "Gandiva v1.0.0" \
  --notes "macOS arm64 build"

# Or add to an existing release
gh release upload v1.0.0 build/Gandiva.dmg --repo your-org/gandiva --clobber
```

Release assets are hosted by GitHub and never touch git history.

---

## Windows

### Prerequisites

1. **Visual Studio Build Tools 2022** — required for Python 3.13 (MinGW won't work)
   - Download from https://visualstudio.microsoft.com/downloads/
   - Install the **"Desktop development with C++"** workload
   - Ensure **Windows SDK** is checked
   - Restart after install

2. **Python 3.13**
   - Download from https://www.python.org/downloads/windows/
   - Check **"Add Python to PATH"** during install

3. **Clone and set up** (from Command Prompt or PowerShell)
   ```cmd
   git clone <repo>
   cd gandiva
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e .
   pip install -e ..\libaditya
   ```

### Build
```cmd
python build.py
```

Output: `build\app.dist\app.exe`

`build.py` automatically adds `--windows-console-mode=disable` on Windows so no console window appears.

---

## Notes

- First build takes 10-30 minutes. Subsequent builds use Nuitka's cache.
- Binary size will be 200-400MB (Qt + ephemeris data + all deps). Normal for PySide6.
- If the build fails on Python 3.13, try 3.12 — Nuitka's 3.13 support is still maturing.
- `$SIGN_ID` is a shell variable — it resets when you close the terminal. Add `export SIGN_ID="..."` to `~/.zshrc` to persist it.
