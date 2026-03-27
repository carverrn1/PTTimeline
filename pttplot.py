import sys
import os
import platform
import re
import subprocess
import webbrowser
import warnings
import configparser
from functools import partial
from pathlib import Path
from importlib.metadata import version as get_module_version

# Suppress matplotlib warning from NavigationToolbar2QT's internal legend()
# call when no labeled artists exist - harmless but noisy
warnings.filterwarnings(
    'ignore',
    message='No artists with labels found to put in legend',
    category=UserWarning,
    module='matplotlib'
)

# Suppress matplotlib log warning when a fixed MultipleLocator interval produces
# more than MAXTICKS ticks on a long timeline.  The plot renders correctly and
# the interval is preserved through zoom, so the warning is harmless.
# Note: matplotlib emits this via _log.warning() (Python logging), not
# warnings.warn(), so warnings.filterwarnings() has no effect here.
import logging
logging.getLogger('matplotlib.ticker').setLevel(logging.ERROR)

def get_app_root():
    # If the application is run as a bundle (PyInstaller)
    if getattr(sys, 'frozen', False):
        # sys.executable is the path to the .exe
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # sys.argv[0] is the path to the .py script
        # realpath() handles symbolic links; abspath() gives the full path
        return os.path.dirname(os.path.realpath(sys.argv[0]))

# Locate the support directories (same folder as this script)
_APP_DIR = get_app_root()
_LIB_DIR = os.path.join(_APP_DIR, "lib")
_RES_DIR = os.path.join(_APP_DIR, "resources")
_CFG_DIR = os.path.join(_APP_DIR, "config")
sys.path.insert(0, _LIB_DIR)    # add source library to search path

from ptt_splash import show_splash as _show_splash, update_splash, close_splash

def show_splash():
    return _show_splash('pttplot_splash.png', _RES_DIR)

# Setup program name and version information
PROGRAM_FILENAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]
capitalize_first_four = lambda s: s[:4].upper() + s[4:]     # Capitalize first 4 letters
from ptt_appinfo import APP_VERSION, APP_COPYRIGHT, APP_AUTHOR, APP_COMPANY, APP_DATE, APP_DESCRIPTION, APP_PACKAGE, APP_ID
PROGRAM_NAME    = capitalize_first_four(PROGRAM_FILENAME)
PACKAGE_NAME    = APP_PACKAGE

from platformdirs import user_config_dir, user_log_dir
USER_CONFIG_PATH = user_config_dir(PACKAGE_NAME, APP_COMPANY)
USER_LOG_PATH = user_log_dir(PACKAGE_NAME, APP_COMPANY)

import pprint

from collections import OrderedDict


DEFAULT_CONFIG = """\
[META]
; DO NOT EDIT THIS SECTION! [META] is maintained by the program
app_package=PTTimeline
app_name=PTTPlot
app_version=0.0.0
ini_version=1

[DEBUGGING]
enabled_bool=False
filename=pttplot.dbg

[EXTERNAL_PROGRAMS]
python_exe=python
viewer_py=pttview.py
viewer_exe=pttview.exe
pdf_viewer_py=pttview.py
pdf_viewer_exe=pttview.exe
svg_viewer_py=pttview.py
svg_viewer_exe=pttview.exe

[PLOTTING]
window_maximized_bool=False
title_text=Process-Task Timeline
x_axis_label=Time
y_axis_label=Processes
set_major_locator_float=1
set_minor_locator_float=0
x_axis_min_float=None
x_axis_max_float=None
exclude_hbar_groups=[""]
save_dpi_int=300

[PRESENTATION]
; hbar_stacking=(Stacked|Unstacked)
hbar_stacking=Unstacked
; hbar_label_justified=(Center|Left)
hbar_label_justified=Center
; hbar_label_rotation=(Horizontal|Slanted|Vertical)
hbar_label_rotation=Horizontal
; dependency_arrow_mode=(Time|Task)
;   Time - arrows connect the specific Start/End times referenced in formulas
;   Task - arrows connect predecessor/successor task bars (start->end of bar)
dependency_arrow_mode=Time
; show_predecessors_bool and show_successors_bool control auto-display of
; dependency arrows for all tasks when a file is loaded.
show_predecessors_bool=False
show_successors_bool=False

; ==============================================================================
; COLORS Section Example for pttplot.ini
; ==============================================================================
; Add this section to your pttplot.ini file to customize process colors
; 
; Notes:
; - Colors can be hex codes (#1f77b4) or named colors (red, blue, green, etc.)
;   https://datascientyst.com/full-list-named-colors-pandas-python-matplotlib/
; - Multi-line format is supported (continuation lines must be indented)
; - Colors will cycle/wrap if you have more processes than colors defined
; - Leave color_list empty or comment it out to use the default tab20 colormap
; ==============================================================================

[COLORS]
; This is the 'Tab20' colormap (default matplotlib qualitative colors)
; 20 distinct colors designed for categorical data
color_list = 
    #1f77b4,
    #aec7e8,
    #ff7f0e,
    #ffbb78,
    #2ca02c,
    #98df8a,
    #d62728,
    #ff9896,
    #9467bd,
    #c5b0d5,
    #8c564b,
    #c49c94,
    #e377c2,
    #f7b6d2,
    #7f7f7f,
    #c7c7c7,
    #bcbd22,
    #dbdb8d,
    #17becf,
    #9edae5

; ==============================================================================
; ANNOTATIONS.MARKER_DEFAULTS Section for pttplot.ini
; ==============================================================================
; Default attribute values applied to all markers when a per-marker field is
; blank or set to the key name.
;
;   linestyle        - Line style (default: dashed)
;   linewidth_float  - Line width; 0 = invisible line (default: 1)
;   color            - Line and label color (default: red)
;   fontsize_float   - Font size for marker labels (default: 7)
;   fontstyle        - Font style: Normal, Bold, Italic, Bold Italic (default: Normal)
;   position         - Label position: Top, Bottom, Center, or N% (default: Top)
;   rotation_float   - Label rotation in degrees (default: 0)
; ==============================================================================

[ANNOTATIONS.MARKER_DEFAULTS]
linestyle=dashed
linewidth_float=1
color=red
fontsize_float=7
fontstyle=normal
position=top
rotation_float=0

; ==============================================================================
; ANNOTATIONS.MARKERS Section for pttplot.ini
; ==============================================================================
; Defines vertical marker lines drawn at specific times on the plot.
; Default attribute values are in [ANNOTATIONS.MARKER_DEFAULTS].
;
; Each marker is defined by a unique key starting with "marker" followed by a
; digit (e.g. marker1, marker2). The value is a semicolon-separated list of
; named parameters. Only label= and time= are required; all others are
; optional and inherit from [ANNOTATIONS.MARKER_DEFAULTS] if omitted.
;
;   label=           - Display text for the marker (spaces allowed)
;   time=            - Time position for the vertical marker line.
;                      Accepts a numeric float:
;                        time=5.0
;                      Or a task reference formula (resolved at plot time):
;                        time=Start(ProcessName:TaskName)
;                        time=End(ProcessName:TaskName)
;                      Supported functions (must match exactly, same as PTTEdit):
;                        Start, End
;   linestyle=       - Matplotlib line style: none, solid, dashed, dashdot, dotted
;                      (or shorthand: -, --, -., :)
;   linewidth_float= - Line width in points (0 = invisible line, label only)
;   color=           - Matplotlib color: hex code (#ff0000) or named color (red)
;   fontsize_float=  - Font size for the label
;   fontstyle=       - Normal, Bold, Italic, Bold Italic
;   position=        - Where label text is placed along the marker line:
;                      Top, Bottom, Center, or a percentage (e.g. 25%)
;                      where the % is measured from the bottom of the plot.
;   rotation_float=  - Label text rotation in degrees.
;                      0 = vertical (reads bottom to top along Y-axis)
;                      90 = horizontal (reads left to right along X-axis)
;
; Example:
;   marker1 = label=Deadline; time=5.0; linestyle=dashed; color=red
;   marker2 = label=Milestone; time=End(Process1:Task3); linestyle=dotted; color=#00aa00; fontstyle=Italic; position=25%
;   marker3 = label=Label Only; time=Start(Process2:Task1); linewidth_float=0; color=blue; position=Center; rotation_float=90
; ==============================================================================

[ANNOTATIONS.MARKERS]
; Demo markers
;marker0=label=←0.0 (NOTE: This demo Marker); time=0.0; linestyle=dotted; linewidth_float=6; color=red; fontsize_float=10; fontstyle=italic; position=top; rotation_float=90
"""


import pandas as pd
import numpy as np

# Suppress Qt screen warnings before importing Qt modules
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.screen.warning=false;qt.qpa.screen.debug=false;qt.qpa.window=false'

from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget, QMessageBox, QPushButton, QDialogButtonBox, QHBoxLayout, QDialog, QListWidget, QLabel, QLineEdit, QScrollArea
from PySide6.QtGui import QIcon, QAction, QIcon, QImageReader, QActionGroup
from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch
from matplotlib.ticker import MultipleLocator, Locator
Locator.MAXTICKS = 10000   # Allow longer timelines; warning suppressed via logging filter above

import json5 as json

def create_save_dialog_with_view_button(parent, caption, directory, filter, view_callback):
    """Create a save dialog with custom 'Save & View' button"""
    # 1. Create the dialog instance
    file_dialog = QFileDialog(parent)
    file_dialog.setWindowTitle(caption)
    file_dialog.setAcceptMode(QFileDialog.AcceptSave)
    file_dialog.setNameFilter(filter)
    file_dialog.selectFile(directory)
    
    # 2. IMPORTANT: Disable native dialog to customize it
    file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
    
    # 3. Create and add custom button
    save_view_button = QPushButton("Save&&&View")
    
    def on_save_and_view():
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            file_path = selected_files[0]
            file_dialog.accept()  # Close dialog
            view_callback(file_path)  # Call the view function
    
    save_view_button.clicked.connect(on_save_and_view)
    
    # 4. Try to add to existing button box (Approach 1: Near standard buttons)
    try:
        # Find the button box that contains Save/Cancel buttons
        button_box = file_dialog.findChild(QDialogButtonBox)
        
        if button_box:
            # Add to existing button box (best placement)
            button_box.addButton(save_view_button, QDialogButtonBox.ActionRole)
        else:
            # Fallback: add to main layout
            layout = file_dialog.layout()
            if layout:
                layout.addWidget(save_view_button)
    except:
        # Ultimate fallback: add to main layout
        layout = file_dialog.layout()
        if layout:
            layout.addWidget(save_view_button)
    
    return file_dialog

def create_save_dialog_with_custom_bottom_buttons(parent, caption, directory, filter):
    """Create save dialog with Save, Save & View, and Cancel buttons.

    After exec(), check file_dialog.view_after_save to determine if the
    user clicked Save & View (True) or just Save (False).
    """
    from PySide6.QtWidgets import QHBoxLayout

    # 1. Create the dialog instance
    file_dialog = QFileDialog(parent)
    file_dialog.setWindowTitle(caption)
    file_dialog.setAcceptMode(QFileDialog.AcceptSave)
    file_dialog.setNameFilter(filter)
    file_dialog.selectFile(directory)

    # Flag to indicate user clicked "Save & View" vs "Save"
    file_dialog.view_after_save = False

    # 2. IMPORTANT: Disable native dialog to customize it
    file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)

    # 3. Hide the default button box
    try:
        button_box = file_dialog.findChild(QDialogButtonBox)
        if button_box:
            button_box.hide()
    except:
        pass

    # 4. Create custom button layout
    custom_button_layout = QHBoxLayout()

    # Create our buttons
    save_button = QPushButton("&Save")
    save_view_button = QPushButton("Save && &View")
    cancel_button = QPushButton("&Cancel")

    # Set up button actions
    def on_save():
        if file_dialog.selectedFiles():
            file_dialog.accept()

    def on_save_and_view():
        if file_dialog.selectedFiles():
            file_dialog.view_after_save = True
            file_dialog.accept()

    def on_cancel():
        file_dialog.reject()

    save_button.clicked.connect(on_save)
    save_view_button.clicked.connect(on_save_and_view)
    cancel_button.clicked.connect(on_cancel)
    
    # Set default button
    save_button.setDefault(True)
    
    # Add buttons to layout
    custom_button_layout.addStretch()  # Push buttons to right
    custom_button_layout.addWidget(save_button)
    custom_button_layout.addWidget(save_view_button)
    custom_button_layout.addWidget(cancel_button)
    
    # 5. Handle different layout types properly
    main_layout = file_dialog.layout()
    if main_layout:
        # Check the layout type and add accordingly
        if hasattr(main_layout, 'addLayout') and hasattr(main_layout, 'rowCount'):
            # It's a QGridLayout - add at the bottom
            row_count = main_layout.rowCount()
            main_layout.addLayout(custom_button_layout, row_count, 0, 1, -1)  # span all columns
        elif hasattr(main_layout, 'addLayout'):
            # It's a QVBoxLayout or QHBoxLayout
            main_layout.addLayout(custom_button_layout)
        else:
            # Fallback: create a container widget for our buttons
            from PySide6.QtWidgets import QWidget
            button_container = QWidget()
            button_container.setLayout(custom_button_layout)
            
            # Try to add the container widget
            if hasattr(main_layout, 'addWidget'):
                main_layout.addWidget(button_container)
    
    return file_dialog

# ── Section name constants ────────────────────────────────────────────────────
CONFIG_DEBUGGING_OPTIONS          = 'DEBUGGING'
CONFIG_PLOTTING_OPTIONS           = 'PLOTTING'
CONFIG_PRESENTATION_OPTIONS       = 'PRESENTATION'
CONFIG_COLORS_OPTIONS             = 'COLORS'
CONFIG_EXTERNAL_PROGRAMS_OPTIONS  = 'EXTERNAL_PROGRAMS'
CONFIG_ANNOTATIONS_MARKER_DEFAULTS_OPTIONS = 'ANNOTATIONS.MARKER_DEFAULTS'
CONFIG_ANNOTATIONS_MARKERS_OPTIONS         = 'ANNOTATIONS.MARKERS'

