## PTTimeline v0.5.0-dev — _Development Release_

PTTimeline is a desktop application suite for creating, editing, and visualizing process-task timing diagrams, targeting real-time systems engineers.

This suite consists of three applications:

**PTTEdit** — Timeline data editor (.pttd files)
**PTTPlot** — Chart and plot renderer (.pttp files)
**PTTView** — PDF/image viewer for rendered output

**Installation**
Run the included installer. PTTimeline requires Windows 10 or later.

**Notes**
This is a development release intended for testing purposes. It is not a stable public release.
Please report bugs and feedback via [GitHub Issues](https://github.com/carverrn1/PTTimeline/issues). A free GitHub account is required to submit an issue.

### What's New in v0.5.0-dev

**New Features**
- Find (Ctrl+F) and Rename (Ctrl+R) in PTTEdit — search Process, Task, Start-ƒ, and End-ƒ columns for literal text; atomically rename Process Names or Process:Task Names across all formula references without breaking dependencies; includes Find All Results window and Rename Preview window (#18)
- File → Open Recent submenu in all three applications — up to 15 entries (newest first), tooltip showing full path on hover, stale entry pruning, and Clear Recent Files; file dialog defaults to the directory of the most recent entry (#4, #19)
- Backup on Save in PTTEdit and PTTPlot — automatic timestamped backups (`.YYYYMMDD-HHMMSS.bak`) before overwriting existing files; configurable backup folder and maximum backup count via INI (#24)
- Help → Support submenu in all three applications — opens GitHub Discussions, GitHub Issues, and pre-filled Submit Bug Report / Submit Feature Request forms in the browser, with live environment data injected into the report template (#8)
- Copy to Clipboard button added to About and System Information dialogs in all three applications; button label briefly shows "Copied!" for 1.5 seconds as visual feedback (#1)

**Changes**
- Removed File → Demo menu item from PTTEdit — sample files installed by the installer make it unnecessary (#21)
- "Open with PTTPlot" registered in the Windows Explorer context menu for .pttd files — double-click still opens PTTEdit; right-click now offers PTTPlot as an additional option (#30)
- PTTView gains a minimal INI configuration (pttview.ini) to support recent files persistence

**Bug Fixes**
- Fixed annotation markers lost on every save in PTTPlot — `[ANNOTATIONS.MARKERS]` was written as an empty section; markers are now correctly serialized back to the .pttp file (#25)
- Fixed PTTEdit creating an unnecessary .pttd backup when View → Plot is selected with no unsaved changes — backup and save are now skipped when the file is already current (#26)

**Infrastructure**
- New shared library module `lib/ptt_recent_files.py` — `RecentFiles` class used by all three apps; persists lists in each app's user INI under a `[RECENT_FILES]` section
- New shared library module `lib/ptt_utils.py` — `html_to_plain_text()` and `build_issue_url()` utilities shared across all three apps
- `ptt_appinfo.py` — added `APP_REPO_URL` as single source of truth for the repository URL
- `ptt_config.py` — added `get_user_ini_path()` and `load_view_config()` to support PTTView configuration

---
Report issues at https://github.com/carverrn1/PTTimeline/issues
