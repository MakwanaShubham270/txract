# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = [('gui', 'gui'), ('core', 'core'), ('/opt/anaconda3/envs/txract38/share/tessdata', 'tessdata')]
binaries = [('/opt/anaconda3/envs/txract38/bin/tesseract', '.')]
hiddenimports = ['PIL._tkinter_finder', 'PIL.Image', 'cv2', 'ezdxf', 'ezdxf.enums', 'numpy', 'rapidocr_onnxruntime', 'onnxruntime', 'pytesseract', 'fitz']
datas += copy_metadata('opencv-python')
datas += copy_metadata('rapidocr-onnxruntime')
datas += copy_metadata('onnxruntime')
datas += copy_metadata('pytesseract')
datas += copy_metadata('pymupdf')
datas += copy_metadata('Pillow')
datas += copy_metadata('ezdxf')
datas += copy_metadata('numpy')
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('rapidocr_onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pytesseract')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ezdxf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('fitz')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


block_cipher = None


a = Analysis(
    ['/Users/mac/Desktop/TXRACT/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TXRACT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TXRACT',
)
app = BUNDLE(
    coll,
    name='TXRACT.app',
    icon=None,
    bundle_identifier='com.txract.txract',
)
