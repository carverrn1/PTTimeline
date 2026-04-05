## PTTimeline v0.4.0-dev — _Development Release_

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

### What's New in v0.4.0-dev

**New Features**
- UML timing diagram export (File → Export UML Timing Diagram) in PTTEdit — generates `.puml` files for PlantUML
- `time_unit` field added to `.pttd` config section (s, ms, µs, ns) for axis labeling and future code generation exports

**Changes**
- Formula language cleaned up: legacy aliases `StartTime()`, `EndTime()`, and `Total()` removed; canonical case-sensitive function set is now authoritative
- Version numbering automated via `ptt_update_version.py`; `ptt_appinfo.py` is the single source of truth
- New format for ANNOTATION MARKERS

**Infrastructure**
- Migrated to Python 3.11.9
- PyInstaller upgraded to 6.19.0

---
Report issues at https://github.com/carverrn1/PTTimeline/issues