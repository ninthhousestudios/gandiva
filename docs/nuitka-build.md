# Building gandiva standalone binaries

gandiva uses [Nuitka](https://nuitka.net) to compile standalone binaries. Each platform must be compiled on that platform — no cross-compilation.

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

Output: `build/app.dist/` (a `.app` bundle will be inside, or use `--macos-create-app-bundle` which `build.py` adds automatically on Darwin)

### Code signing and notarization

Requires an Apple Developer account ($99/year) with a "Developer ID Application" certificate installed in your Keychain.

**1. Find your signing identity:**
```bash
security find-identity -v -p codesigning
```
Look for `Developer ID Application: Your Name (TEAMID)`.

**2. Sign the app bundle:**
```bash
SIGN_ID="Developer ID Application: Your Name (TEAMID)"

codesign \
  --deep \
  --force \
  --options runtime \
  --timestamp \
  --sign "$SIGN_ID" \
  build/Gandiva.app

# Verify
codesign -v build/Gandiva.app
```

**3. Notarize:**
```bash
# Create an app-specific password at https://appleid.apple.com
# (Security > App-Specific Passwords)

# Zip for submission
ditto -c -k --keepParent build/Gandiva.app build/Gandiva.zip

xcrun notarytool submit build/Gandiva.zip \
  --apple-id "your@email.com" \
  --password "<app-specific-password>" \
  --team-id "TEAMID" \
  --wait

# Staple the ticket to the app
xcrun stapler staple build/Gandiva.app
```

**4. Distribute** as `.dmg` or `.zip`. A `.dmg` avoids some quarantine issues:
```bash
hdiutil create -volname Gandiva -srcfolder build/Gandiva.app -ov build/Gandiva.dmg
```

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

## Adding an app icon

Place icon files in `gandiva/assets/`:
- macOS: `icon.icns` (use `iconutil` or an online converter)
- Windows: `icon.ico`

Then add to `build.py`'s cmd list:
```python
if platform.system() == "Darwin":
    cmd.append("--macos-app-icon=gandiva/assets/icon.icns")
if platform.system() == "Windows":
    cmd.append("--windows-icon-from-ico=gandiva/assets/icon.ico")
```

---

## Notes

- First build takes 10-30 minutes. Subsequent builds use Nuitka's cache.
- Binary size will be 200-400MB (Qt + ephemeris data + all deps). Normal for PyQt6.
- PyQt6 support in Nuitka is "experimental" but works for gandiva's use case (no Qt threading).
- If the build fails on Python 3.13, try 3.12 — Nuitka's 3.13 support is still maturing.
