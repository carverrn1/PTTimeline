"""
ptt_update_version.py
---------------------
Syncs version information from ptt_appinfo.py (single source of truth)
to the following files:

    pttedit.VersionInfo
    pttplot.VersionInfo
    pttview.VersionInfo
    PTTimeline.iss

Also auto-increments the build number (APP_VERSION_INFO 5th element) in
ptt_appinfo.py itself when a suffix AND a build number are present.

Rules:
  - No suffix (3-element)         -> ptt_appinfo.py left untouched; "v1.0.0"
  - Suffix, no number (4-element) -> ptt_appinfo.py left untouched; "v0.5.0-dev"
  - Suffix + number (5-element)   -> number incremented by 1; "v0.5.0-dev.N"
  - Number wraps past 65535       -> wraps to 1, warning printed

To start numbered builds: manually add the 5th element set to 0 (e.g. (0, 5, 0, "dev", 0)); the first build run will increment it to 1.
To stop numbering: manually remove the 5th element from the tuple.

Invoked as the first step in BUILD_ALL.BAT before PyInstaller runs.

Usage:
    python ptt_update_version.py

All paths are relative to the script's own directory, which must be the
project root (parent of the lib/ folder containing ptt_appinfo.py).
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate project root and import ptt_appinfo
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR    = SCRIPT_DIR / "lib"
sys.path.insert(0, str(LIB_DIR))

try:
    import ptt_appinfo
except ImportError as e:
    print(f"ERROR: Cannot import ptt_appinfo.py from {LIB_DIR}: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Auto-increment build number in ptt_appinfo.py when suffix is present
# ---------------------------------------------------------------------------

def _update_appinfo() -> None:
    """
    Update ptt_appinfo.py in place:
      - APP_DATE is always set to today's date (YYYY-MM-DD).
      - APP_VERSION_INFO build number (5th element) is incremented by 1 only
        when a 5-element tuple (suffix + number) is present.  3-element (no
        suffix) and 4-element (suffix only) tuples are left untouched — APP_DATE
        is still updated in all cases.  To begin a numbered build sequence,
        manually set the 5th element to 0; the first build run increments it to 1.

    Reads and writes the file directly (bypassing .pyc cache) so repeated
    runs within the same Python process always see the current on-disk state.
    """
    appinfo_path = LIB_DIR / "ptt_appinfo.py"
    text         = appinfo_path.read_text(encoding="utf-8")
    today_iso    = datetime.now().strftime("%Y-%m-%d")   # e.g. "2026-03-26"
    # --- APP_DATE (always updated) ---
    m_date = re.search(r'(APP_DATE\s*=\s*")[^"]*(")', text)
    if m_date:
        old_date = m_date.group(0)
        new_date = m_date.group(1) + today_iso + m_date.group(2)
        if old_date != new_date:
            print(f"  ptt_appinfo.py: APP_DATE:")
            print(f"    old: {old_date}")
            print(f"    new: {new_date}")
            text = text.replace(old_date, new_date, 1)

    # Parse the APP_VERSION_INFO tuple from source text.
    # Matches both 4-element (suffix only) and 5-element (suffix + number) forms.
    m = re.search(
        r'APP_VERSION_INFO\s*=\s*'
        r'\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*'   # major, minor, patch
        r',\s*"([^"]+)"'                              # suffix (double-quoted)
        r'(?:\s*,\s*(\d+))?'                          # optional suf_num
        r'\s*\)',
        text
    )
    if not m:
        # 3-element tuple (no suffix) — write APP_DATE update if needed and stop
        if text != appinfo_path.read_text(encoding="utf-8"):
            appinfo_path.write_text(text, encoding="utf-8")
            with open(appinfo_path, encoding="utf-8") as _f:
                exec(compile(_f.read(), str(appinfo_path), "exec"), ptt_appinfo.__dict__)
        return

    major_   = int(m.group(1))
    minor_   = int(m.group(2))
    patch_   = int(m.group(3))
    suffix_  = m.group(4)
    suf_num_ = int(m.group(5)) if m.group(5) is not None else None

    if suf_num_ is None:
        # 4-element tuple (suffix only, no number) — leave APP_VERSION_INFO
        # untouched; write APP_DATE update if needed and stop.
        if text != appinfo_path.read_text(encoding="utf-8"):
            appinfo_path.write_text(text, encoding="utf-8")
            with open(appinfo_path, encoding="utf-8") as _f:
                exec(compile(_f.read(), str(appinfo_path), "exec"), ptt_appinfo.__dict__)
        return

    # 5-element tuple — increment the build number.
    new_suf_num = suf_num_ + 1
    wrapped     = new_suf_num > 65535
    if wrapped:
        new_suf_num = 1
        print(f"  WARNING: ptt_appinfo.py: build counter wrapped from 65535 to 1")

    # Build replacement strings
    old_assignment = m.group(0)
    old_tuple_str  = old_assignment.split('=', 1)[1].strip()
    new_tuple_str  = f'({major_}, {minor_}, {patch_}, "{suffix_}", {new_suf_num})'
    new_assignment = f"APP_VERSION_INFO = {new_tuple_str}"

    new_text = text.replace(old_assignment, new_assignment, 1)
    appinfo_path.write_text(new_text, encoding="utf-8")
    text = new_text   # keep text in sync for the re-exec below

    print(f"  ptt_appinfo.py: APP_VERSION_INFO:")
    print(f"    old: APP_VERSION_INFO = {old_tuple_str}")
    print(f"    new: APP_VERSION_INFO = {new_tuple_str}")

    # Re-exec the updated file directly into ptt_appinfo's module namespace,
    # bypassing .pyc cache so the rest of this script sees the new value.
    with open(appinfo_path, encoding="utf-8") as _f:
        exec(compile(_f.read(), str(appinfo_path), "exec"), ptt_appinfo.__dict__)

# ---------------------------------------------------------------------------
# Derive version components from APP_VERSION_INFO
# (called after _update_appinfo so values reflect any changes)
# ---------------------------------------------------------------------------

def _derive_version_vars() -> dict:
    """Return a dict of all version strings derived from the current ptt_appinfo."""
    info    = ptt_appinfo.APP_VERSION_INFO
    major   = info[0]
    minor   = info[1]
    patch   = info[2]
    suffix  = info[3] if len(info) >= 4 else None
    suf_num = info[4] if len(info) >= 5 else None

    # Windows 4-tuple build integer: last 4 digits of suf_num, else 0
    if suf_num is not None:
        build4 = int(str(suf_num)[-4:])
    else:
        build4 = 0

    ver_windows = f"{major}.{minor}.{patch}.{build4}"

    ver_iss = f"{ver_windows}-{suffix}" if suffix else ver_windows

    if suffix == "dev":
        desc_suffix = " (Development Use Only)"
    elif suffix:
        desc_suffix = f" ({suffix})"
    else:
        desc_suffix = ""

    return dict(
        major=major, minor=minor, patch=patch,
        suffix=suffix, suf_num=suf_num, build4=build4,
        ver_windows=ver_windows, ver_iss=ver_iss,
        desc_suffix=desc_suffix,
        win_tuple=(major, minor, patch, build4),
    )

# ---------------------------------------------------------------------------
# Helper: report a change
# ---------------------------------------------------------------------------

changes_found = False

def report(filename: str, field: str, old: str, new: str) -> None:
    global changes_found
    if old != new:
        changes_found = True
        print(f"  {filename}: {field}:")
        print(f"    old: {old}")
        print(f"    new: {new}")

# ---------------------------------------------------------------------------
# Update a .VersionInfo file
# ---------------------------------------------------------------------------

# Base descriptions per app (without any parenthetical suffix)
_BASE_DESCRIPTIONS = {
    "pttedit.VersionInfo": "PTTimeline Editor",
    "pttplot.VersionInfo": "PTTimeline Plotter",
    "pttview.VersionInfo": "PTTimeline Viewer",
}


def update_version_info(filename: str, v: dict) -> None:
    path = SCRIPT_DIR / filename
    if not path.exists():
        print(f"  WARNING: {filename} not found, skipping.")
        return

    original = path.read_text(encoding="utf-8")
    text = original

    # --- filevers / prodvers tuples ---
    tuple_str = f"({v['major']}, {v['minor']}, {v['patch']}, {v['build4']})"

    for field in ("filevers", "prodvers"):
        pattern   = rf'({field}\s*=\s*)\([^)]+\)'
        old_match = re.search(pattern, text)
        if old_match:
            report(filename, field, old_match.group(0), old_match.group(1) + tuple_str)
            text = text[:old_match.start()] + old_match.group(1) + tuple_str + text[old_match.end():]

    # --- FileVersion / ProductVersion strings ---
    for field in ("FileVersion", "ProductVersion"):
        pattern   = rf"(StringStruct\('{field}',\s*')[^']*(')"
        old_match = re.search(pattern, text)
        if old_match:
            old_full = old_match.group(0)
            new_full = old_match.group(1) + v['ver_windows'] + old_match.group(2)
            report(filename, field, old_full, new_full)
            text = text[:old_match.start()] + new_full + text[old_match.end():]

    # --- FileDescription ---
    base_desc = _BASE_DESCRIPTIONS.get(filename, "PTTimeline")
    new_desc  = base_desc + v['desc_suffix']
    pattern   = r"(StringStruct\('FileDescription',\s*')[^']*(')"
    old_match = re.search(pattern, text)
    if old_match:
        old_full = old_match.group(0)
        new_full = old_match.group(1) + new_desc + old_match.group(2)
        report(filename, "FileDescription", old_full, new_full)
        text = text[:old_match.start()] + new_full + text[old_match.end():]

    if text != original:
        path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Update PTTimeline.iss
# ---------------------------------------------------------------------------

def update_iss(v: dict, filename: str = "PTTimeline.iss") -> None:
    path = SCRIPT_DIR / filename
    if not path.exists():
        print(f"  WARNING: {filename} not found, skipping.")
        return

    original = path.read_text(encoding="utf-8")
    text = original

    ver_iss = v['ver_iss']

    # 1. "; Version:      x.x.x..."  comment line
    pattern = r'(;\s*Version:\s+)[^\r\n]+'
    m = re.search(pattern, text)
    if m:
        old_full = m.group(0)
        new_full = m.group(1) + ver_iss
        report(filename, "; Version", old_full, new_full)
        text = text[:m.start()] + new_full + text[m.end():]

    # 2. #define AppVersion     "x.x.x..."
    pattern = r'(#define\s+AppVersion\s+")[^"]*(")'
    m = re.search(pattern, text)
    if m:
        old_full = m.group(0)
        new_full = m.group(1) + ver_iss + m.group(2)
        report(filename, "#define AppVersion", old_full, new_full)
        text = text[:m.start()] + new_full + text[m.end():]

    # 3. #define AppVerName     "PTTimeline x.x.x..."
    pattern = r'(#define\s+AppVerName\s+")PTTimeline\s+[^"]*(")'
    m = re.search(pattern, text)
    if m:
        old_full = m.group(0)
        new_full = m.group(1) + f"PTTimeline {ver_iss}" + m.group(2)
        report(filename, "#define AppVerName", old_full, new_full)
        text = text[:m.start()] + new_full + text[m.end():]

    # 4. OutputBaseFilename       =PTTimeline_x.x.x..._setup
    pattern = r'(OutputBaseFilename\s*=\s*)PTTimeline_[^\r\n]+'
    m = re.search(pattern, text)
    if m:
        old_full = m.group(0)
        new_full = m.group(1) + f"PTTimeline_{ver_iss}_setup"
        report(filename, "OutputBaseFilename", old_full, new_full)
        text = text[:m.start()] + new_full + text[m.end():]

    if text != original:
        path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _update_appinfo()

    v = _derive_version_vars()

    print(f"ptt_update_version.py")
    print(f"  APP_VERSION_INFO : {ptt_appinfo.APP_VERSION_INFO}")
    print(f"  APP_DATE         : {ptt_appinfo.APP_DATE}")
    print(f"  ver_windows      : {v['ver_windows']}")
    print(f"  ver_iss          : {v['ver_iss']}")
    print(f"  win_tuple        : {v['win_tuple']}")
    print(f"  desc_suffix      : '{v['desc_suffix']}'")
    print()
    print("Checking files...")
    print()

    update_version_info("pttedit.VersionInfo", v)
    update_version_info("pttplot.VersionInfo", v)
    update_version_info("pttview.VersionInfo", v)
    update_iss(v)

    print()
    if changes_found:
        print("Done — files updated.")
    else:
        print("Done — no changes needed.")


if __name__ == "__main__":
    main()