# ── Key name constants (must match DEFAULT_CONFIG INI string exactly) ─────────
CONFIG_DEBUGGING_ENABLED          = 'enabled_bool'
CONFIG_DEBUGGING_FILENAME         = 'filename'
CONFIG_PLOTTING_TITLE_TEXT        = 'title_text'
CONFIG_PLOTTING_X_AXIS_LABEL      = 'x_axis_label'
CONFIG_PLOTTING_Y_AXIS_LABEL      = 'y_axis_label'
CONFIG_PLOTTING_SET_MAJOR_LOCATOR = 'set_major_locator_float'
CONFIG_PLOTTING_SET_MINOR_LOCATOR = 'set_minor_locator_float'
CONFIG_PLOTTING_EXCLUDE_HBAR_GROUPS = 'exclude_hbar_groups'
CONFIG_PLOTTING_X_AXIS_MIN        = 'x_axis_min_float'
CONFIG_PLOTTING_X_AXIS_MAX        = 'x_axis_max_float'
CONFIG_PLOTTING_SAVE_DPI          = 'save_dpi_int'
CONFIG_PLOTTING_WINDOW_MAXIMIZED  = 'window_maximized_bool'
CONFIG_PRESENTATION_HBAR_STACKING        = 'hbar_stacking'
CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED = 'hbar_label_justified'
CONFIG_PRESENTATION_HBAR_LABEL_ROTATION  = 'hbar_label_rotation'
CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE = 'dependency_arrow_mode'
CONFIG_PRESENTATION_SHOW_PREDECESSORS     = 'show_predecessors_bool'
CONFIG_PRESENTATION_SHOW_SUCCESSORS       = 'show_successors_bool'
CONFIG_COLORS_COLOR_LIST                 = 'color_list'
CONFIG_EXTERNAL_PROGRAMS_PYTHON_EXE      = 'python_exe'
CONFIG_EXTERNAL_PROGRAMS_VIEWER_PY       = 'viewer_py'
CONFIG_EXTERNAL_PROGRAMS_VIEWER_EXE      = 'viewer_exe'
CONFIG_EXTERNAL_PROGRAMS_PDF_VIEWER_PY   = 'pdf_viewer_py'
CONFIG_EXTERNAL_PROGRAMS_PDF_VIEWER_EXE  = 'pdf_viewer_exe'
CONFIG_EXTERNAL_PROGRAMS_SVG_VIEWER_PY   = 'svg_viewer_py'
CONFIG_EXTERNAL_PROGRAMS_SVG_VIEWER_EXE  = 'svg_viewer_exe'
CONFIG_PROCESS_ATTRIBUTES_OPTIONS        = 'PROCESS_ATTRIBUTES'
CONFIG_PROCESS_ATTRIBUTES_COLOR          = 'color'
CONFIG_PROCESS_ATTRIBUTES_KNOWN          = {CONFIG_PROCESS_ATTRIBUTES_COLOR}  # expand as new attrs arrive
CONFIG_ANNOTATIONS_MARKERS_LINESTYLE     = 'linestyle'
CONFIG_ANNOTATIONS_MARKERS_LINEWIDTH     = 'linewidth_float'
CONFIG_ANNOTATIONS_MARKERS_COLOR         = 'color'
CONFIG_ANNOTATIONS_MARKERS_FONTSIZE      = 'fontsize_float'
CONFIG_ANNOTATIONS_MARKERS_FONTSTYLE     = 'fontstyle'
CONFIG_ANNOTATIONS_MARKERS_POSITION      = 'position'
CONFIG_ANNOTATIONS_MARKERS_ROTATION      = 'rotation_float'

# ── Presentation choice lists ─────────────────────────────────────────────────
CONFIG_PRESENTATION_HBAR_STACKING_Unstacked       = 'Unstacked'
CONFIG_PRESENTATION_HBAR_STACKING_Stacked         = 'Stacked'
CONFIG_PRESENTATION_HBAR_STACKING_CHOICES         = ['Unstacked', 'Stacked']
CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Center   = 'Center'
CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Left     = 'Left'
CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_CHOICES  = ['Center', 'Left']
CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal = 'Horizontal'
CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted   = 'Slanted'
CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical  = 'Vertical'
CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_CHOICES   = ['Horizontal', 'Slanted', 'Vertical']
CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Task    = 'Task'
CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Time    = 'Time'
CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_CHOICES = ['Time', 'Task']

# ── Marker fontstyle choices ──────────────────────────────────────────────────
CONFIG_ANNOTATIONS_MARKERS_FONTSTYLE_Normal     = 'Normal'
CONFIG_ANNOTATIONS_MARKERS_FONTSTYLE_Bold       = 'Bold'
CONFIG_ANNOTATIONS_MARKERS_FONTSTYLE_Italic     = 'Italic'
CONFIG_ANNOTATIONS_MARKERS_FONTSTYLE_BoldItalic = 'Bold Italic'
CONFIG_ANNOTATIONS_MARKERS_FONTSTYLE_CHOICES    = ['Normal', 'Bold', 'Italic', 'Bold Italic']

# Runtime config dict — populated by load_ini() at startup
config = {}


from ptt_config import load_plot_config, _apply_ini_config, _make_parser
from ptt_debugging import Debugging, CrashLogger
debugging_enabled = False
debugging_filename = None
debugging = Debugging()

_FORMULA_DEP_RE = re.compile(r'\b(\w+)\(([A-Za-z_$][A-Za-z0-9_]*:[A-Za-z_$][A-Za-z0-9_]*)\)')

def _get_formula_dependencies(formula_str, current_process, current_task):
    """Extract (process, task, ref_edge) tuples referenced in a formula string,
    expanding $ macros.  ref_edge is 'start' or 'end' based on the function name
    (Start() -> 'start', End() -> 'end', anything else -> 'end')."""
    deps = set()
    if not formula_str:
        return deps
    for match in _FORMULA_DEP_RE.finditer(formula_str):
        func_name = match.group(1).lower()
        proc, task = match.group(2).split(':')
        if proc == '$':
            proc = current_process
        if task == '$':
            task = current_task
        ref_edge = 'start' if func_name == 'start' else 'end'
        deps.add((proc, task, ref_edge))
    return deps


