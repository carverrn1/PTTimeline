# -*- mode: python ; coding: utf-8 -*-
#
# PTTimeline.spec
# PyInstaller build spec for PTTEdit, PTTPlot, and PTTView.
#
# Builds three EXEs into a single one-dir output:
#   dist\PTTimeline\
#     pttedit.exe
#     pttplot.exe
#     pttview.exe
#     _internal\        <- shared PyInstaller runtime/support files
#     resources\        <- application icons
#     samples\          <- sample .pttd and .ini data files
#     docs\             <- HTML documentation
#
# Usage:
#   pyinstaller PTTimeline.spec
# Or use build.bat for a clean build.
#
# ─────────────────────────────────────────────────────────────────────────────

import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks import copy_metadata

# Root of the source tree (same directory as this spec file)
ROOT = os.path.dirname(os.path.abspath(SPEC))

# Subdirectories
LIB_DIR       = os.path.join(ROOT, 'lib')
RESOURCES_DIR = os.path.join(ROOT, 'resources')
SAMPLES_DIR   = os.path.join(ROOT, 'samples')
DOCS_DIR      = os.path.join(ROOT, 'docs')

# Package metadata - required for importlib.metadata.version() to work in frozen app.
# configparser and numpy are excluded: configparser is stdlib (no dist-info),
# numpy's metadata is already included by PyInstaller's built-in numpy hook.
METADATAS = []
for _pkg in ['PySide6','pandas','matplotlib','platformdirs','json5','configupdater','odfpy']:
    METADATAS += copy_metadata(_pkg)

# Data files - copied to top-level output dir by build.bat, not bundled here
DATAS = METADATAS

# Hidden imports that PyInstaller may miss
HIDDEN_IMPORTS = [
    'json5',
    'configupdater',
    'platformdirs',
    'matplotlib.backends.backend_pdf',
    'matplotlib.backends.backend_svg',
    'matplotlib.backends.backend_agg',
]

# Common Analysis kwargs
COMMON = dict(
    pathex        = [ROOT, LIB_DIR],
    datas         = DATAS,
    hiddenimports = HIDDEN_IMPORTS,
    hookspath     = [],
    hooksconfig   = {},
    runtime_hooks = [],
    excludes      = [],
    noarchive     = False,
    optimize      = 0,
)

# ─────────────────────────────────────────────────────────────────────────────
# PTTEdit
# ─────────────────────────────────────────────────────────────────────────────

a_edit = Analysis(
    [os.path.join(ROOT, 'pttedit.py')],
    **COMMON,
)

pyz_edit = PYZ(a_edit.pure)

exe_edit = EXE(
    pyz_edit,
    a_edit.scripts,
    [],
    exclude_binaries = True,
    name             = 'pttedit',
    icon             = os.path.join(RESOURCES_DIR, 'PTTEdit.ico'),
    debug            = False,
    bootloader_ignore_signals = False,
    strip            = False,
    upx              = False,
    console          = False,
    disable_windowed_traceback = False,
    version          = 'pttedit.VersionInfo',
)

# ─────────────────────────────────────────────────────────────────────────────
# PTTPlot
# ─────────────────────────────────────────────────────────────────────────────

a_plot = Analysis(
    [os.path.join(ROOT, 'pttplot.py')],
    **COMMON,
)

pyz_plot = PYZ(a_plot.pure)

exe_plot = EXE(
    pyz_plot,
    a_plot.scripts,
    [],
    exclude_binaries = True,
    name             = 'pttplot',
    icon             = os.path.join(RESOURCES_DIR, 'PTTPlot.ico'),
    debug            = False,
    bootloader_ignore_signals = False,
    strip            = False,
    upx              = False,
    console          = False,
    disable_windowed_traceback = False,
    version          = 'pttplot.VersionInfo',
)

# ─────────────────────────────────────────────────────────────────────────────
# PTTView
# ─────────────────────────────────────────────────────────────────────────────

a_view = Analysis(
    [os.path.join(ROOT, 'pttview.py')],
    **COMMON,
)

pyz_view = PYZ(a_view.pure)

exe_view = EXE(
    pyz_view,
    a_view.scripts,
    [],
    exclude_binaries = True,
    name             = 'pttview',
    icon             = os.path.join(RESOURCES_DIR, 'PTTView.ico'),
    debug            = False,
    bootloader_ignore_signals = False,
    strip            = False,
    upx              = False,
    console          = False,
    disable_windowed_traceback = False,
    version          = 'pttview.VersionInfo',
)

# ─────────────────────────────────────────────────────────────────────────────
# COLLECT - merge all three into dist\PTTimeline\
# ─────────────────────────────────────────────────────────────────────────────

coll = COLLECT(
    exe_edit,  a_edit.binaries,  a_edit.datas,
    exe_plot,  a_plot.binaries,  a_plot.datas,
    exe_view,  a_view.binaries,  a_view.datas,
    strip = False,
    upx   = False,
    name  = 'PTTimeline',
)
