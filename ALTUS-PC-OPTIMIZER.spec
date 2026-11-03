# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/resources', 'src/resources')],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'psutil', 'platformdirs'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'matplotlib', 'pandas', 'cv2', 'torch', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtNetworkAuth', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.Qt3DCore', 'PySide6.QtSensors', 'PySide6.QtPositioning', 'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtSerialPort', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ALTUS-PC-OPTIMIZER',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src/resources/icons/app.ico'],
)