class TimelinePlotWidget(QWidget):
    def __init__(self, parent=None):
        debugging.enter()
        super().__init__(parent)
        self.parent = parent
        self.dataframe = None
        self.label_text_x_offset = 0
        self.label_text_font_size = 6
        self.default_xlim = None
        self.default_ylim = None
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        # Remove the toolbar's built-in options we don't want
        for action in self.toolbar.actions():
            if action.text() in ['Pan','Subplots','Customize','Save']:
                self.toolbar.removeAction(action)
        self.toolbar.setVisible(False)  # Hidden by default; toggle via Help menu
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.annotations = []
        self.task_plot_positions = {}   # (process, task) -> {'y': int, 'x_start': float, 'x_end': float}
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        debugging.leave()
        return

    def set_dataframe(self, dataframe):
        self.dataframe = dataframe
        return

    def _do_bars_overlap(self, start1, end1, start2, end2):
        # start should be less than or equal to end for this check
        if start1 > end1:
            start1, end1 = end1, start1
        if start2 > end2:
            start2, end2 = end2, start2
        # Check for overlap. Start and end of two bars touching is not an overlap.
        if start1 < end2 and start2 < end1:
            return True
        return False

    def plot_timeline(self, file_name):
        global config
        debugging.enter()

        # Show "Updating..." in status bar; processEvents() paints it before plot work begins
        if self.parent is not None:
            self.parent.statusBar().showMessage('Updating...')
            QApplication.processEvents()

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.ax = ax
        self.task_bars = []
        self.task_plot_positions = {}

        is_stacked_process_tasks = (config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]== CONFIG_PRESENTATION_HBAR_STACKING_Stacked)

        all_process_names = list(self.dataframe['ProcessName'])  # Keep original dataframe order
        excluded_process_names = config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_EXCLUDE_HBAR_GROUPS]
        included_process_names = []
        # print(f"all_process_names={all_process_names}")
        # print(f"excluded_process_names={excluded_process_names}")
        for process_name in all_process_names:
            # print(f"process_name={process_name}")
            if (process_name not in excluded_process_names):
                included_process_names.append(process_name)
        # print(f"included_process_names={included_process_names}")
        
        # Get unique process names BEFORE reversing to maintain consistent color assignment
        unique_process_names = list(dict.fromkeys(included_process_names))
        # print(f"unique_process_names={unique_process_names}")
        
        # Now reverse for display order
        included_process_names = included_process_names[::-1]
        # print(f"included_process_names reversed={included_process_names}")

        debugging.print(f"process_attributes={config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS]}")
        
        hbar_groups = OrderedDict()
        for row_index in reversed(range(self.dataframe.shape[0])):
            row = self.dataframe.iloc[row_index]
            process_name = row['ProcessName']
            if (process_name in excluded_process_names): continue
            task_name = row['TaskName']
            start_time = row['StartTime']
            end_time = row['EndTime']
            subgroup_cnt = 1
            group_found = False
            while (not group_found):
                if (is_stacked_process_tasks):
                    hbar_group_name = f"{process_name}:*:{subgroup_cnt}"
                else:
                    hbar_group_name = f"{process_name}:{task_name}:{subgroup_cnt}"
                if (hbar_group_name not in hbar_groups):
                    hbar_groups[hbar_group_name] = []
                task_info = OrderedDict()
                task_info['row_index'] = row_index
                task_info['process_name'] = process_name
                task_info['task_name'] = task_name
                task_info['start_time'] = start_time
                task_info['end_time'] = end_time
                this_task_overlaps = False
                for group_task in hbar_groups[hbar_group_name]:
                    this_task_overlaps = self._do_bars_overlap(task_info['start_time'], task_info['end_time'], group_task['start_time'], group_task['end_time'])
                    if (this_task_overlaps): break
                debugging.print(f"{task_info['process_name']}:{task_info['task_name']} in group '{hbar_group_name}': this_task_overlaps={this_task_overlaps}")
                if (this_task_overlaps):
                    subgroup_cnt += 1
                else:
                    hbar_groups[hbar_group_name].append(task_info)
                    group_found = True
        debugging.print(f"hbar_groups=\n{pprint.pformat(hbar_groups)}")
            

        debugging.print(f"self.dataframe['ProcessName']={self.dataframe['ProcessName']}")
        debugging.print(f"unique_process_names={unique_process_names}")
        debugging.print(f"process_attributes={config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS]}")
        
        if (is_stacked_process_tasks):
            process_grouping = unique_process_names
        else:
            process_grouping = included_process_names
            
        process_labels = []
        
        # Sort hbar_groups keys by first occurrence order in dataframe
        # Extract process name from each key and map to first occurrence
        first_occurrence = {}
        for idx, process_name in enumerate(self.dataframe['ProcessName']):
            if process_name not in first_occurrence and process_name not in excluded_process_names:
                first_occurrence[process_name] = idx
        
        # Sort hbar_group keys by first occurrence of their process, then reverse
        # so that first-occurring processes plot last (appear at top)
        sorted_keys = sorted(hbar_groups.keys(),
                            key=lambda k: first_occurrence.get(k.split(':')[0], float('inf')),
                            reverse=True)
        group_y_index = {key: idx for idx, key in enumerate(sorted_keys)}

        # for process in process_grouping:
            # process_data = self.dataframe[included_process_names == process]
            # debugging.print(f"  process={process}")
            # debugging.print(f"  process_data=\n{process_data}")
            # for _, row in process_data.iterrows():
            
            
        for hbar_group_name in sorted_keys:
            process_name, task_name, group_num = hbar_group_name.split(':')
            hbar_group_size = len(hbar_groups[hbar_group_name])
            if (hbar_group_size > 1):
                process_labels.append(f"{process_name}*{hbar_group_size}")
            else:
                process_labels.append(f"{process_name}")
            for task_info in hbar_groups[hbar_group_name]:
                row_index = task_info['row_index']
                row = self.dataframe.iloc[row_index]
                process = row['ProcessName']
                if (process in excluded_process_names): continue
                debugging.print(f"  hbar_group_name={hbar_group_name}")
                debugging.print(f"  row_index={row_index}")
                debugging.print(f"  process={process}")

                debugging.print(f"    row=\n{row}")
                duration = row['EndTime']-row['StartTime']
                _proc_attrs = config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS].get(process, {})
                _fill_color = _proc_attrs.get(CONFIG_PROCESS_ATTRIBUTES_COLOR, (0.5, 0.5, 0.5, 1.0))
                if (duration < 0):
                    fill_color = _fill_color
                    box_color = 'red'
                    box_style = '-'    # '-', '--', '-.', ':', ''
                    box_thickness = 1
                    box_hatch = None    # '/', '\', '|', '-', '+', 'x', 'o', 'O', '.', '*'
                    text_color = 'black'
                else:
                    fill_color = _fill_color
                    box_color = 'black'
                    box_style = '-'     # '-', '--', '-.', ':', ''
                    box_thickness = 1
                    box_hatch = None    # '/', '\', '|', '-', '+', 'x', 'o', 'O', '.', '*'
                    text_color = 'black'
                # if (is_stacked_process_tasks):
                    # bar_name = row['ProcessName']
                # else:
                    # bar_name = f"{row['ProcessName']}:{row['TaskName']}"
                bar_name = hbar_group_name
                rect = ax.barh(bar_name, width=duration, left=row['StartTime'], color=fill_color, edgecolor=box_color, linestyle=box_style, linewidth=box_thickness, hatch=box_hatch, alpha=1.0, zorder=3)
                self.task_bars.append((rect[0], row))
                self.task_plot_positions[(row['ProcessName'], row['TaskName'])] = {
                    'y': group_y_index[hbar_group_name],
                    'x_start': float(row['StartTime']),
                    'x_end': float(row['EndTime']),
                }
                # Adding task name text on the bar with black text for clarity
                if (config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal):
                    label_rotation = 0
                elif (config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted):
                    label_rotation = 45
                elif (config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical):
                    label_rotation = 90
                else:
                    label_rotation = 0
                label_indent = 0
                if (config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED] == CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Left):
                    ha = 'left'
                    label_indent = 0.05
                    label_x = row['StartTime']
                else:
                    ha = 'center'
                    label_indent = 0
                    label_x = row['StartTime'] + (row['EndTime']-row['StartTime'])/2
                
                # ax.text(row['StartTime'] + (row['EndTime']-row['StartTime'])/2, bar_name, row['TaskName'], ha='center', va='center', color='black', fontsize=6, rotation=label_rotation)
                txt = ax.text(label_x + label_indent, bar_name, row['TaskName'], ha=ha, va='center', color=text_color, fontsize=6, rotation=label_rotation, clip_on=True, zorder=5.5)
                txt.set_clip_box(ax.bbox)

        if (config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_SET_MAJOR_LOCATOR] > 0):
            ax.xaxis.set_major_locator(MultipleLocator(config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_SET_MAJOR_LOCATOR]))
            ax.grid(which='major', color='gray', linestyle='-', linewidth=0.5, zorder=1)

        if (config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_SET_MINOR_LOCATOR] > 0):
            ax.xaxis.set_minor_locator(MultipleLocator(config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_SET_MINOR_LOCATOR]))
            ax.grid(which='minor', color='gray', linestyle=':', linewidth=0.5, zorder=1)

        # Set axis spines (border lines) to be behind bars
        ax.set_axisbelow(True)

        x_tick_fontsize = 6
        y_tick_fontsize = 8
        ax.tick_params(axis='x', labelsize=x_tick_fontsize)  # Set font size for X axis tick labels
        ax.tick_params(axis='y', labelsize=y_tick_fontsize)  # Set font size for Y axis tick labels

        x_label_fontsize = 10
        y_label_fontsize = 10
        ax.set_xlabel(config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_X_AXIS_LABEL], fontsize=x_label_fontsize)
        ax.set_ylabel(config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_Y_AXIS_LABEL], fontsize=y_label_fontsize)
        
        # process_labels = []
        
        # if (is_stacked_process_tasks):
            # process_labels = unique_process_names
        # else:
            # process_labels = included_process_names
            
        ax.set_yticks(np.arange(len(process_labels)))
        ax.set_yticklabels(process_labels)

        # Rotate X-axis tick labels
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
        ax.tick_params(axis='x', labelrotation = 45)
        
        # Add subtitle to the plot
        subtitle = f'(File:{file_name})'
        ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, fontsize=7, color='gray', ha='center')
        
        # Add title to the plot
        ax.set_title(config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_TITLE_TEXT], loc='center', pad=20)  # Adjust the pad to increase the distance between title and subtitle

        # Set x-axis limits if configured
        x_axis_min = config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_X_AXIS_MIN]
        x_axis_max = config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_X_AXIS_MAX]
        if x_axis_min is not None or x_axis_max is not None:
            current_xlim = ax.get_xlim()
            new_left = x_axis_min if x_axis_min is not None else current_xlim[0]
            new_right = x_axis_max if x_axis_max is not None else current_xlim[1]
            ax.set_xlim(left=new_left, right=new_right)

        # Draw annotation marker lines (skip markers outside visible x-axis range)
        markers = config[CONFIG_ANNOTATIONS_MARKERS_OPTIONS].get('_markers', [])
        plot_xlim = ax.get_xlim()
        for marker in markers:
            # Resolve task reference formula if time= was not a literal float
            if marker['time'] is None:
                ref_edge, ref_proc, ref_task = marker['time_ref']
                pos_key = (ref_proc, ref_task)
                if pos_key in self.task_plot_positions:
                    # Task was plotted — use its bar position directly
                    pos_data = self.task_plot_positions[pos_key]
                    resolved_time = pos_data['x_start'] if ref_edge == 'start' else pos_data['x_end']
                else:
                    # Task not in plot (e.g. excluded or parameter row) — look up in DataFrame
                    mask = (self.dataframe['ProcessName'] == ref_proc) & (self.dataframe['TaskName'] == ref_task)
                    matches = self.dataframe[mask]
                    if matches.empty:
                        debugging.print(
                            f"WARNING: Marker '{marker['name']}': "
                            f"task '{ref_proc}:{ref_task}' not found in data. Skipping."
                        )
                        continue
                    row = matches.iloc[0]
                    resolved_time = float(row['StartTime']) if ref_edge == 'start' else float(row['EndTime'])
            else:
                resolved_time = marker['time']

            if resolved_time < plot_xlim[0] or resolved_time > plot_xlim[1]:
                continue
            if marker['linewidth'] > 0 and marker['linestyle'] != 'None':
                ax.axvline(x=resolved_time, linestyle=marker['linestyle'], color=marker['color'], linewidth=marker['linewidth'], zorder=4)
            pos = marker['position']
            if pos >= 1.0:
                va = 'top'
            elif pos <= 0.0:
                va = 'bottom'
            else:
                va = 'center'
            # User rotation: 0=vertical(bottom-to-top), 90=horizontal(left-to-right)
            # Matplotlib rotation: 0=horizontal, 90=vertical(bottom-to-top)
            mpl_rotation = 90.0 - marker['rotation']
            txt = ax.text(resolved_time, pos, f" {marker['name']}", transform=ax.get_xaxis_transform(),
                    fontsize=marker['fontsize'], fontweight=marker['fontweight'], fontstyle=marker['fontstyle'],
                    color=marker['color'], va=va, ha='left', rotation=mpl_rotation, clip_on=True)
            txt.set_clip_box(ax.bbox)

        # Auto-show dependency arrows if configured
        if config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_PREDECESSORS]:
            for rect, row in self.task_bars:
                arrows = self._draw_dependency_arrows(row['ProcessName'], row['TaskName'], rect.get_facecolor(), direction='predecessors')
                if arrows:
                    rect.pred_arrows = arrows
        if config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_SUCCESSORS]:
            for rect, row in self.task_bars:
                arrows = self._draw_dependency_arrows(row['ProcessName'], row['TaskName'], rect.get_facecolor(), direction='successors')
                if arrows:
                    rect.succ_arrows = arrows

        self.canvas.draw()

        # Capture default limits after drawing so toolbar Home button and
        # zoom-out clamping both reference the full initial view
        self.default_xlim = ax.get_xlim()
        self.default_ylim = ax.get_ylim()
        ax.callbacks.connect('xlim_changed', self.on_xlim_changed)
        ax.callbacks.connect('ylim_changed', self.on_ylim_changed)

        # Register the full initial view as the Home position in the nav stack.
        # update() clears any stale history from a previous file; push_current()
        # records the current (full) view so Home always returns here.
        self.toolbar.update()
        self.toolbar.push_current()

        # Clear "Updating..." and show Ready in status bar
        if self.parent is not None:
            self.parent.statusBar().showMessage('Ready')

        debugging.leave()

    def on_xlim_changed(self, ax):
        """Clamp X axis to prevent zooming out beyond the default full view"""
        if self.default_xlim is None:
            return
        lo, hi = ax.get_xlim()
        clamped = False
        if lo < self.default_xlim[0]:
            lo = self.default_xlim[0]
            clamped = True
        if hi > self.default_xlim[1]:
            hi = self.default_xlim[1]
            clamped = True
        if clamped:
            ax.set_xlim(lo, hi)

    def on_ylim_changed(self, ax):
        """Clamp Y axis to prevent zooming out beyond the default full view.
        Uses min/max comparisons to handle matplotlib's inverted Y axis on Gantt
        charts (where get_ylim() returns (lo, hi) with lo > hi).
        """
        if self.default_ylim is None:
            return
        lo, hi = ax.get_ylim()
        d_lo, d_hi = self.default_ylim
        # Work in terms of actual numeric bounds regardless of axis inversion
        view_min, view_max = min(lo, hi), max(lo, hi)
        bound_min, bound_max = min(d_lo, d_hi), max(d_lo, d_hi)
        clamped = False
        if view_min < bound_min:
            view_min = bound_min
            clamped = True
        if view_max > bound_max:
            view_max = bound_max
            clamped = True
        if clamped:
            # Restore original inversion direction
            if lo > hi:
                ax.set_ylim(view_max, view_min)
            else:
                ax.set_ylim(view_min, view_max)

    def on_scroll(self, event):
        """Mouse wheel pan/zoom — only active when toolbar (Zoom Controls) is visible.
        Wheel alone = pan up/down, Shift+Wheel = pan left/right, Ctrl+Wheel = zoom in/out.
        """
        debugging.enter()
        if not self.toolbar.isVisible():
            debugging.leave('toolbar not visible, ignoring scroll')
            return
        if event.xdata is None or event.ydata is None:
            debugging.leave('scroll outside axes, ignoring')
            return

        ax = self.ax
        ZOOM_FACTOR = 1.2
        PAN_FRACTION = 0.1  # pan 10% of current view range per scroll tick

        # Use Qt keyboard modifiers directly — matplotlib's event.key is unreliable
        # for scroll events on Windows (often arrives as None).
        qt_modifiers = QApplication.keyboardModifiers()
        ctrl_held  = bool(qt_modifiers & Qt.ControlModifier)
        shift_held = bool(qt_modifiers & Qt.ShiftModifier)

        if ctrl_held:
            # Ctrl + Wheel → zoom in/out both axes centered on cursor.
            # Push to toolbar history so Home button can return to pre-zoom state.
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            xdata, ydata = event.xdata, event.ydata
            if event.button == 'down':
                scale = ZOOM_FACTOR
            else:
                scale = 1 / ZOOM_FACTOR 
            new_xlim = [xdata + (x - xdata) * scale for x in xlim]
            new_ylim = [ydata + (y - ydata) * scale for y in ylim]
            # Clamp zoom-out to default full view (same logic as on_xlim/ylim_changed)
            if self.default_xlim is not None:
                new_xlim[0] = max(new_xlim[0], self.default_xlim[0])
                new_xlim[1] = min(new_xlim[1], self.default_xlim[1])
            if self.default_ylim is not None:
                new_ylim[0] = max(new_ylim[0], self.default_ylim[0])
                new_ylim[1] = min(new_ylim[1], self.default_ylim[1])
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            self.toolbar.push_current()  # record in nav history so Home works

        elif shift_held:
            # Shift + Wheel → pan left/right as a rigid window (no stretching).
            # Stop at the default view boundary instead of clamping one edge.
            xlim = ax.get_xlim()
            x_range = xlim[1] - xlim[0]
            delta = PAN_FRACTION * x_range
            if event.button == 'down': delta = -delta
            new_lo = xlim[0] + delta
            new_hi = xlim[1] + delta
            if self.default_xlim is not None:
                if new_lo < self.default_xlim[0]:
                    new_lo = self.default_xlim[0]
                    new_hi = new_lo + x_range
                if new_hi > self.default_xlim[1]:
                    new_hi = self.default_xlim[1]
                    new_lo = new_hi - x_range
            ax.set_xlim(new_lo, new_hi)

        else:
            # Wheel alone → pan up/down as a rigid window (no stretching).
            # Use min/max to handle inverted Y axis correctly.
            ylim = ax.get_ylim()
            delta = PAN_FRACTION * abs(ylim[1] - ylim[0]) 
            if event.button == 'down': delta = -delta
            new_lo = ylim[0] + delta
            new_hi = ylim[1] + delta
            if self.default_ylim is not None:
                d_lo, d_hi = self.default_ylim
                bound_min, bound_max = min(d_lo, d_hi), max(d_lo, d_hi)
                cur_min, cur_max = min(new_lo, new_hi), max(new_lo, new_hi)
                span = cur_max - cur_min
                if cur_min < bound_min:
                    cur_min = bound_min
                    cur_max = cur_min + span
                if cur_max > bound_max:
                    cur_max = bound_max
                    cur_min = cur_max - span
                # Restore original inversion direction
                if ylim[0] > ylim[1]:
                    new_lo, new_hi = cur_max, cur_min
                else:
                    new_lo, new_hi = cur_min, cur_max
            ax.set_ylim(new_lo, new_hi)

        self.canvas.draw_idle()
        debugging.leave()

    def _draw_dependency_arrows(self, process_name, task_name, color, direction='both'):
        """Draw dependency arrows for a task.
        direction: 'predecessors' (feed into this task), 'successors' (feed out of this task), or 'both'.
        In Task mode:  dep_end  -> task_start,  task_end -> succ_start  (bar-to-bar).
        In Time mode:  dep_ref_edge -> dest_formula_edge  (cell-to-cell, exact formula reference).
        Ghost arrows are drawn for dependencies whose process is excluded from the plot:
          - Ghost predecessor: short downward arrow into the bar's top edge at middle-X
          - Ghost successor:   short downward arrow out of the bar's bottom edge at middle-X
        Returns a list of FancyArrowPatch objects added to the axes."""
        debugging.enter(f'process_name={process_name}, task_name={task_name}, direction={direction}')
        arrows = []
        key = (process_name, task_name)
        if key not in self.task_plot_positions:
            debugging.leave('key not in task_plot_positions')
            return arrows
        pos = self.task_plot_positions[key]
        x_start, x_end, y = pos['x_start'], pos['x_end'], pos['y']

        mask = (self.dataframe['ProcessName'] == process_name) & (self.dataframe['TaskName'] == task_name)
        rows = self.dataframe[mask]
        if rows.empty:
            debugging.leave('no matching rows')
            return arrows
        row = rows.iloc[0]

        dep_arrow_mode = config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]
        time_mode = (dep_arrow_mode == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Time)

        # Darken the bar color slightly so arrows remain visible when crossing same-colored bars
        r, g, b, a = color
        color = (r * 0.85, g * 0.85, b * 0.85, a)

        arrow_kw = dict(arrowstyle='fancy,head_width=1.0,head_length=1.0,tail_width=0.5', mutation_scale=10, facecolor=color, edgecolor='black',
                        linewidth=0.5, linestyle='solid', zorder=5,
                        # connectionstyle='bar,angle=0,fraction=0.5',
                        connectionstyle='arc3,rad=0',
                        transform=self.ax.transData)

        # Ghost arrow keyword overrides: dashed line style to signal an excluded (off-plot) dependency
        ghost_arrow_kw = dict(arrow_kw, linestyle='dashed')

        # Ghost arrow length as a fraction of the current x-axis range so it scales with zoom
        GHOST_LENGTH_FRACTION = 0.04
        xlim = self.ax.get_xlim()
        ghost_length = (xlim[1] - xlim[0]) * GHOST_LENGTH_FRACTION

        # Bar half-height for barh bars (matplotlib default bar height is 0.8)
        BAR_HALF_HEIGHT = 0.4

        def _arrow_endpoints(sx0, sx1, sy, dx0, dx1, dy, src_edge=None, dst_edge=None):
            """Return (src_x, src_y, dst_x, dst_y, mutation_scale) for a dependency arrow.
            In Task mode (src_edge/dst_edge are None): tail is placed 2% inside the source
            bar's right edge; arrowhead is placed 2% inside the destination bar's left edge.
            In Time mode: src_edge ('start'|'end') and dst_edge ('start'|'end') select the
            exact bar edge, with a 2% inset toward bar center to keep arrows visible.
            When endpoints are coincident (touching bars, same row), use a larger inset (10%)."""
            if src_edge is None:
                # Task mode: source is right edge, destination is left edge
                src_x = sx1 - (sx1 - sx0) * 0.02
                dst_x = dx0 + (dx1 - dx0) * 0.02
            else:
                # Time mode: use specified edges with inset toward bar center
                src_x = (sx0 + (sx1 - sx0) * 0.02) if src_edge == 'start' else (sx1 - (sx1 - sx0) * 0.02)
                dst_x = (dx0 + (dx1 - dx0) * 0.02) if dst_edge == 'start' else (dx1 - (dx1 - dx0) * 0.02)
            mutation_scale = 10
            if abs(src_x - dst_x) < 1e-9 and abs(sy - dy) < 1e-9:
                inset = min((sx1 - sx0) * 0.10, (dx1 - dx0) * 0.10)
                if src_edge is None:
                    src_x = sx1 - inset
                    dst_x = dx0 + inset
                else:
                    src_x = (sx0 + inset) if src_edge == 'start' else (sx1 - inset)
                    dst_x = (dx0 + inset) if dst_edge == 'start' else (dx1 - inset)
            return src_x, sy, dst_x, dy, mutation_scale

        # Predecessor arrows: tasks that this task's formulas reference (feed into this task)
        if direction in ('predecessors', 'both'):
            own_deps = set()
            for col in ('StartTimeFormula', 'EndTimeFormula'):
                if col in self.dataframe.columns:
                    dest_edge = 'start' if col == 'StartTimeFormula' else 'end'
                    for dep_proc, dep_task, ref_edge in _get_formula_dependencies(str(row.get(col, '')), process_name, task_name):
                        own_deps.add((dep_proc, dep_task, ref_edge, dest_edge))

            pred_drawn = set()
            for dep_proc, dep_task, ref_edge, dest_edge in own_deps:
                dep_key = (dep_proc, dep_task)
                if dep_key == key:
                    continue
                # Dedup key: Task mode keyed on (proc, task); Time mode keyed on full 4-tuple
                dedup_key = (dep_proc, dep_task, ref_edge, dest_edge) if time_mode else (dep_proc, dep_task)
                if dedup_key in pred_drawn:
                    continue
                pred_drawn.add(dedup_key)
                if dep_key not in self.task_plot_positions:
                    # Excluded dependency: draw ghost arrow into top edge of this bar at middle-X
                    mid_x = (x_start + x_end) / 2.0
                    top_y  = y + BAR_HALF_HEIGHT
                    tail_y = top_y + ghost_length
                    arrows.append(self.ax.add_patch(FancyArrowPatch(
                        (mid_x, tail_y), (mid_x, top_y),
                        **dict(ghost_arrow_kw, mutation_scale=10))))
                    debugging.print(f'ghost predecessor arrow (excluded): {dep_key} -> {key}')
                else:
                    dp = self.task_plot_positions[dep_key]
                    se = ref_edge if time_mode else None
                    de = dest_edge if time_mode else None
                    sx, sy_, dx, dy_, ms = _arrow_endpoints(dp['x_start'], dp['x_end'], dp['y'], x_start, x_end, y, se, de)
                    arrows.append(self.ax.add_patch(FancyArrowPatch((sx, sy_), (dx, dy_), **dict(arrow_kw, mutation_scale=ms))))
                    debugging.print(f'predecessor arrow ({dep_arrow_mode}): {dep_key}[{ref_edge}] -> {key}[{dest_edge}]')

        # Successor arrows: tasks whose formulas reference this task (feed out of this task)
        if direction in ('successors', 'both'):
            succ_drawn = set()
            for idx in range(len(self.dataframe)):
                succ_row = self.dataframe.iloc[idx]
                succ_key = (succ_row['ProcessName'], succ_row['TaskName'])
                if succ_key == key:
                    continue
                for col in ('StartTimeFormula', 'EndTimeFormula'):
                    if col in self.dataframe.columns:
                        dest_edge = 'start' if col == 'StartTimeFormula' else 'end'
                        deps = _get_formula_dependencies(str(succ_row.get(col, '')), succ_row['ProcessName'], succ_row['TaskName'])
                        for dep_proc, dep_task, ref_edge in deps:
                            if (dep_proc, dep_task) != key:
                                continue
                            # Dedup key: Task mode keyed on (proc, task); Time mode keyed on full 4-tuple
                            dedup_key = (succ_key, ref_edge, dest_edge) if time_mode else succ_key
                            if dedup_key in succ_drawn:
                                continue
                            succ_drawn.add(dedup_key)
                            if succ_key not in self.task_plot_positions:
                                # Excluded dependency: draw ghost arrow out of bottom edge of this bar at middle-X
                                mid_x  = (x_start + x_end) / 2.0
                                bot_y  = y - BAR_HALF_HEIGHT
                                head_y = bot_y - ghost_length
                                arrows.append(self.ax.add_patch(FancyArrowPatch(
                                    (mid_x, bot_y), (mid_x, head_y),
                                    **dict(ghost_arrow_kw, mutation_scale=10))))
                                debugging.print(f'ghost successor arrow (excluded): {key} -> {succ_key}')
                            else:
                                sp = self.task_plot_positions[succ_key]
                                se = ref_edge if time_mode else None
                                de = dest_edge if time_mode else None
                                sx, sy_, dx, dy_, ms = _arrow_endpoints(x_start, x_end, y, sp['x_start'], sp['x_end'], sp['y'], se, de)
                                arrows.append(self.ax.add_patch(FancyArrowPatch((sx, sy_), (dx, dy_), **dict(arrow_kw, mutation_scale=ms))))
                                debugging.print(f'successor arrow ({dep_arrow_mode}): {key}[{ref_edge}] -> {succ_key}[{dest_edge}]')

        debugging.leave(f'{len(arrows)} arrows drawn')
        return arrows

    def toggle_all_predecessors(self):
        """Toggle predecessor arrows for all tasks. Returns True if arrows are now shown, False if hidden."""
        any_shown = any(hasattr(rect, 'pred_arrows') for rect, _ in self.task_bars)
        if any_shown:
            for rect, _ in self.task_bars:
                if hasattr(rect, 'pred_arrows'):
                    for arrow in rect.pred_arrows:
                        arrow.remove()
                    del rect.pred_arrows
        else:
            for rect, row in self.task_bars:
                arrows = self._draw_dependency_arrows(row['ProcessName'], row['TaskName'], rect.get_facecolor(), direction='predecessors')
                if arrows:
                    rect.pred_arrows = arrows
        self.canvas.draw()
        return not any_shown

    def toggle_all_successors(self):
        """Toggle successor arrows for all tasks. Returns True if arrows are now shown, False if hidden."""
        any_shown = any(hasattr(r, 'succ_arrows') for r, _ in self.task_bars)
        if any_shown:
            for r, _ in self.task_bars:
                if hasattr(r, 'succ_arrows'):
                    for arrow in r.succ_arrows:
                        arrow.remove()
                    del r.succ_arrows
        else:
            for r, row in self.task_bars:
                arrows = self._draw_dependency_arrows(row['ProcessName'], row['TaskName'], r.get_facecolor(), direction='successors')
                if arrows:
                    r.succ_arrows = arrows
        self.canvas.draw()
        return not any_shown

    def on_click(self, event):
        debugging.enter()
        qt_modifiers = QApplication.keyboardModifiers()
        ctrl_held = bool(qt_modifiers & Qt.ControlModifier)
        alt_held = bool(qt_modifiers & Qt.AltModifier)
        if event.button == 1 and ctrl_held:  # Ctrl+Left-Click: toggle predecessor arrows for clicked task
            for rect, row in self.task_bars:
                if rect.contains(event)[0]:
                    if hasattr(rect, 'pred_arrows'):
                        for arrow in rect.pred_arrows:
                            arrow.remove()
                        del rect.pred_arrows
                    else:
                        arrows = self._draw_dependency_arrows(row['ProcessName'], row['TaskName'], rect.get_facecolor(), direction='predecessors')
                        if arrows:
                            rect.pred_arrows = arrows
                    self.canvas.draw()
                    break
        if event.button == 3:  # Right-click
            for rect, row in self.task_bars:
                if rect.contains(event)[0]:
                    if ctrl_held:
                        # Ctrl+Right-Click: toggle successor arrows for clicked task
                        if hasattr(rect, 'succ_arrows'):
                            for arrow in rect.succ_arrows:
                                arrow.remove()
                            del rect.succ_arrows
                        else:
                            arrows = self._draw_dependency_arrows(row['ProcessName'], row['TaskName'], rect.get_facecolor(), direction='successors')
                            if arrows:
                                rect.succ_arrows = arrows
                    else:
                            # Right-click: toggle info annotation
                            duration = row['EndTime'] - row['StartTime']
                            # annotation_text = (f"Process: {row['ProcessName']}\nTask: {row['TaskName']}\n"
                                               # f"Start: {row['StartTime']}\nEnd: {row['EndTime']}\nDuration: {duration:.2f}")
                            if (alt_held):  # Alternate info display showing formulas
                                # Build predecessor list from this task's own formula dependencies
                                key = (row['ProcessName'], row['TaskName'])
                                pred_deps = set()
                                for col in ('StartTimeFormula', 'EndTimeFormula'):
                                    if col in self.dataframe.columns:
                                        pred_deps.update((p, t) for p, t, _ in _get_formula_dependencies(str(row.get(col, '')), row['ProcessName'], row['TaskName']))
                                pred_deps.discard(key)
                                pred_lines = '\n'.join(f"  {p}:{t}" for p, t in sorted(pred_deps)) if pred_deps else '  None'

                                # Build successor list by scanning all rows for references to this task
                                succ_deps = set()
                                for scan_idx in range(len(self.dataframe)):
                                    scan_row = self.dataframe.iloc[scan_idx]
                                    scan_key = (scan_row['ProcessName'], scan_row['TaskName'])
                                    if scan_key == key:
                                        continue
                                    for col in ('StartTimeFormula', 'EndTimeFormula'):
                                        if col in self.dataframe.columns:
                                            deps = {(p, t) for p, t, _ in _get_formula_dependencies(str(scan_row.get(col, '')), scan_row['ProcessName'], scan_row['TaskName'])}
                                            if key in deps:
                                                succ_deps.add(scan_key)
                                                break
                                succ_lines = '\n'.join(f"  {p}:{t}" for p, t in sorted(succ_deps)) if succ_deps else '  None'

                                annotation_text = ( f"Process: {row['ProcessName']}\n"
                                                    f"Task: {row['TaskName']}\n"
                                                    f"Start-ƒ: {row['StartTimeFormula']}\n"
                                                    f"Start: {row['StartTime']}\n"
                                                    f"End-ƒ: {row['EndTimeFormula']}\n"
                                                    f"End: {row['EndTime']}\n"
                                                    f"Duration: {duration:.2f}\n"
                                                    f"Predecessors:\n{pred_lines}\n"
                                                    f"Successors:\n{succ_lines}" )
                                annotation_text = annotation_text.replace("$", r"\$")
                            else:
                                annotation_text = ( f"Process: {row['ProcessName']}\n"
                                                    f"Task: {row['TaskName']}\n"
                                                    f"Start: {row['StartTime']}\n"
                                                    f"End: {row['EndTime']}\n"
                                                    f"Duration: {duration:.2f}" )
                            if not hasattr(rect, 'annot'):
                                annot = self.ax.annotate(annotation_text, xy=(event.xdata, event.ydata), xytext=(20, 20), textcoords="offset points",
                                                         bbox=dict(boxstyle="round", fc="w"), arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0", shrinkB=10), fontsize=6, zorder=6)
                                rect.annot = annot
                                self.annotations.append(annot)
                            else:
                                rect.annot.remove()
                                del rect.annot
                    self.canvas.draw()
                    break
        debugging.leave()

class ProcessAttributesDialog(QDialog):
    """
    Modeless dialog for viewing and editing per-process color attributes.

    Displays a two-column table: process name | colored swatch button.
    Clicking a swatch opens QColorDialog; picking a color updates
    config['PROCESS_ATTRIBUTES'] and immediately replots.

    Revert restores the snapshot taken when the dialog was opened.
    Close dismisses the dialog; changes survive in config and are saved
    via Presentation -> Save.
    """

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle('Process Attributes')
        self.setModal(False)

        # Snapshot of process_attributes at dialog-open time for Revert
        self._snapshot = self._take_snapshot()

        self._build_ui()

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def _take_snapshot(self):
        """Deep-copy the current process attributes (excluding runtime keys)."""
        import copy
        src = config.get(CONFIG_PROCESS_ATTRIBUTES_OPTIONS, {})
        return {k: copy.copy(v) for k, v in src.items() if not k.startswith('_')}

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Scrollable area for the process rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._grid = QVBoxLayout(container)
        self._grid.setSpacing(4)
        self._swatch_buttons = {}   # process_name -> QPushButton

        self._populate_rows()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Button row
        btn_layout = QHBoxLayout()
        revert_btn = QPushButton('&Revert')
        revert_btn.setToolTip('Restore colors to the state when this dialog was opened')
        revert_btn.clicked.connect(self._on_revert)
        close_btn = QPushButton('&Close')
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(revert_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setMinimumWidth(320)
        self.resize(360, min(80 + 36 * len(self._swatch_buttons), 600))

    def _populate_rows(self):
        """Fill the grid with one row per process."""
        from matplotlib.colors import to_hex
        proc_attrs = config.get(CONFIG_PROCESS_ATTRIBUTES_OPTIONS, {})
        for proc_name, attrs in proc_attrs.items():
            if proc_name.startswith('_'):
                continue
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 2, 4, 2)

            label = QLabel(proc_name)
            label.setMinimumWidth(160)
            row_layout.addWidget(label)

            btn = QPushButton()
            btn.setFixedWidth(80)
            btn.setFixedHeight(24)
            rgba = attrs.get(CONFIG_PROCESS_ATTRIBUTES_COLOR, (0.5, 0.5, 0.5, 1.0))
            self._apply_swatch_color(btn, rgba)
            btn.clicked.connect(lambda checked, p=proc_name, b=btn: self._on_swatch_clicked(p, b))
            row_layout.addWidget(btn)
            row_layout.addStretch()

            self._grid.addWidget(row_widget)
            self._swatch_buttons[proc_name] = btn

    def _apply_swatch_color(self, btn, rgba):
        """Set button background to rgba (matplotlib RGBA tuple)."""
        from matplotlib.colors import to_hex
        hex_color = to_hex(rgba)
        # Choose black or white label text based on luminance
        r, g, b = rgba[0], rgba[1], rgba[2]
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        text_color = '#000000' if luminance > 0.5 else '#ffffff'
        btn.setStyleSheet(
            f'background-color: {hex_color}; color: {text_color}; border: 1px solid #888;'
        )
        btn.setText(hex_color)

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_swatch_clicked(self, proc_name, btn):
        """Open color picker for proc_name; apply and replot on accept."""
        from matplotlib.colors import to_hex, to_rgba
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog

        proc_attrs = config.get(CONFIG_PROCESS_ATTRIBUTES_OPTIONS, {})
        current_rgba = proc_attrs.get(proc_name, {}).get(
            CONFIG_PROCESS_ATTRIBUTES_COLOR, (0.5, 0.5, 0.5, 1.0))
        initial = QColor(to_hex(current_rgba))

        color = QColorDialog.getColor(initial, self, f'Select Color — {proc_name}')
        if not color.isValid():
            return  # user cancelled

        # Convert QColor -> matplotlib RGBA and store
        new_rgba = to_rgba(color.name())
        proc_attrs[proc_name][CONFIG_PROCESS_ATTRIBUTES_COLOR] = new_rgba

        # Update _overrides so save_pttp_config round-trips the hex string
        overrides = proc_attrs.setdefault('_overrides', {})
        overrides.setdefault(proc_name, {})[CONFIG_PROCESS_ATTRIBUTES_COLOR] = color.name()

        self._apply_swatch_color(btn, new_rgba)
        self.main_window.plot_widget.plot_timeline(self.main_window.pttd_file_name)

    def _on_revert(self):
        """Restore colors to the snapshot taken when the dialog was opened."""
        from matplotlib.colors import to_hex
        proc_attrs = config.get(CONFIG_PROCESS_ATTRIBUTES_OPTIONS, {})

        for proc_name, snap_attrs in self._snapshot.items():
            if proc_name not in proc_attrs:
                continue
            snap_color = snap_attrs.get(CONFIG_PROCESS_ATTRIBUTES_COLOR)
            if snap_color is not None:
                proc_attrs[proc_name][CONFIG_PROCESS_ATTRIBUTES_COLOR] = snap_color
                btn = self._swatch_buttons.get(proc_name)
                if btn:
                    self._apply_swatch_color(btn, snap_color)

        # Restore _overrides to snapshot state
        overrides = proc_attrs.get('_overrides', {})
        for proc_name in list(overrides.keys()):
            if proc_name in self._snapshot:
                snap_color = self._snapshot[proc_name].get(CONFIG_PROCESS_ATTRIBUTES_COLOR)
                if snap_color is not None:
                    overrides[proc_name][CONFIG_PROCESS_ATTRIBUTES_COLOR] = to_hex(snap_color)
                else:
                    overrides.pop(proc_name, None)
            else:
                overrides.pop(proc_name, None)

        self.main_window.plot_widget.plot_timeline(self.main_window.pttd_file_name)

    # ------------------------------------------------------------------
    # Public refresh — called when a new file is loaded while dialog is open
    # ------------------------------------------------------------------

    def refresh(self):
        """Rebuild the dialog rows for a newly loaded file."""
        # Clear existing rows
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._swatch_buttons.clear()
        self._snapshot = self._take_snapshot()
        self._populate_rows()


class MainWindow(QMainWindow):
    def __init__(self, filename=None, splash=None, splash_label=None, splash_img=None):
        debugging.enter(f'filename={filename}')
        super().__init__()
        self.setWindowTitle(f'{PROGRAM_NAME}')
        # Set window icon
        icon_path = os.path.join(_RES_DIR, f"{PACKAGE_NAME}.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(100, 100, 800, 600)
        
        # Store the filename for loading after UI setup
        self.file_name = filename
        self.pttd_file_name = None
        self.pttp_file_name = None
        self.presentation_name = None   # qualifier string, e.g. '' for {}, 'overview' for {overview}
        self._splash = splash
        self._splash_label = splash_label
        self._splash_img = splash_img
        # Process Attributes dialog — single modeless instance
        self.process_attributes_dialog = None
        try:
            self.presentation_name_action.setText(f'Name: {{{self.presentation_name}}}')
        except:
            pass
        debugging.print(f'command line file: {self.file_name}')
        
        # File watcher for auto-reload when file changes
        self.file_watcher = None
        self.file_monitoring_enabled = False    # Set True only after a successful file load
        self._monitoring_paused_mtime = None    # mtime recorded when monitoring is disabled
        
        self.plot_widget = TimelinePlotWidget(parent=self)
        self.setCentralWidget(self.plot_widget)
        
        # config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING] = CONFIG_PRESENTATION_HBAR_STACKING_Stacked

        self.create_menu_bar()

        self.statusBar().showMessage('Ready')

        if (self.file_name):
            self.load_and_plot(self.file_name)
            self.setup_file_watcher()

        close_splash(self._splash)
        debugging.leave()
    
    def create_menu_bar(self):
        debugging.enter()
        menu_bar = self.menuBar()

        # ==== File Menu ====
        debugging.print(f'Adding File Menu')
        file_menu = menu_bar.addMenu('&File')

        file_open_action = QAction('&Open', self)
        file_open_action.triggered.connect(self.file_open_dialog)
        file_menu.addAction(file_open_action)
        
        file_save_menu = file_menu.addMenu('&Save')

        for fmt, label, ext, file_filter in [
            ('jpg', 'As &JPG', '.jpg', 'JPEG Files (*.jpg)'),
            ('png', 'As &PNG', '.png', 'PNG Files (*.png)'),
            ('pdf', 'As &PDF', '.pdf', 'PDF Files (*.pdf)'),
            ('svg', 'As &SVG', '.svg', 'SVG Files (*.svg)'),
        ]:
            action = QAction(label, self)
            action.triggered.connect(partial(self.save_as_format, fmt, ext, file_filter))
            file_save_menu.addAction(action)
        
        # file_close_action = QAction('&Close', self)
        # file_close_action.triggered.connect(self.exit_app)
        # file_menu.addAction(file_close_action)

        file_exit_action = QAction("&Exit", self)
        file_exit_action.triggered.connect(self.exit_app)
        file_menu.addAction(file_exit_action)
        
        # ==== Presentation Menu ====
        debugging.print(f'Adding Presentation Menu')
        presentation_menu = menu_bar.addMenu('&Presentation')

        self.presentation_open_action = QAction('&Open...', self)
        self.presentation_open_action.triggered.connect(self.presentation_open_dialog)
        self.presentation_open_action.setEnabled(False)
        presentation_menu.addAction(self.presentation_open_action)

        self.presentation_save_action = QAction('&Save...', self)
        self.presentation_save_action.triggered.connect(self.presentation_save_dialog)
        self.presentation_save_action.setEnabled(False)
        presentation_menu.addAction(self.presentation_save_action)

        presentation_menu.addSeparator()
        
        self.presentation_replot_action = QAction('Re-&Plot On PTTD Change', self, checkable=True)
        self.presentation_replot_action.setChecked(False)   # False until a file is successfully loaded
        self.presentation_replot_action.setEnabled(False)   # Disabled until a file is successfully loaded
        self.presentation_replot_action.triggered.connect(self.on_replot_on_pttd_change_toggled)
        presentation_menu.addAction(self.presentation_replot_action)

        presentation_menu.addSeparator()

        # Use disabled action as a label
        presentation_name = self.presentation_name if (self.presentation_name is not None) else ''
        self.presentation_name_action = QAction(f'Name:{{{presentation_name}}}', self)
        self.presentation_name_action.setEnabled(False)
        font = self.presentation_name_action.font()
        font.setBold(True)
        self.presentation_name_action.setFont(font)
        presentation_menu.addAction(self.presentation_name_action)
        
        presentation_menu.addSeparator()

        # Format > Bars > (Stacking + Labels)
        presentation_format_menu = presentation_menu.addMenu('&Format')
        presentation_bars_menu = presentation_format_menu.addMenu('&Bars')

        self.presentation_layout_stacked_action = QAction('&Stacked', self, checkable=True)
        self.presentation_layout_stacked_action.triggered.connect(self.presentation_layout_set_stacked)
        presentation_bars_menu.addAction(self.presentation_layout_stacked_action)

        self.presentation_layout_unstacked_action = QAction('&Unstacked', self, checkable=True)
        self.presentation_layout_unstacked_action.triggered.connect(self.presentation_layout_set_unstacked)
        presentation_bars_menu.addAction(self.presentation_layout_unstacked_action)

        self.presentation_layout_stacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Stacked)
        self.presentation_layout_unstacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Unstacked)

        presentation_bars_menu.addSeparator()

        presentation_label_menu = presentation_bars_menu.addMenu('&Labels')

        self.presentation_label_justified_left_action = QAction('&Left Justified', self, checkable=True)
        self.presentation_label_justified_left_action.triggered.connect(self.presentation_label_set_justified_left)
        presentation_label_menu.addAction(self.presentation_label_justified_left_action)

        self.presentation_label_justified_center_action = QAction('&Center Justified', self, checkable=True)
        self.presentation_label_justified_center_action.triggered.connect(self.presentation_label_set_justified_center)
        presentation_label_menu.addAction(self.presentation_label_justified_center_action)

        self.presentation_label_justified_left_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED] == CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Left)
        self.presentation_label_justified_center_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED] == CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Center)

        presentation_label_menu.addSeparator()

        self.presentation_label_rotation_horizontal_action = QAction('Rotation &Horizontal (0 Degrees)', self, checkable=True)
        self.presentation_label_rotation_horizontal_action.triggered.connect(self.presentation_label_set_rotation_horizontal)
        presentation_label_menu.addAction(self.presentation_label_rotation_horizontal_action)

        self.presentation_label_rotation_slanted_action = QAction('Rotation &Slanted (45 Degrees)', self, checkable=True)
        self.presentation_label_rotation_slanted_action.triggered.connect(self.presentation_label_set_rotation_slanted)
        presentation_label_menu.addAction(self.presentation_label_rotation_slanted_action)

        self.presentation_label_rotation_vertical_action = QAction('Rotation &Vertical (90 Degrees)', self, checkable=True)
        self.presentation_label_rotation_vertical_action.triggered.connect(self.presentation_label_set_rotation_vertical)
        presentation_label_menu.addAction(self.presentation_label_rotation_vertical_action)

        self.presentation_label_rotation_horizontal_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal)
        self.presentation_label_rotation_slanted_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted)
        self.presentation_label_rotation_vertical_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical)

        self.presentation_process_attributes_action = QAction('Process &Attributes...', self)
        self.presentation_process_attributes_action.triggered.connect(self.show_process_attributes_dialog)
        self.presentation_process_attributes_action.setEnabled(False)   # Disabled until file loaded
        presentation_format_menu.addAction(self.presentation_process_attributes_action)

        presentation_format_menu.addSeparator()

        presentation_dep_arrows_menu = presentation_format_menu.addMenu('&Dependency Arrows')

        self.presentation_dep_arrows_show_pred_action = QAction('Show &Predecessors', self, checkable=True)
        self.presentation_dep_arrows_show_pred_action.triggered.connect(self.presentation_dep_arrows_toggle_predecessors)
        presentation_dep_arrows_menu.addAction(self.presentation_dep_arrows_show_pred_action)

        self.presentation_dep_arrows_show_succ_action = QAction('Show &Successors', self, checkable=True)
        self.presentation_dep_arrows_show_succ_action.triggered.connect(self.presentation_dep_arrows_toggle_successors)
        presentation_dep_arrows_menu.addAction(self.presentation_dep_arrows_show_succ_action)

        self.presentation_dep_arrows_show_pred_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_PREDECESSORS])
        self.presentation_dep_arrows_show_succ_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_SUCCESSORS])

        presentation_dep_arrows_menu.addSeparator()

        dep_arrows_mode_group = QActionGroup(self)
        dep_arrows_mode_group.setExclusive(True)

        self.presentation_dep_arrows_time_action = QAction('&Time', self, checkable=True)
        self.presentation_dep_arrows_time_action.triggered.connect(self.presentation_dep_arrows_set_time)
        dep_arrows_mode_group.addAction(self.presentation_dep_arrows_time_action)
        presentation_dep_arrows_menu.addAction(self.presentation_dep_arrows_time_action)

        self.presentation_dep_arrows_task_action = QAction('T&ask', self, checkable=True)
        self.presentation_dep_arrows_task_action.triggered.connect(self.presentation_dep_arrows_set_task)
        dep_arrows_mode_group.addAction(self.presentation_dep_arrows_task_action)
        presentation_dep_arrows_menu.addAction(self.presentation_dep_arrows_task_action)

        self.presentation_dep_arrows_time_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Time)
        self.presentation_dep_arrows_task_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Task)
        
        # ==== Help Menu ====
        debugging.print(f'Adding Help Menu')
        help_menu = menu_bar.addMenu('&Help')

        help_userguide_action = QAction('&User Guide', self)
        help_userguide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(help_userguide_action)

        help_instructions_action = QAction('&Instructions', self)
        help_instructions_action.setShortcut('F1')
        help_instructions_action.triggered.connect(self.show_help)
        help_menu.addAction(help_instructions_action)

        help_menu.addSeparator()

        help_toggle_navbar_action = QAction('&Zoom Controls', self, checkable=True)
        help_toggle_navbar_action.setChecked(False)  # Off by default
        help_toggle_navbar_action.triggered.connect(self.on_toolbar_toggled)
        help_menu.addAction(help_toggle_navbar_action)

        help_menu.addSeparator()

        help_about_action = QAction('&About', self)
        help_about_action.triggered.connect(self.show_about)
        help_menu.addAction(help_about_action)
        
        help_sysinfo_action = QAction('&System Information', self)
        help_sysinfo_action.triggered.connect(self.show_system_info)
        help_menu.addAction(help_sysinfo_action)
        
        debugging.leave()
        return

    def on_toolbar_toggled(self, checked: bool):
        self.plot_widget.toolbar.setVisible(checked)
        # deactivate Zoom if currently activated
        if self.plot_widget.toolbar.mode == 'zoom rect':
            self.plot_widget.toolbar.zoom()

    def on_replot_on_pttd_change_toggled(self, checked: bool):
        """Enable or disable automatic re-plot when the .pttd file changes.
        When re-enabled, reload only if the file was modified while monitoring was paused."""
        debugging.enter(f'checked={checked}')
        if not checked:
            # Record the current mtime so we can detect changes while paused
            try:
                self._monitoring_paused_mtime = os.path.getmtime(self.pttd_file_name)
            except Exception:
                self._monitoring_paused_mtime = None
            self.file_monitoring_enabled = False
        else:
            self.file_monitoring_enabled = True
            # Only reload if the file changed while monitoring was paused
            changed = False
            if self._monitoring_paused_mtime is not None and self.pttd_file_name:
                try:
                    changed = os.path.getmtime(self.pttd_file_name) != self._monitoring_paused_mtime
                except Exception:
                    pass
            self._monitoring_paused_mtime = None
            if changed:
                debugging.print('File changed while monitoring was paused — reloading')
                self.load_and_plot(self.pttd_file_name)
            else:
                debugging.print('File unchanged while monitoring was paused — no reload')
        debugging.leave()

    def setup_file_watcher(self):
        """Setup file system watcher to monitor the loaded .pttd data file for changes"""
        debugging.enter(f'self.pttd_file_name={self.pttd_file_name}')

        if not self.pttd_file_name:
            debugging.leave('No file to watch')
            return

        # Clean up old watcher if it exists
        if self.file_watcher is not None:
            debugging.print('Disconnecting old file watcher')
            self.file_watcher.fileChanged.disconnect()
            self.file_watcher.deleteLater()
            self.file_watcher = None

        # Create file watcher and monitor the loaded .pttd data file
        self.file_watcher = QFileSystemWatcher([self.pttd_file_name], self)
        self.file_watcher.fileChanged.connect(self.on_file_changed)

        debugging.print(f'Watching file: {self.pttd_file_name}')
        debugging.leave()

    def on_file_changed(self, path):
        """Called when the watched file is modified - schedule a delayed reload"""
        debugging.enter(f'path={path}')
        
        if not self.file_monitoring_enabled:
            debugging.print('File monitoring disabled — ignoring file change event')
            debugging.leave()
            return

        # Use a short delay to allow the file operation to complete
        # This handles editors that delete/recreate files or have temporary locks
        debugging.print('File change detected, scheduling reload in 200ms...')
        QTimer.singleShot(200, self.reload_file)
        
        debugging.leave()

    def reload_file(self):
        """Perform the actual file reload - called after a short delay"""
        debugging.enter()

        try:
            # Check if file still exists and is being watched
            if not self.file_watcher.files():
                debugging.print('Re-adding file to watcher (file was recreated)')
                self.file_watcher.addPath(self.pttd_file_name)

            # Reload and replot the data
            debugging.print('Reloading plot...')
            self.load_and_plot(self.pttd_file_name)
            debugging.print('Plot reloaded successfully')
            
        except FileNotFoundError:
            debugging.print(f'File not found — disabling file monitoring: {self.pttd_file_name}')
            self.file_monitoring_enabled = False
            QMessageBox.warning(self, 'WARNING: File Monitoring Disabled',
                f'File is no longer available:\n{self.pttd_file_name}\n\n'
                f'Open an existing PTTD file to restore File Monitoring.')
        except Exception as e:
            debugging.print(f'Error reloading file: {e}')
            # Don't show error dialog - file might be temporarily locked
        
        debugging.leave()

    def presentation_label_set_rotation_horizontal(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] = CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal
        self.presentation_label_rotation_horizontal_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal)
        self.presentation_label_rotation_slanted_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted)
        self.presentation_label_rotation_vertical_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]}")
        return

    def presentation_label_set_rotation_slanted(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] = CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted
        self.presentation_label_rotation_horizontal_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal)
        self.presentation_label_rotation_slanted_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted)
        self.presentation_label_rotation_vertical_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]}")
        return

    def presentation_label_set_rotation_vertical(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] = CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical
        self.presentation_label_rotation_horizontal_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal)
        self.presentation_label_rotation_slanted_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted)
        self.presentation_label_rotation_vertical_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]==CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION]}")
        return

    def presentation_label_set_justified_left(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED] = CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Left
        self.presentation_label_justified_center_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]==CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Center)
        self.presentation_label_justified_left_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]==CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Left)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]}")
        return

    def presentation_label_set_justified_center(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED] = CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Center
        self.presentation_label_justified_center_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]==CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Center)
        self.presentation_label_justified_left_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]==CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Left)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED]}")
        return

    def presentation_layout_set_stacked(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING] = CONFIG_PRESENTATION_HBAR_STACKING_Stacked
        self.presentation_layout_stacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Stacked)
        self.presentation_layout_unstacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Unstacked)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]}")
        return

    def presentation_layout_set_unstacked(self):
        global config
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING] = CONFIG_PRESENTATION_HBAR_STACKING_Unstacked
        self.presentation_layout_stacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Stacked)
        self.presentation_layout_unstacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Unstacked)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]}")
        self.plot_widget.plot_timeline(self.file_name)
        return

    def show_process_attributes_dialog(self):
        """Open (or raise) the modeless Process Attributes dialog."""
        debugging.enter()
        if self.process_attributes_dialog is None or not self.process_attributes_dialog.isVisible():
            self.process_attributes_dialog = ProcessAttributesDialog(self)
            self.process_attributes_dialog.show()
        else:
            self.process_attributes_dialog.raise_()
            self.process_attributes_dialog.activateWindow()
        debugging.leave()

    def presentation_dep_arrows_set_time(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] = CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Time
        self.presentation_dep_arrows_time_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Time)
        self.presentation_dep_arrows_task_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Task)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]}")
        return

    def presentation_dep_arrows_set_task(self):
        debugging.enter(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]}")
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] = CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Task
        self.presentation_dep_arrows_time_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Time)
        self.presentation_dep_arrows_task_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Task)
        self.plot_widget.plot_timeline(self.file_name)
        debugging.leave(f"config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]={config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE]}")
        return

    def presentation_dep_arrows_toggle_predecessors(self):
        debugging.enter()
        now_shown = self.plot_widget.toggle_all_predecessors()
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_PREDECESSORS] = now_shown
        self.presentation_dep_arrows_show_pred_action.setChecked(now_shown)
        debugging.leave(f'now_shown={now_shown}')
        return

    def presentation_dep_arrows_toggle_successors(self):
        debugging.enter()
        now_shown = self.plot_widget.toggle_all_successors()
        config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_SUCCESSORS] = now_shown
        self.presentation_dep_arrows_show_succ_action.setChecked(now_shown)
        debugging.leave(f'now_shown={now_shown}')
        return

    def exit_app(self):
        """Called by File->Close menu action"""
        debugging.enter()
        self.close()  # This triggers closeEvent
        debugging.leave()

    def closeEvent(self, event):
        """Override closeEvent to handle window closing properly"""
        debugging.enter(f'event={event}')
        # if (self.file_name.endswith("pttd-tmp")): os.remove(self.file_name)
        event.accept()  # Accept the close event
        debugging.leave()
        
    def load_and_plot(self, file_name):
        debugging.enter(f'file_name={file_name}')
        update_splash(getattr(self, '_splash', None), getattr(self, '_splash_label', None), getattr(self, '_splash_img', None), 'Loading file...')
        
        file_basename = os.path.basename(file_name) if (file_name is not None) else ''
        debugging.print(f'{file_name=} ({file_basename})')

        pttd_basename = os.path.basename(self.pttd_file_name) if (self.pttd_file_name is not None) else ''
        debugging.print(f'{self.pttd_file_name=} ({pttd_basename})')

        pttp_basename = os.path.basename(self.pttp_file_name) if (self.pttp_file_name is not None) else ''
        debugging.print(f'{self.pttp_file_name=} ({pttp_basename})')

        debugging.print(f'{self.presentation_name=}')

        # Determine the incoming pttd absolute path for same-file comparison.
        # derive_file_pair handles both .pttd and .pttp inputs.
        incoming_pttd, incoming_pttp = derive_file_pair(os.path.abspath(str(file_name)))
        incoming_pttd_resolved = str(Path(incoming_pttd).resolve())
        incoming_is_pttp = os.path.splitext(str(file_name))[1].lower() == '.pttp'
        debugging.print(f'{incoming_pttd_resolved=}')
        debugging.print(f'{incoming_is_pttp=}')

        # Apply the four pttp reload rules using full absolute path comparison:
        #   Rule 1: No pttd was previously loaded  -> load default pttp (or create it)
        #   Rule 2: A different pttd is being loaded -> clear previous state, then Rule 1
        #   Rule 3: The same pttd is being reloaded -> keep the currently loaded pttp as-is
        #   Rule 4: The same pttd but an explicit different pttp -> reset config and load the new pttp
        #   Note: Rule 4 only applies when the incoming filename is explicitly a .pttp file.
        #         Re-opening the same .pttd always triggers Rule 3, preserving the current presentation.
        if self.pttd_file_name is None:
            # Rule 1: first load — no prior state
            debugging.print('Rule 1: no prior pttd loaded — loading default pttp')
            is_same_pttd = False
        else:
            current_pttd_resolved = str(Path(self.pttd_file_name).resolve())
            is_same_pttd = (incoming_pttd_resolved == current_pttd_resolved)
            if is_same_pttd:
                if incoming_is_pttp:
                    # Check if the incoming pttp is different from the currently loaded one
                    current_pttp_resolved = str(Path(self.pttp_file_name).resolve()) if self.pttp_file_name else None
                    incoming_pttp_resolved = str(Path(incoming_pttp).resolve())
                    if current_pttp_resolved != incoming_pttp_resolved:
                        # Rule 4: same pttd, explicit different pttp — load the new presentation
                        debugging.print('Rule 4: same pttd, different pttp — loading new presentation')
                        is_same_pttd = False
                        self.pttp_file_name = None
                        self.presentation_name = None
                        self.presentation_name_action.setText(f'Name: {{{self.presentation_name}}}')
                    else:
                        # Same pttd, same explicit pttp — treat as Rule 3
                        debugging.print('Rule 3: same pttd, same pttp reloaded — keeping current pttp presentation')
                else:
                    # Rule 3: same pttd reloaded via .pttd or file watcher — preserve current presentation
                    debugging.print('Rule 3: same pttd reloaded — keeping current pttp presentation')
            else:
                # Rule 2: different pttd — clear previous state and apply Rule 1
                debugging.print('Rule 2: different pttd loaded — clearing previous state, loading default pttp')
                self.pttd_file_name = None
                self.pttp_file_name = None
                self.presentation_name = None
                self.presentation_name_action.setText(f'Name: {{{self.presentation_name}}}')

        if not is_same_pttd:
            # Rules 1 & 2: derive and store the new pttd+pttp pair
            pttd_filename, pttp_filename = incoming_pttd, incoming_pttp
            self.pttd_file_name = pttd_filename
            self.pttp_file_name = pttp_filename

            # Extract presentation name from qualifier, e.g. 'sample.{overview}.pttp' -> 'overview'
            match = re.search(r'\.\{([^{}]*)\}', os.path.basename(pttp_filename))
            self.presentation_name = match.group(1) if match else ''
            self.presentation_name_action.setText(f'Name: {{{self.presentation_name}}}')

            debugging.print(f'{self.pttd_file_name=}')
            debugging.print(f'{self.pttp_file_name=}')
            debugging.print(f'{self.presentation_name=}')

            self._update_window_title()

            # Reset configuration to baseline (hardcoded defaults + pttplot.ini overrides)
            reset_config_to_baseline()

            # Load per-file presentation configuration from .pttp INI file (tier 3).
            # auto_discovered=True: create basename.{}.pttp from current config if not found.
            load_pttp_config(pttp_filename, auto_discovered=True)
        else:
            # Rule 3: pttd/pttp filenames and presentation config are unchanged
            pttd_filename = self.pttd_file_name
            debugging.print(f'{self.pttd_file_name=}')
            debugging.print(f'{self.pttp_file_name=}')
            debugging.print(f'{self.presentation_name=}')

        # Load data from .pttd file (always, regardless of which rule applied)
        with open(pttd_filename, 'r') as json_file:
            config_dataframe_dict = json.load(json_file)

        # Load and process dataframe
        self.dataframe = pd.DataFrame.from_dict(config_dataframe_dict['dataframe'], orient='index')
        self.dataframe.index = self.dataframe.index.astype(int)     # Convert indexes to integers instead of strings
        self.dataframe = self.dataframe.fillna('')   # Fill missing values with blanks

        # Convert numeric columns to proper data types (JSON loads them as strings)
        numeric_columns = ['StartTime', 'EndTime', 'Duration']
        for col in numeric_columns:
            if col in self.dataframe.columns:
                self.dataframe[col] = pd.to_numeric(self.dataframe[col], errors='coerce')

        self.plot_widget.set_dataframe(self.dataframe)

        # Build process attributes (palette + .pttp overrides) before plotting
        build_process_attributes(self.dataframe)

        self.plot_widget.plot_timeline(self.pttd_file_name)

        # Enable presentation menu items now that a file is loaded
        self.presentation_open_action.setEnabled(True)
        self.presentation_save_action.setEnabled(True)
        self.presentation_process_attributes_action.setEnabled(True)

        # Refresh menu states to reflect new configuration
        self.refresh_menu_states()

        # Refresh open Process Attributes dialog for the new file, or close it
        if self.process_attributes_dialog is not None and self.process_attributes_dialog.isVisible():
            self.process_attributes_dialog.refresh()

        # File loaded successfully — enable file monitoring
        self.file_monitoring_enabled = True

        debugging.leave()
        
    def _update_window_title(self):
        """Update window title to show data filename and current presentation name."""
        if self.pttd_file_name:
            presentation = f'{self.presentation_name}' if self.presentation_name is not None else ''
            self.setWindowTitle(f'{PROGRAM_NAME} - {self.pttd_file_name}  {{{presentation}}}')
        else:
            self.setWindowTitle(PROGRAM_NAME)

    def refresh_menu_states(self):
        """
        Refresh all menu checkbox states to match current configuration.
        Called after loading PTTD files to ensure UI reflects the file's settings.
        """
        debugging.enter()
        
        # Enable and sync Re-Plot On PTTD Change (enabled and checked once a file is loaded)
        self.presentation_replot_action.setEnabled(True)
        self.presentation_replot_action.setChecked(self.file_monitoring_enabled)

        # Update presentation layout menu
        self.presentation_layout_stacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Stacked)
        self.presentation_layout_unstacked_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_STACKING]==CONFIG_PRESENTATION_HBAR_STACKING_Unstacked)
        
        # Update presentation label justification menu
        self.presentation_label_justified_left_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED] == CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Left)
        self.presentation_label_justified_center_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED] == CONFIG_PRESENTATION_HBAR_LABEL_JUSTIFIED_Center)
        
        # Update presentation label rotation menu
        self.presentation_label_rotation_horizontal_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Horizontal)
        self.presentation_label_rotation_slanted_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Slanted)
        self.presentation_label_rotation_vertical_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_HBAR_LABEL_ROTATION] == CONFIG_PRESENTATION_HBAR_LABEL_ROTATION_Vertical)

        # Update dependency arrow mode menu
        self.presentation_dep_arrows_show_pred_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_PREDECESSORS])
        self.presentation_dep_arrows_show_succ_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_SHOW_SUCCESSORS])
        self.presentation_dep_arrows_time_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Time)
        self.presentation_dep_arrows_task_action.setChecked(config[CONFIG_PRESENTATION_OPTIONS][CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE] == CONFIG_PRESENTATION_DEPENDENCY_ARROW_MODE_Task)
        
        debugging.print("Menu states refreshed to match current configuration")
        debugging.leave()
    
    def file_open_dialog(self):
        debugging.enter()
        while True:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Open PTTimeline File", "",
                "PTTimeline Data Files (*.pttd)")
            if not file_name:
                break  # user cancelled
            base = os.path.basename(file_name)
            # Reject .pttd filenames containing {} (reserved for .pttp presentation qualifiers)
            if file_name.lower().endswith('.pttd') and ('{' in base or '}' in base):
                QMessageBox.warning(self, "Invalid Filename",
                    f"'{base}' contains '{{' or '}}' which are reserved for PTTPlot "
                    "presentation qualifiers (e.g. sample.{overview}.pttp) and cannot "
                    "be used in data file names.\n\nPlease choose a different file.")
                continue
            try:
                self.file_name = file_name
                self.load_and_plot(self.file_name)
                self.setup_file_watcher()
            except Exception as e:
                self.file_name = None
                QMessageBox.critical(self, "Error", f"An error occurred while reading the file: {e}")
            break
        debugging.leave()

    def presentation_open_dialog(self):
        """
        Show a dialog listing all .pttp presentations available for the current
        .pttd file.  The user picks one and PTTPlot reloads with that presentation.
        """
        debugging.enter()

        # Scan the directory for matching basename.{*}.pttp files
        base_dir  = os.path.dirname(self.pttd_file_name)
        base_stem = os.path.splitext(os.path.basename(self.pttd_file_name))[0]
        pattern   = re.compile(r'^' + re.escape(base_stem) + r'\.\{([^{}]*)\}\.pttp$', re.IGNORECASE)

        entries = []
        try:
            for fname in sorted(os.listdir(base_dir)):
                m = pattern.match(fname)
                if m:
                    entries.append((m.group(1), os.path.join(base_dir, fname)))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not scan directory: {e}")
            debugging.leave()
            return

        if not entries:
            QMessageBox.information(self, "No Presentations",
                f"No presentation files found for '{base_stem}'.\n\n"
                f"Expected files named: {base_stem}.{{name}}.pttp")
            debugging.leave()
            return

        # Build display labels: qualifier in braces, e.g. '{}', '{overview}'
        labels = [f'{{{name}}}' for name, _ in entries]

        dlg = QDialog(self)
        dlg.setWindowTitle("Open Presentation")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(f"Select a presentation for  {base_stem}.pttd:"))

        list_widget = QListWidget()
        list_widget.addItems(labels)
        # Pre-select the currently loaded presentation
        current_label = f'{{{self.presentation_name}}}'
        matches = list_widget.findItems(current_label, Qt.MatchExactly)
        if matches:
            list_widget.setCurrentItem(matches[0])
        else:
            list_widget.setCurrentRow(0)
        list_widget.itemDoubleClicked.connect(lambda _: dlg.accept())
        layout.addWidget(list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.Accepted:
            debugging.leave()
            return

        row = list_widget.currentRow()
        if row < 0:
            debugging.leave()
            return

        _, pttp_filename = entries[row]
        debugging.print(f'Selected presentation: {pttp_filename}')
        try:
            self.load_and_plot(pttp_filename)
            self.setup_file_watcher()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred loading the presentation: {e}")

        debugging.leave()

    def presentation_save_dialog(self):
        """
        Show a dialog to save the current config as a .pttp presentation file.
        The presentation name (qualifier) is pre-filled and editable.
        Warns before overwriting an existing file.
        """
        debugging.enter()

        from PySide6.QtGui import QRegularExpressionValidator
        from PySide6.QtCore import QRegularExpression

        dlg = QDialog(self)
        dlg.setWindowTitle("Save Presentation")
        layout = QVBoxLayout(dlg)

        base_stem = os.path.splitext(os.path.basename(self.pttd_file_name))[0]
        layout.addWidget(QLabel(f"Save presentation for  {base_stem}.pttd"))
        layout.addWidget(QLabel("Presentation name  (alphanumeric, underscore, hyphen — leave blank for unnamed):"))

        # { name_edit } row
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("{"))
        name_edit = QLineEdit()
        name_edit.setText(self.presentation_name if self.presentation_name else '')
        # Restrict input to [A-Za-z0-9_-] only
        validator = QRegularExpressionValidator(QRegularExpression(r'[A-Za-z0-9_\-]*'))
        name_edit.setValidator(validator)
        name_edit.setMinimumWidth(200)
        name_row.addWidget(name_edit)
        name_row.addWidget(QLabel("}"))
        name_row.addStretch()
        layout.addLayout(name_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.Accepted:
            debugging.leave()
            return

        new_name = name_edit.text().strip()
        base_dir  = os.path.dirname(self.pttd_file_name)
        pttp_filename = os.path.join(base_dir, f'{base_stem}.{{{new_name}}}.pttp')

        # Confirm overwrite if file already exists
        if os.path.exists(pttp_filename):
            reply = QMessageBox.question(self, "Overwrite?",
                f"'{os.path.basename(pttp_filename)}' already exists.\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                debugging.leave()
                return

        try:
            save_pttp_config(pttp_filename)
            self.presentation_name = new_name
            self.presentation_name_action.setText(f'Name: {{{self.presentation_name}}}')
            self.pttp_file_name = pttp_filename
            self._update_window_title()
            debugging.print(f'Saved presentation: {pttp_filename}')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save presentation: {e}")

        debugging.leave()

    def save_as_format(self, fmt, ext, file_filter):
        debugging.enter(f'fmt={fmt}, ext={ext}')
        if self.file_name:
            original_title = self.windowTitle()
            self.setWindowTitle(f"Save File...")
            QApplication.processEvents()
            
            debugging.print(f"{self.pttd_file_name=}")
            debugging.print(f"{self.pttp_file_name=}")
            debugging.print(f"{self.presentation_name=}")

            file_dialog = create_save_dialog_with_custom_bottom_buttons(
                self,
                f"Save {fmt.upper()}",
                self.pttp_file_name.replace(".pttp", ext) if self.pttp_file_name else f"output{ext}",
                file_filter
            )

            if file_dialog.exec():
                image_file_path = file_dialog.selectedFiles()[0]
                debugging.print(f"{image_file_path=}")
                if self.do_save_figure(image_file_path, fmt) and file_dialog.view_after_save:
                    self.launch_pttview(image_file_path, fmt)

            self.setWindowTitle(original_title)
        else:
            QMessageBox.warning(self, "Warning", "No data to save. Please open a file first.")
        debugging.leave()

    def launch_pttview(self, image_file_path, fmt):
        """Launch a viewer to display the saved image file.

        Viewer selection by format:
          - 'pdf' uses pdf_viewer_exe / pdf_viewer_py
          - 'svg' uses svg_viewer_exe / svg_viewer_py
          - all others use viewer_exe / viewer_py

        Resolution order for the selected viewer pair:
          1. viewer_exe non-empty and exists as a file â†’ launch it
          2. viewer_py non-empty â†’ launch via python_exe
          3. both blank â†’ os.startfile() (OS default handler)
        """
        debugging.enter(f'image_file_path={image_file_path}, fmt={fmt}')

        try:
            python_exe = sys.executable

            # Select format-specific viewer config keys
            FORMAT_VIEWER_KEYS = {
                'pdf': (CONFIG_EXTERNAL_PROGRAMS_PDF_VIEWER_PY, CONFIG_EXTERNAL_PROGRAMS_PDF_VIEWER_EXE),
                'svg': (CONFIG_EXTERNAL_PROGRAMS_SVG_VIEWER_PY, CONFIG_EXTERNAL_PROGRAMS_SVG_VIEWER_EXE),
            }
            viewer_py_key, viewer_exe_key = FORMAT_VIEWER_KEYS.get(
                fmt, (CONFIG_EXTERNAL_PROGRAMS_VIEWER_PY, CONFIG_EXTERNAL_PROGRAMS_VIEWER_EXE))

            viewer_exe = config[CONFIG_EXTERNAL_PROGRAMS_OPTIONS][viewer_exe_key]
            viewer_py = config[CONFIG_EXTERNAL_PROGRAMS_OPTIONS][viewer_py_key]

            # Resolve bare filenames to _APP_DIR (same fix as pttedit.py plotter launch)
            if viewer_exe and Path(viewer_exe).parent == Path('.'):
                viewer_exe = f"{_APP_DIR}/{viewer_exe}"
            if viewer_py and not os.path.isabs(viewer_py):
                viewer_py = os.path.join(_APP_DIR, viewer_py)

            # Convert image path to absolute path to avoid working directory issues
            abs_image_path = os.path.abspath(image_file_path)
            debugging.print(f'Absolute image path: {abs_image_path}')
            debugging.print(f'Format: {fmt}, viewer_exe={viewer_exe}, viewer_py={viewer_py}')

            if viewer_exe and os.path.isfile(viewer_exe):
                # Launch the configured executable viewer
                debugging.print(f'Running viewer process: {viewer_exe} {abs_image_path}')
                subprocess.Popen([viewer_exe, abs_image_path])
            elif viewer_py:
                # Launch the configured Python script viewer
                # if not os.path.isabs(viewer_py):
                    # script_dir = os.path.dirname(os.path.abspath(__file__))
                    # abs_viewer_py = os.path.join(script_dir, viewer_py)
                    # debugging.print(f'Converted relative viewer_py to absolute: {abs_viewer_py}')
                # else:
                    # abs_viewer_py = viewer_py
                # debugging.print(f'Running viewer process: {python_exe} {abs_viewer_py} {abs_image_path}')
                # subprocess.Popen([python_exe, abs_viewer_py, abs_image_path])
                debugging.print(f'Running viewer process: {python_exe} {viewer_py} {abs_image_path}')
                subprocess.Popen([python_exe, viewer_py, abs_image_path])
            else:
                # Both viewer_exe and viewer_py are blank â€” use OS default handler
                debugging.print(f'Using OS default handler for: {abs_image_path}')
                os.startfile(abs_image_path)

        except Exception as e:
            debugging.print(f'ERROR launching viewer: {e}')
            QMessageBox.critical(self, "Error", f"Failed to launch viewer: {e}")

        debugging.leave()

    def do_save_figure(self, file_path, fmt):
        """Save the figure in the specified format. Returns True on success."""
        debugging.enter(f'file_path={file_path}, fmt={fmt}')
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            # Save the current zoom state so we can restore it after saving
            ax = self.plot_widget.ax
            saved_xlim = ax.get_xlim()
            saved_ylim = ax.get_ylim()

            # Always save the full plot regardless of current zoom level.
            # Restore the default (full) view before saving so the exported
            # image always shows the complete timeline.
            if self.plot_widget.default_xlim is not None:
                ax.set_xlim(self.plot_widget.default_xlim)
            if self.plot_widget.default_ylim is not None:
                ax.set_ylim(self.plot_widget.default_ylim)

            # Get the current size of the figure
            width, height = self.plot_widget.figure.get_size_inches()
            # Set output size of the figure
            output_width = 16.5
            output_height = 10.5
            self.plot_widget.figure.set_size_inches(output_width, output_height)
            # Save the figure
            debugging.print(f"Saving to: {file_path}")
            save_dpi = config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_SAVE_DPI]
            bbox = 'tight' if fmt != 'svg' else None
            self.plot_widget.figure.savefig(file_path, format=fmt, dpi=save_dpi, bbox_inches=bbox)
            # Reset the size of the figure back to its original size
            self.plot_widget.figure.set_size_inches(width, height)

            # Restore the user's zoom state after saving
            ax.set_xlim(saved_xlim)
            ax.set_ylim(saved_ylim)

            # Redraw canvas to ensure the plot is visible
            self.plot_widget.canvas.draw()

            QApplication.restoreOverrideCursor()
            debugging.leave(f'Success')
            return True
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to save {fmt.upper()}: {e}")
            debugging.leave(f'Error: {e}')
            return False

    def show_about(self):
        """Display About dialog with version and copyright information"""
        debugging.enter()
        
        # Create a custom message box instead of using QMessageBox.about()
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"About {PROGRAM_NAME}")
        
        # Load and set the icon (adjust path as needed)
        icon_path = os.path.join(_RES_DIR, f"{PROGRAM_NAME}.ico")
        if os.path.isfile(icon_path):
            icon = QIcon(icon_path)
            msg_box.setIconPixmap(icon.pixmap(48, 48))  # pixel display size
        else:
            # Fallback to default info icon if file not found
            msg_box.setIcon(QMessageBox.Information)
        
        about_text = f"""
            <h2>{PROGRAM_NAME}</h2>
            <p><b>Version:</b> {APP_VERSION}</p>
            <p><b>Description:</b> {APP_DESCRIPTION}</p>
            <p><b>Author:</b> {APP_AUTHOR}</p>
            <p><b>Company:</b> {APP_COMPANY}</p>
            <p><b>Date:</b> {APP_DATE}</p>
            <p>{APP_COPYRIGHT}</p>
            """
        msg_box.setText(about_text)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.exec()
        
        debugging.leave()


    def show_system_info(self):
        """Display System Information dialog with Python and module versions"""
        debugging.enter()

        # Get Python version
        python_version, python_details = sys.version.split(' ', 1)
        python_build, python_compile = python_details.split(') [', 1)
        python_build = python_build + ')'
        python_compile = '[' + python_compile

        # Get module versions
        module_list = ['PySide6', 'pandas', 'numpy', 'matplotlib', 'configparser', 'platformdirs', 'json5', 'configupdater']
        module_versions = []
        for module_name in module_list:
            try:
                ver = get_module_version(module_name)
                module_versions.append(f"<tr><td>&nbsp;&nbsp;{module_name}</td><td>&nbsp;{ver}</td></tr>")
            except Exception:
                module_versions.append(f"<tr><td>&nbsp;&nbsp;{module_name}</td><td>&nbsp;<i>(version not found)</i></td></tr>")

        # Get OS information with Windows 11 detection
        platform_str = platform.platform()
        os_name = platform.system()
        os_release = platform.release()

        # Check if Windows 11 based on build number
        if os_name == "Windows" and os_release == "10":
            # Format: Windows-10-10.0.BUILDNUMBER-SP0
            build_match = re.search(r'10\.0\.(\d+)', platform_str)
            if build_match:
                build_num = int(build_match.group(1))
                if build_num >= 22000:  # Windows 11 starts at build 22000
                    os_info = f"Windows 11 (Build {build_num})"
                else:
                    os_info = f"Windows 10 (Build {build_num})"
            else:
                os_info = f"{os_name} {os_release}"
        else:
            os_info = f"{os_name} {os_release}"

        # Get file paths
        current_dir = os.getcwd()
        script_path = os.path.dirname(os.path.abspath(__file__))

        sysinfo_text = f"""
            <h3>System Information</h3>
            <p><b>Application:</b> {PROGRAM_NAME} v{APP_VERSION}</p>

            <p><b>Operating System:</b> {os_info}</p>
            <p><b>Platform:</b> {platform_str}</p>

            <p><b>Python Version:</b> {python_version}<br>&nbsp;&nbsp;{python_build}<br>&nbsp;&nbsp;{python_compile}</p>
            <p><b>Third-Party Packages:</b></p
            >
            <table border="0" cellpadding="0">
            {''.join(module_versions)}
            </table>

            <p><b>File Paths:</b></p>
            <table border="0" cellpadding="3">
            <tr><td><b>Working Directory:</b></td><td>{current_dir}</td></tr>
            <tr><td><b>Script Directory:</b></td><td>{script_path}</td></tr>
            <tr><td><b>Config Directory:</b></td><td>{USER_CONFIG_PATH}</td></tr>
            <tr><td><b>Log Directory:</b></td><td>{USER_LOG_PATH}</td></tr>
            <tr><td><b>Debug<br>Logging:</b></td><td><b>Enabled:</b> {debugging_enabled}<br><b>File:</b> {os.path.basename(debugging_filename) if debugging_filename else 'None'}</td></tr>
            </table>
            """
        QMessageBox.about(self, "System Information", sysinfo_text)
        debugging.leave()

    def show_user_guide(self):
        """Open the PTTPlot User Guide HTML file in the default browser."""
        guide_path = Path(_APP_DIR) / "docs" / "PTTPlot_UserGuide.html"
        if guide_path.is_file():
            webbrowser.open_new_tab(guide_path.as_uri())
        else:
            QMessageBox.warning(self, "User Guide Not Found",
                f"The User Guide could not be found:\n{guide_path}")

    def show_help(self):
        """Show help dialog with mouse and keyboard controls"""
        help_text = """
            <h3>PTTPlot - Controls</h3>

            <h4>File Operations:</h4>
            <ul>
            <li><b>File &rarr; Open:</b> Load a .pttd timeline data file</li>
            <li><b>File &rarr; Save:</b> Export chart as PNG, JPG, PDF, or SVG</li>
            </ul>

            <h4>Mouse Wheel (requires Zoom Controls enabled):</h4>
            <ul>
            <li><b>Wheel:</b> Pan up / down</li>
            <li><b>Shift + Wheel:</b> Pan left / right</li>
            <li><b>Ctrl + Wheel:</b> Zoom in / out centered on cursor</li>
            </ul>

            <h4>Click Controls:</h4>
            <ul>
            <li><b>Right-Click on bar:</b> Toggle task info (process, start, end, duration)</li>
            <li><b>Alt + Right-Click on bar:</b> Toggle task info with formula details</li>
            <li><b>Ctrl + Left-Click on bar:</b> Toggle predecessor arrows &mdash; tasks that feed <i>into</i> this task</li>
            <li><b>Ctrl + Right-Click on bar:</b> Toggle successor arrows &mdash; tasks this task feeds <i>into</i></li>
            <li><b>Shift + Ctrl + Left-Click:</b> Toggle predecessor arrows for <i>all</i> tasks</li>
            <li><b>Shift + Ctrl + Right-Click:</b> Toggle successor arrows for <i>all</i> tasks</li>
            </ul>

            <h4>Keyboard:</h4>
            <ul>
            <li><b>F1:</b> Show this help</li>
            </ul>
            """
        QMessageBox.about(self, "Help - Controls", help_text)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_F1:
            self.show_help()
        else:
            super().keyPressEvent(event)

