"""build.py – Build TXRACT for macOS + Windows."""

from __future__ import annotations

import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path


APP_NAME     = "TXRACT"
APP_VERSION  = "1.0.0"
BUNDLE_ID    = "com.txract.txract"
PROJECT_ROOT = Path(__file__).parent.resolve()
ENTRY_POINT  = PROJECT_ROOT / "main.py"
MACOS_MIN    = "12.0"

DATA_DIRS = [("gui", "gui"), ("core", "core")]

COLLECT_ALL_PACKAGES = [
    "cv2", "rapidocr_onnxruntime", "onnxruntime",
    "pytesseract", "ezdxf", "fitz", "PIL",
]

COPY_METADATA_PACKAGES = [
    "opencv-python", "rapidocr-onnxruntime", "onnxruntime",
    "pytesseract", "pymupdf", "Pillow", "ezdxf", "numpy",
]

HIDDEN_IMPORTS = [
    "PIL._tkinter_finder", "PIL.Image", "cv2",
    "ezdxf", "ezdxf.enums", "numpy",
    "rapidocr_onnxruntime", "onnxruntime",
    "pytesseract", "fitz",
]


def banner(msg):
    print("\n" + "=" * 60)
    print("  " + msg)
    print("=" * 60 + "\n")


def run(cmd, env=None):
    print(">> " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        print("[X] Command failed (exit {})".format(r.returncode))
        sys.exit(r.returncode)


def clean_artefacts():
    for folder in ("build", "dist", "installer_root"):
        p = PROJECT_ROOT / folder
        if p.exists():
            shutil.rmtree(p)
            print("[--] Removed: {}".format(p))
    spec = PROJECT_ROOT / (APP_NAME + ".spec")
    if spec.exists():
        spec.unlink()


def find_tesseract():
    binary = None
    tessdata = None
    system = platform.system()

    try:
        import pytesseract
        cmd = pytesseract.pytesseract.tesseract_cmd
        if cmd and Path(cmd).exists():
            binary = Path(cmd)
    except Exception:
        pass

    if not binary:
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            if system == "Windows":
                c = Path(conda_prefix) / "Library" / "bin" / "tesseract.exe"
            else:
                c = Path(conda_prefix) / "bin" / "tesseract"
            if c.exists():
                binary = c

    if not binary:
        cands = []
        if system == "Windows":
            cands = [Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")]
        elif system == "Darwin":
            cands = [Path("/opt/homebrew/bin/tesseract"),
                     Path("/usr/local/bin/tesseract")]
        else:
            cands = [Path("/usr/bin/tesseract")]
        for c in cands:
            if c.exists():
                binary = c
                break

    tp = os.environ.get("TESSDATA_PREFIX")
    if tp and Path(tp).is_dir():
        tessdata = Path(tp)
    else:
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            if system == "Windows":
                c = Path(conda_prefix) / "Library" / "share" / "tessdata"
            else:
                c = Path(conda_prefix) / "share" / "tessdata"
            if c.is_dir():
                tessdata = c

    return binary, tessdata


def build(debug=False, skip_clean=False):
    system = platform.system()
    banner("Building {} v{} | {} | Python {}".format(
        APP_NAME, APP_VERSION, system, sys.version.split()[0]))

    if not ENTRY_POINT.exists():
        print("[X] Entry point not found: {}".format(ENTRY_POINT))
        sys.exit(1)

    if not skip_clean:
        clean_artefacts()

    tess_bin, tess_data = find_tesseract()
    if tess_bin:
        print("[OK] Tesseract: {}".format(tess_bin))
    else:
        print("[!!] Tesseract not found")
    if tess_data:
        print("[OK] Tessdata: {}".format(tess_data))
    else:
        print("[!!] Tessdata not found")

    sep = os.pathsep
    args = [sys.executable, "-m", "PyInstaller",
            "--noconfirm", "--clean",
            "--name={}".format(APP_NAME), "--onedir"]
    args.append("--console" if debug else "--windowed")

    for src, dst in DATA_DIRS:
        if (PROJECT_ROOT / src).exists():
            args += ["--add-data", "{}{}{}".format(src, sep, dst)]

    if tess_bin:
        args += ["--add-binary", "{}{}.".format(tess_bin, sep)]
    if tess_data:
        args += ["--add-data", "{}{}tessdata".format(tess_data, sep)]

    for pkg in COLLECT_ALL_PACKAGES:
        args += ["--collect-all", pkg]
    for pkg in COPY_METADATA_PACKAGES:
        args += ["--copy-metadata", pkg]
    for imp in HIDDEN_IMPORTS:
        args += ["--hidden-import", imp]

    if system == "Darwin":
        args += ["--osx-bundle-identifier", BUNDLE_ID]

    args.append(str(ENTRY_POINT))

    env = os.environ.copy()
    if system == "Darwin":
        env["MACOSX_DEPLOYMENT_TARGET"] = MACOS_MIN

    run(args, env=env)

    if system == "Darwin":
        output = PROJECT_ROOT / "dist" / (APP_NAME + ".app")
        plist = output / "Contents" / "Info.plist"
        if plist.exists():
            subprocess.run(["/usr/libexec/PlistBuddy", "-c",
                            "Set :LSMinimumSystemVersion " + MACOS_MIN,
                            str(plist)], check=False)
            subprocess.run(["/usr/libexec/PlistBuddy", "-c",
                            "Add :LSMinimumSystemVersion string " + MACOS_MIN,
                            str(plist)], check=False)
    else:
        output = PROJECT_ROOT / "dist" / APP_NAME

    if output.exists():
        size = sum(f.stat().st_size for f in output.rglob("*")
                   if f.is_file()) / (1024 * 1024)
        banner("[DONE] Built: {} ({:.1f} MB)".format(
            output.relative_to(PROJECT_ROOT), size))
    else:
        print("[X] Output not found: {}".format(output))
        sys.exit(1)


def build_macos_pkg():
    app_path = PROJECT_ROOT / "dist" / (APP_NAME + ".app")
    if not app_path.exists():
        return
    banner("Creating macOS .pkg")
    subprocess.run(["xattr", "-cr", str(app_path)], check=False)

    root_dir = PROJECT_ROOT / "installer_root"
    if root_dir.exists():
        shutil.rmtree(root_dir)
    apps = root_dir / "Applications"
    apps.mkdir(parents=True)
    shutil.copytree(app_path, apps / (APP_NAME + ".app"), symlinks=True)

    comp = PROJECT_ROOT / "dist" / (APP_NAME + "-component.pkg")
    final = PROJECT_ROOT / "dist" / "{}-{}.pkg".format(APP_NAME, APP_VERSION)

    run(["pkgbuild", "--root", str(root_dir),
         "--identifier", BUNDLE_ID,
         "--version", APP_VERSION,
         "--install-location", "/",
         "--min-os-version", MACOS_MIN,
         str(comp)])

    run(["productbuild", "--package", str(comp), str(final)])

    shutil.rmtree(root_dir)
    comp.unlink()
    size = final.stat().st_size / (1024 * 1024)
    banner("[DONE] Installer: {} ({:.1f} MB)".format(final.name, size))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--debug", action="store_true")
    p.add_argument("--skip-clean", action="store_true")
    p.add_argument("--no-installer", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    print("=" * 60)
    print("  TXRACT Build Script Starting")
    print("=" * 60)

    args = parse_args()

    try:
        build(debug=args.debug, skip_clean=args.skip_clean)

        if not args.no_installer and platform.system() == "Darwin":
            build_macos_pkg()

        print("\n" + "=" * 60)
        print("  BUILD COMPLETE - check dist/ folder")
        print("=" * 60 + "\n")

    except Exception as e:
        import traceback
        print("\n[X] BUILD FAILED")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        sys.exit(1)