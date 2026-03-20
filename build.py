#!/usr/bin/env python
"""Build gandiva standalone binary with Nuitka."""

import argparse
import platform
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Build gandiva with Nuitka")
    parser.add_argument("-j", "--jobs", type=int, default=None,
                        help="Number of parallel compilation jobs (default: all cores)")
    args = parser.parse_args()

    # Ensure nuitka is installed
    subprocess.check_call(
        ["uv", "pip", "install", "nuitka", "ordered-set", "zstandard"],
    )

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--output-dir=build",
        "--enable-plugin=pyqt6",
        "--include-qt-plugins=sensible",
        "--include-package=libaditya",
        "--include-package-data=libaditya",
        "--include-package-data=gandiva",
        "--follow-imports",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=pip",
        "--nofollow-import-to=distutils",
    ]

    if args.jobs:
        cmd.append(f"--jobs={args.jobs}")

    if platform.system() == "Darwin":
        cmd.append("--macos-create-app-bundle")
        cmd.append("--macos-app-name=Gandiva")

    if platform.system() == "Windows":
        cmd.append("--windows-console-mode=disable")

    cmd.append("gandiva/app.py")

    print("Running:", " ".join(cmd))
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