def _build_palette_from_config():
    """
    Return the ordered color palette (list of RGBA tuples) from config.
    Uses [COLORS].color_list if defined and valid; falls back to Tab20.
    """
    from matplotlib.colors import to_rgba

    color_list_str = config[CONFIG_COLORS_OPTIONS][CONFIG_COLORS_COLOR_LIST]

    if color_list_str is None or not color_list_str.strip():
        color_map = plt.get_cmap('tab20')
        return [color_map(i / 20.0) for i in range(20)]

    color_strings = [c.strip() for c in color_list_str.split(',') if c.strip()]
    color_list = []
    for color_str in color_strings:
        try:
            color_list.append(to_rgba(color_str))
        except ValueError as e:
            debugging.print(f"WARNING: Invalid color '{color_str}' in color_list: {e}")

    if not color_list:
        debugging.print("WARNING: All custom colors were invalid — falling back to Tab20")
        color_map = plt.get_cmap('tab20')
        color_list = [color_map(i / 20.0) for i in range(20)]

    return color_list


def build_process_attributes(dataframe):
    """
    Build config['PROCESS_ATTRIBUTES'] for the loaded dataframe.

    Tier sequence:
      1. Assign Tab20 / [COLORS].color_list palette by position (modulo cycling)
         to each unique process name in dataframe order.
      2. Apply per-process overrides from config['PROCESS_ATTRIBUTES']['_overrides']
         — a raw dict of {ProcessName: {attr: value}} staged by load_pttp_config().
         Unknown process names and unknown attribute names are debug-logged and ignored.

    Result: config['PROCESS_ATTRIBUTES'] is a dict keyed by process name, each
    value being an attribute dict (currently {'color': <rgba>}).
    The '_overrides' staging key is retained so save_pttp_config() can round-trip
    the original color strings rather than re-serialising RGBA tuples.
    """
    global config
    from matplotlib.colors import to_rgba

    debugging.enter()

    # --- Tier 1: palette assignment ---
    all_process_names = list(dataframe['ProcessName'])
    excluded_process_names = config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_EXCLUDE_HBAR_GROUPS]
    included_process_names = [p for p in all_process_names if p not in excluded_process_names]
    unique_process_names = list(dict.fromkeys(included_process_names))  # deduplicated, dataframe order

    palette = _build_palette_from_config()
    process_attrs = {}
    for i, name in enumerate(unique_process_names):
        process_attrs[name] = {CONFIG_PROCESS_ATTRIBUTES_COLOR: palette[i % len(palette)]}

    debugging.print(f"Palette-assigned process_attributes: {process_attrs}")

    # --- Tier 2: per-process overrides from [PROCESS_ATTRIBUTES] in .pttp ---
    overrides = config.get(CONFIG_PROCESS_ATTRIBUTES_OPTIONS, {}).get('_overrides', {})
    for proc_name, attrs in overrides.items():
        if proc_name not in process_attrs:
            debugging.print(f"[PROCESS_ATTRIBUTES] unknown process '{proc_name}' — ignored")
            continue
        for attr_name, attr_value in attrs.items():
            if attr_name not in CONFIG_PROCESS_ATTRIBUTES_KNOWN:
                debugging.print(f"[PROCESS_ATTRIBUTES] unknown attribute '{attr_name}' "
                                 f"for process '{proc_name}' — ignored")
                continue
            if attr_name == CONFIG_PROCESS_ATTRIBUTES_COLOR:
                try:
                    color = to_rgba(attr_value)
                    process_attrs[proc_name][CONFIG_PROCESS_ATTRIBUTES_COLOR] = color
                    debugging.print(f"[PROCESS_ATTRIBUTES] override: '{proc_name}' color={attr_value}")
                except ValueError:
                    debugging.print(f"[PROCESS_ATTRIBUTES] invalid color '{attr_value}' "
                                     f"for process '{proc_name}' — ignored")
            else:
                # Future attrs: store raw value directly
                process_attrs[proc_name][attr_name] = attr_value
                debugging.print(f"[PROCESS_ATTRIBUTES] override: '{proc_name}' {attr_name}={attr_value}")

    # Store final table; preserve _overrides so save_pttp_config can write them back
    config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS] = process_attrs
    if overrides:
        config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS]['_overrides'] = overrides

    debugging.print(f"Final process_attributes: {config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS]}")
    debugging.leave()


