# PTTimeline

**Process-Task Timeline** — a desktop tool for creating, editing, and visualizing real-time process/task timing diagrams.

PTTimeline is aimed at real-time systems engineers who need to document, analyze, and present the timing relationships between concurrent processes and tasks — particularly in instrument control, embedded systems, and automated test environments.

---

## Applications

PTTimeline consists of three companion applications:

| Application | Description |
|-------------|-------------|
| **PTTEdit** | Timeline data editor — create and manage processes, tasks, durations, and formula-driven scheduling |
| **PTTPlot** | Chart renderer — visualize timeline data as publication-quality timing diagrams |
| **PTTView** | PDF/image viewer — review and present exported diagrams |

---

## File Formats

| Extension | Format | Owner | Description |
|-----------|--------|-------|-------------|
| `.pttd` | JSON | PTTEdit | Timeline data — processes, tasks, durations, dependencies |
| `.pttp` | INI | PTTPlot | Presentation settings — colors, layout, scaling |

---

## Key Features

- **Formula-driven task scheduling** — task start/end times can reference other tasks using expressions (`Start()`, `End()`, `Duration()`, `Min()`, `Max()`)
- **Named durations** — define reusable duration constants in a dedicated process
- **Three-tier configuration** — hardcoded defaults → user INI → per-presentation overrides
- **Multiple presentations** — the same `.pttd` data file can drive multiple independent `.pttp` presentations
- **Professional installer** — Windows x64 installer built with PyInstaller and Inno Setup

---

## Requirements

- Python 3.x
- PySide6
- matplotlib
- pandas
- Pillow
- portalocker

Install dependencies:
```
pip install PySide6 matplotlib pandas Pillow portalocker
```

---

## Running from Source

```
python pttedit.py
python pttplot.py
python pttview.py
```

---

## Building

```
build_all.bat          # Build all executables and installer
build_exe.bat          # Build executables only
build_install.bat      # Build installer only (run manually)
```

Requires PyInstaller and Inno Setup to be installed.

---

## Sample Files

The `samples/` folder contains example `.pttd` and `.pttp` files demonstrating PTTimeline with representative real-world timing diagrams.

---

## Project Structure

```
PTTimeline_Dev/
    pttedit.py                  # PTTEdit main application
    pttplot.py                  # PTTPlot main application
    pttview.py                  # PTTView main application
    lib/
        ptt_appinfo.py          # Shared version and metadata
        ptt_config.py           # Configuration management
        ptt_debugging.py        # Crash logging
        ptt_splash.py           # Splash screen (shared)
        pttedit_delegates.py    # PTTEdit table delegates
        pttedit_expression_evaluator.py  # Formula engine
    resources/                  # Icons and splash images
    docs/                       # User guides (HTML)
    samples/                    # Example .pttd and .pttp files
```

---

## Version

Current version: **0.3.1-dev**

---

## Author

Richard Carver — RNCSoftware

---

## License

See [license.txt](license.txt)
