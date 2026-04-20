# PTTimeline

**Process-Task Timeline** — a desktop tool for creating, editing, and visualizing real-time process/task timing diagrams.

PTTimeline is aimed at real-time systems engineers who need to document, analyze, and present the timing relationships between concurrent processes and tasks — particularly in instrument control, embedded systems, and automated test environments.

---

## Applications

PTTimeline consists of three companion applications:

| Application | Description                                                                                         |
| ----------- | --------------------------------------------------------------------------------------------------- |
| **PTTEdit** | Timeline data editor — create and manage processes, tasks, durations, and formula-driven scheduling |
| **PTTPlot** | Chart renderer — visualize timeline data as publication-quality timing diagrams                     |
| **PTTView** | PDF/image viewer — review and present exported diagrams                                             |

---

## File Formats

| Extension | Format | Owner   | Description                                               |
| --------- | ------ | ------- | --------------------------------------------------------- |
| `.pttd`   | JSON5  | PTTEdit | Timeline data — processes, tasks, durations, dependencies |
| `.pttp`   | INI    | PTTPlot | Presentation settings — colors, layout, scaling           |

---

## Key Features

- **Formula-driven task scheduling** — task start/end times can reference other tasks using expressions (`Start()`, `End()`, `Duration()`, `Min()`, `Max()`)
- **Named Constants** — define reusable constants using the "unnamed" process entries
- **Find & Rename** — locate text across the grid and atomically rename Process or Process:Task names without breaking formula references (PTTEdit)
- **Open Recent** — File → Open Recent submenu in all three apps, with up to 15 entries and file-dialog directory following the most recent file
- **Backup on Save** — automatic timestamped backups before overwriting `.pttd` and `.pttp` files, with configurable folder and retention limit
- **Multiple presentations** — the same `.pttd` data file can drive multiple independent `.pttp` presentations
- **Open with PTTPlot** — Windows Explorer context menu option to open a `.pttd` file directly in PTTPlot without going through PTTEdit
- **Professional installer** — Windows x64 installer built with PyInstaller and Inno Setup

---

## Installation (Windows)

Download and run the PTTimeline installer (`PTTimeline_vX.X.X_Setup.exe`). The installer:

- Installs `PTTEdit.exe`, `PTTPlot.exe`, and `PTTView.exe` as self-contained executables (no Python installation required)
- Registers `.pttd` files to open with PTTEdit by double-click, and adds **Open with PTTPlot** to the Windows Explorer context menu
- Creates Start Menu shortcuts for all three applications
- Installs sample `.pttd` and `.pttp` files to `%PUBLIC%\Documents\RNCSoftware\PTTimeline\Samples`
- Supports upgrade-over-existing installs

The installer is built with [PyInstaller](https://pyinstaller.org) and [Inno Setup](https://jrsoftware.org/isinfo.php).

---

## Sample Files

Sample `.pttd` and `.pttp` files are installed to:

```
%PUBLIC%\Documents\RNCSoftware\PTTimeline\Samples\
```

These demonstrate PTTimeline with representative real-world timing diagrams and serve as starting points for new projects.

---

## For Developers

### Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for environment and dependency management

### Setup

```
pyenv local 3.11.9         # Set Python version for this folder
uv venv                    # Create the virtual environment
uv sync --group build      # Install all dependencies
. .\set-env.ps1            # Activate the virtual environment
```

### Running from Source

```
python pttedit.py
python pttplot.py
python pttview.py
```

### Building

```
build_all.bat          # Update version, build executables, build installer
build_exe.bat          # Build executables only (PyInstaller)
build_install.bat      # Build installer only (Inno Setup, run manually)
```

Requires [Inno Setup](https://jrsoftware.org/isinfo.php) to be installed. PyInstaller is managed via `uv` as a build dependency.

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
        ptt_recent_files.py     # Shared recent files manager
        ptt_splash.py           # Splash screen (shared)
        ptt_utils.py            # Shared utilities
        pttedit_delegates.py    # PTTEdit table delegates
        pttedit_expression_evaluator.py  # Formula engine
    resources/                  # Icons and splash images
    docs/                       # User guides (HTML)
    samples/                    # Example .pttd and .pttp files
    INI/                        # Default INI files generated by each app
    branding/                   # Social Media Preview images
    Releases/                   # Release Notes files
```

---

## Version

Current version: **v0.5.0-dev**

---

## Author

Richard Carver — RNCSoftware

---

## License

See [license.txt](license.txt)