def _apply_pttp_process_attributes(pttp_cfg):
    """
    Parse [PROCESS_ATTRIBUTES] from a .pttp RawConfigParser using a
    case-preserving parser, and stage the raw overrides into
    config['PROCESS_ATTRIBUTES']['_overrides'] for build_process_attributes()
    to consume after the dataframe is loaded.

    Format per entry:  ProcessName = color=#rrggbb[, attr=value, ...]
    """
    global config

    SECTION = CONFIG_PROCESS_ATTRIBUTES_OPTIONS

    if not pttp_cfg.has_section(SECTION):
        debugging.print(f"No [{SECTION}] section in PTTP file — skipping")
        return

    # Re-read with a case-preserving parser so process names keep their casing.
    case_cfg = configparser.RawConfigParser(comment_prefixes=(';',), inline_comment_prefixes=())
    case_cfg.optionxform = str   # preserve key case
    source_files = getattr(pttp_cfg, '_files', [])
    if source_files:
        case_cfg.read(source_files, encoding='utf-8')
    else:
        debugging.print(f"WARNING: [{SECTION}] cannot recover key casing — "
                         "process name matching may fail")
        case_cfg = pttp_cfg

    if not case_cfg.has_section(SECTION):
        debugging.print(f"[{SECTION}] not found in case-preserving re-read — skipping")
        return

    overrides = {}
    for proc_name in case_cfg.options(SECTION):
        raw_value = case_cfg.get(SECTION, proc_name).strip()
        if not raw_value:
            continue
        # Parse comma-separated attr=value pairs
        attr_dict = {}
        for pair in raw_value.split(','):
            pair = pair.strip()
            if '=' not in pair:
                debugging.print(f"[{SECTION}] '{proc_name}': malformed pair '{pair}' — ignored")
                continue
            attr_name, attr_value = pair.split('=', 1)
            attr_dict[attr_name.strip()] = attr_value.strip()
        if attr_dict:
            overrides[proc_name] = attr_dict

    if overrides:
        if CONFIG_PROCESS_ATTRIBUTES_OPTIONS not in config:
            config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS] = {}
        config[CONFIG_PROCESS_ATTRIBUTES_OPTIONS]['_overrides'] = overrides
        debugging.print(f"[{SECTION}] staged overrides: {overrides}")
    else:
        debugging.print(f"[{SECTION}] section present but no valid entries")


