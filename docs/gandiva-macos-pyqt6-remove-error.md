# Fix: Nuitka PyQt6 macOS fatal error

Nuitka 4.0.7 treats PyQt6 on macOS as a fatal error:

```
FATAL: options-nanny: Using module 'PyQt6' (version 6.10.2) with incomplete support due to condition 'macos and use_pyqt6': PyQt6 on macOS is not supported, use PySide6 instead
```

## Fix

Edit the nuitka options-nanny config in your venv:

```
.venv/lib/python3.13/site-packages/nuitka/plugins/standard/standard.nuitka-package.config.yml
```

Find (around line 5105):

```yaml
      - description: 'PyQt6 on macOS is not supported, use PySide6 instead'
        support_info: 'error'
        when: 'macos and use_pyqt6'
```

Change `'error'` to `'warning'`:

```yaml
      - description: 'PyQt6 on macOS is not supported, use PySide6 instead'
        support_info: 'warning'
        when: 'macos and use_pyqt6'
```

## Note

This change lives inside the venv and will be reset if nuitka is reinstalled. Reapply after `uv pip install nuitka`.