def load_ini():
    global config
    config = load_plot_config(f'{PROGRAM_FILENAME}.ini', DEFAULT_CONFIG, PROGRAM_NAME)


def reset_config_to_baseline():
    """
    Reset configuration to baseline (hardcoded defaults + user INI overrides).
    This ensures each PTTD file starts from a clean slate.
    """
    global config
    debugging.enter()
    config = load_plot_config(f'{PROGRAM_FILENAME}.ini', DEFAULT_CONFIG, PROGRAM_NAME)
    debugging.leave()

def derive_file_pair(filename):
    """
    Derive the .pttd data filename and .{}.pttp presentation filename from
    either a .pttd or .pttp filename passed on the command line or via
    the open dialog.

    Rules:
      - Strip any {qualifier} from the base name to get the data base name.
      - Data file:         <base>.pttd
      - Presentation file: <base>.{<qualifier>}.pttp
        where <qualifier> is empty for the default presentation.

    Examples:
      sample.pttd            -> sample.pttd,    sample.{}.pttp
      sample.{}.pttp         -> sample.pttd,    sample.{}.pttp
      sample.{overview}.pttp -> sample.pttd,    sample.{overview}.pttp
    """
    stem, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext == '.pttp':
        # Extract qualifier (including braces) from stem, e.g. 'sample{overview}' -> qualifier='{overview}'
        match = re.search(r'(\.\{[^{}]*\})$', stem)
        qualifier = match.group(1) if match else '.{}'
        base = stem[:match.start()] if match else stem
    else:
        # .pttd or bare name - no qualifier
        base = stem
        qualifier = '.{}'

    pttd_filename = base + '.pttd'
    pttp_filename = base + qualifier + '.pttp'
    return pttd_filename, pttp_filename


def load_file_ini(pttd_filename):
    """
    Load per-file INI overrides. Looks for <filename>.ini alongside the .pttd file.
    If found, applies its settings over the current config (pttplot.ini baseline).
    """
    global config

    debugging.enter(f'pttd_filename={pttd_filename}')

    ini_filename = os.path.splitext(pttd_filename)[0] + '.ini'
    if not os.path.isfile(ini_filename):
        debugging.print(f"No per-file INI found: {ini_filename}")
        debugging.leave()
        return

    debugging.print(f"Loading per-file INI: {ini_filename}")
    ini_cfg = _make_parser()
    ini_cfg.read(ini_filename, encoding='utf-8')

    _apply_ini_config(ini_cfg, config)

    debugging.print(f"Per-file INI applied: {ini_filename}")
    debugging.leave()

def save_pttp_config(pttp_filename):
    """
    Write the current config to a .pttp INI file.
    Called when auto-creating a default sample.{}.pttp alongside a .pttd file.
    Skips META, DEBUGGING, and EXTERNAL_PROGRAMS sections — those are
    application-level settings, not per-file presentation settings.
    PROCESS_ATTRIBUTES is handled separately with its own comment header and
    one entry per process in palette order (color expressed as hex).
    """
    SKIP_SECTIONS = {'META', 'DEBUGGING', 'EXTERNAL_PROGRAMS', CONFIG_PROCESS_ATTRIBUTES_OPTIONS}

    debugging.enter(f'pttp_filename={pttp_filename}')

    pttp_cfg = _make_parser()
    for section, keys in config.items():
        if section in SKIP_SECTIONS:
            continue
        pttp_cfg.add_section(section)
        for key, value in keys.items():
            if key.startswith('_'):          # skip runtime-only keys like _markers
                continue
            pttp_cfg.set(section, key, str(value))

    try:
        with open(pttp_filename, 'w', encoding='utf-8') as f:
            pttp_cfg.write(f)

            # Write [PROCESS_ATTRIBUTES] section with comment header.
            # One entry per process (palette order); per-process overrides preserved
            # from _overrides if present, else palette color written as hex.
            from matplotlib.colors import to_hex
            f.write(
                '; ==============================================================================\n'
                '; PROCESS_ATTRIBUTES Section\n'
                '; ==============================================================================\n'
                '; Per-process attribute overrides. Applies on top of [COLORS].color_list\n'
                '; palette assignment. ProcessName must match the PTTD exactly (case-sensitive).\n'
                '; Unknown process names and unknown attribute names are ignored (debug-logged).\n'
                ';\n'
                '; Format:  ProcessName = color=#rrggbb\n'
                ';\n'
                '[PROCESS_ATTRIBUTES]\n'
            )
            proc_attrs = config.get(CONFIG_PROCESS_ATTRIBUTES_OPTIONS, {})
            overrides  = proc_attrs.get('_overrides', {})
            for proc_name, attrs in proc_attrs.items():
                if proc_name.startswith('_'):
                    continue
                # Use the override string verbatim if present; otherwise convert
                # the RGBA tuple back to a hex string for readability.
                if proc_name in overrides and CONFIG_PROCESS_ATTRIBUTES_COLOR in overrides[proc_name]:
                    color_str = overrides[proc_name][CONFIG_PROCESS_ATTRIBUTES_COLOR]
                else:
                    rgba = attrs.get(CONFIG_PROCESS_ATTRIBUTES_COLOR, (0.5, 0.5, 0.5, 1.0))
                    color_str = to_hex(rgba)
                f.write(f'{proc_name} = {CONFIG_PROCESS_ATTRIBUTES_COLOR}={color_str}\n')

        debugging.print(f"Created PTTP file: {pttp_filename}")
    except Exception as e:
        debugging.print(f"ERROR creating PTTP file {pttp_filename}: {e}")

    debugging.leave()


def load_pttp_config(pttp_filename, auto_discovered=False):
    """
    Load presentation configuration from a .pttp INI file and merge into
    global config.  This implements the third tier of the config hierarchy:
    PTTP file settings override defaults and pttplot.ini.

    If auto_discovered is True and the file does not exist, it is created
    from the current config (post tiers 1 and 2).  If auto_discovered is
    False (explicitly passed on the command line) and the file does not
    exist, this is a hard error — the caller is responsible for having
    already validated existence before calling here.
    """
    global config

    debugging.enter(f'pttp_filename={pttp_filename}, auto_discovered={auto_discovered}')

    if not os.path.exists(pttp_filename):
        if auto_discovered:
            debugging.print(f"Auto-discovered PTTP not found — creating: {pttp_filename}")
            save_pttp_config(pttp_filename)
        else:
            # Explicitly passed but missing — should have been caught by caller
            debugging.print(f"ERROR: PTTP file not found: {pttp_filename}")
        debugging.leave()
        return

    debugging.print(f"Loading PTTP configuration from: {pttp_filename}")
    pttp_cfg = _make_parser()
    pttp_cfg.read(pttp_filename, encoding='utf-8')
    pttp_cfg._files = [pttp_filename]   # stash path for case-preserving re-read

    _apply_ini_config(pttp_cfg, config)

    # Stage [PROCESS_ATTRIBUTES] overrides for build_process_attributes()
    _apply_pttp_process_attributes(pttp_cfg)

    debugging.print("Final config after PTTP merge:")
    for config_option in config.keys():
        for config_param in config[config_option].keys():
            debugging.print(f"config[{config_option}][{config_param}]={config[config_option][config_param]}, type={type(config[config_option][config_param])}")

    debugging.leave()
    
def parse_command_line_args():
    """Parse and validate command line arguments before any system initialization"""
    # NOTE: No debugging calls here since debugging system not yet initialized

    # Check for too many arguments
    if len(sys.argv) > 2:
        print("Usage: PTTPlot [file_name[.pttd] | file_name.{[presentation_name]}.pttp]")
        sys.exit(1)

    # Get filename if provided
    filename = None
    if len(sys.argv) == 2:
        filename = os.path.abspath(sys.argv[1])
        ext = os.path.splitext(filename)[1].lower()

        # Auto-append .pttd if no recognised extension present
        if ext not in ('.pttd', '.pttp'):
            filename = filename + '.pttd'
            ext = '.pttd'

        # Command line files must always exist
        if not os.path.isfile(filename):
            raise FileNotFoundError(f"{filename}")

        # Derive the file pair and verify the data file exists
        pttd_filename, pttp_filename = derive_file_pair(filename)
        if not os.path.isfile(pttd_filename):
            raise FileNotFoundError(f"Data file not found: {pttd_filename}")

        # For an explicitly passed .pttp, the .pttp file itself must also exist
        # (already checked above via isfile(filename)); no auto-creation here.
        
        filename = Path(filename).resolve()     # Preserves case of the filename

    return filename
    
if __name__ == "__main__":
    # Show splash screen FIRST - before any other initialization
    _splash, _splash_label, _splash_img = show_splash()

    # Install crash logger FIRST - before anything else can fail.
    # USER_LOG_PATH is defined at module level via platformdirs.
    crash_logger = CrashLogger(
        app_name     = PROGRAM_NAME,
        app_version  = APP_VERSION,
        log_dir      = USER_LOG_PATH,
        log_filename = 'pttplot_crash.log',
    )
    crash_logger.install()

    # Parse and validate command line arguments FIRST - before any other initialization
    filename = parse_command_line_args()
    
    load_ini()
    
    debugging_enabled = config['DEBUGGING']['enabled_bool']
    debugging_filename = config['DEBUGGING']['filename']
    if debugging_filename and not os.path.dirname(debugging_filename):
        # Bare filename - place in user log dir
        log_dir = user_log_dir(PACKAGE_NAME, APP_COMPANY)
        os.makedirs(log_dir, exist_ok=True)
        debugging_filename = os.path.join(log_dir, debugging_filename)
    # if (debugging_enabled):
        # print(f'config={config}')
        # print(f'debugging_enabled={debugging_enabled}')
        # print(f'debugging_filename={debugging_filename}')
    debugging.set_output_filename(debugging_filename)
    debugging.set_enabled(debugging_enabled)

    # Log module versions to debug file
    debugging.log_module_versions(module_list=['PySide6', 'pandas', 'numpy', 'configparser', 'platformdirs', 'json5'])
    debugging.print(f"{PROGRAM_NAME} v{APP_VERSION}, {APP_COPYRIGHT}")
    debugging.print("")
    debugging.print(f"{_APP_DIR=}")
    debugging.print(f"{_LIB_DIR=}")
    debugging.print(f"{_RES_DIR=}")
    debugging.print(f"{_CFG_DIR=}")
    
    # Log command line arguments for debugging (after validation completed)
    debugging.print(f'sys.argv({len(sys.argv)}):')
    for n, arg in enumerate(sys.argv):
        debugging.print(f'{n}: {arg}')
    debugging.print(f'Validated filename: {filename}')
    
    debugging.enter()
    
    app = QApplication(sys.argv)
    # Remove Qt's default 256MB image allocation limit - this guard exists to
    # protect against malicious image files but is not relevant here since we
    # are generating our own images. High DPI saves can otherwise be rejected.
    QImageReader.setAllocationLimit(0)
    mainWindow = MainWindow(filename, splash=_splash, splash_label=_splash_label, splash_img=_splash_img)
    if config[CONFIG_PLOTTING_OPTIONS][CONFIG_PLOTTING_WINDOW_MAXIMIZED]:
        mainWindow.showMaximized()
    else:
        mainWindow.show()
    exit_code = app.exec()
    debugging.leave(f'exit_code={exit_code}')
    sys.exit(exit_code)
