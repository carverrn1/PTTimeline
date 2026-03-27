import sys
import os
import platform
import shutil
from pathlib import Path
from importlib.metadata import version as get_module_version

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
    return _show_splash('pttedit_splash.png', _RES_DIR)

# Setup program name and version information
PROGRAM_FILENAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]

capitalize_first_four = lambda s: s[:4].upper() + s[4:]     # Capitalize first 4 letters
from ptt_appinfo import APP_VERSION, APP_COPYRIGHT, APP_AUTHOR, APP_COMPANY, APP_DATE, APP_DESCRIPTION, APP_PACKAGE, APP_ID
PROGRAM_NAME    = capitalize_first_four(PROGRAM_FILENAME)
PACKAGE_NAME    = APP_PACKAGE

from platformdirs import user_config_dir, user_log_dir
USER_CONFIG_PATH = user_config_dir(PACKAGE_NAME, APP_COMPANY)
USER_LOG_PATH = user_log_dir(PACKAGE_NAME, APP_COMPANY)

import re

from collections import OrderedDict

from functools import partial

import subprocess
import webbrowser

import csv
import json5 as json

import pandas as pd
import numpy as np

# Suppress Qt screen warnings before importing Qt modules
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.screen.warning=false;qt.qpa.screen.debug=false'

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QMenuBar, QFileDialog, QVBoxLayout, QWidget, QAbstractItemView, 
    QMenu, QStyledItemDelegate, QLineEdit, QMessageBox, QCompleter, QMessageBox, QHeaderView, QStyle
    )
from PySide6.QtCore import Qt, QRegularExpression, QStringListModel, QEvent
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont, QAction, QRegularExpressionValidator, QKeySequence, QIcon

QT_ROLES = ['Qt.DisplayRole','Qt.DecorationRole','Qt.EditRole','Qt.ToolTipRole','Qt.StatusTipRole','Qt.WhatsThisRole','Qt.SizeHintRole']

config = {}

DEFAULT_CONFIG = """\
[META]
; DO NOT EDIT THIS SECTION! [META] is maintained by the program
app_package=PTTimeline
app_name=PTTEdit
app_version=0.0.0
ini_version=1

[DEBUGGING]
enabled_bool=False
filename=pttedit.dbg

[EXTERNAL_PROGRAMS]
python_exe=python
plotter_py=pttplot.py
plotter_exe=pttplot.exe
"""




from ptt_config import load_edit_config
from ptt_debugging import Debugging, CrashLogger
debugging_enabled = False
debugging_filename = None
debugging = Debugging()
#debugging.exclude_add('HighlightedStandardItem','*')
# debugging.exclude_add('DataFrameModel','recalculateRow')
# debugging.exclude_add('DataFrameEditor','apply_rules_and_populate_model')

import pttedit_expression_evaluator
import pttedit_delegates
pttedit_expression_evaluator.debugging = debugging
pttedit_delegates.debugging = debugging

from pttedit_expression_evaluator import (
    exception_traceback,
    GENERIC_RESULT_ERROR, EXPRESSION_RESULT_ERROR, START_TIME_RESULT_ERROR,
    ENDTIME_RESULT_ERROR, DURATION_RESULT_ERROR, CIRCULAR_REFERENCE_RESULT_ERROR,
    ResultError, ExpressionResultError, StartTimeResultError, EndTimeResultError,
    DurationResultError, CircularReferenceResultError,
    get_object_methods, calculation_error_value,
    BadFormulaError, CircularReferenceError,
    ExpressionEvaluator,
)

from pttedit_delegates import (
    DATA_FILE_EXTENSION,
    PROCESS_NAME_HDR, TASK_NAME_HDR, START_TIME_FORMULA_HDR, START_TIME_HDR,
    END_TIME_FORMULA_HDR, END_TIME_HDR, DURATION_HDR,
    COLUMN_NAMES, TABLE_COLUMN_HEADER_LABELS,
    column_index, COLUMN_WIDTHS, column_width,
    DECIMAL_PLACES_START_TIME, DECIMAL_PLACES_ENDTIME, DECIMAL_PLACES_DURATION,
    formatStartTime, formatEndTime, formatDuration,
    ReadOnlyItemDelegate, ProcessNameItemDelegate, TaskNameItemDelegate,
    FormulaItemDelegate, PosFloatItemDelegate, AnyFloatItemDelegate,
    StartTimeFormulaItemDelegate, StartTimeItemDelegate,
    EndTimeFormulaItemDelegate, EndTimeItemDelegate, DurationItemDelegate,
    HighlightedStandardItem, EditableTableView,
)




class DataFrameModel(QStandardItemModel):
    def __init__(self, *args, **kwargs):
        super(DataFrameModel, self).__init__(*args, **kwargs)
        debugging.enter()
        debugging.leave()

    def setData(self, index, value, role=Qt.EditRole):
        debugging.enter(f'index.row()={index.row()}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}, value={value}({type(value)}), role={QT_ROLES[role]}')
        if role == Qt.EditRole:
            valid = super().setData(index, value, role)
            debugging.print(f'valid={valid}')
            if valid:
                current_value = self.window.dataframe.iloc[index.row(), index.column()]
                debugging.print(f'current_value={current_value}({type(current_value)}), index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')

                if (index.column() == column_index(PROCESS_NAME_HDR)):
                    new_value = str(value)
                elif (index.column() == column_index(TASK_NAME_HDR)):
                    new_value = str(value)
                elif (index.column() == column_index(START_TIME_FORMULA_HDR)):
                    new_value = str(value)
                elif (index.column() == column_index(END_TIME_FORMULA_HDR)):
                    new_value = str(value)
                else:
                    new_value = np.float64(value)

                # Check for duplicate ProcessName:TaskName before accepting the edit
                if index.column() in [column_index(PROCESS_NAME_HDR), column_index(TASK_NAME_HDR)]:
                    # Determine what the ProcessName:TaskName would be after this edit
                    if index.column() == column_index(PROCESS_NAME_HDR):
                        check_process = new_value
                        check_task = self.window.dataframe.iloc[index.row()][TASK_NAME_HDR]
                    else:
                        check_process = self.window.dataframe.iloc[index.row()][PROCESS_NAME_HDR]
                        check_task = new_value

                    # Only check if both names are non-empty
                    if check_process and check_task:
                        for row_idx in range(self.window.dataframe.shape[0]):
                            if row_idx == index.row():
                                continue  # Skip the row being edited
                            existing_process = self.window.dataframe.iloc[row_idx][PROCESS_NAME_HDR]
                            existing_task = self.window.dataframe.iloc[row_idx][TASK_NAME_HDR]
                            if existing_process == check_process and existing_task == check_task:
                                # Duplicate found - revert the edit
                                super().setData(index, current_value, role)
                                QMessageBox.warning(self.window, 'Duplicate Process:Task',
                                    f'"{check_process}:{check_task}" already exists at row {row_idx + 1}.\n'
                                    f'Each Process:Task combination must be unique.')
                                debugging.leave(f'Duplicate rejected: {check_process}:{check_task}')
                                return False

                self.window.dataframe.iloc[index.row(), index.column()] = new_value

                process_name = self.window.dataframe.iloc[index.row()][PROCESS_NAME_HDR]
                task_name = self.window.dataframe.iloc[index.row()][TASK_NAME_HDR]
                column_name = COLUMN_NAMES[index.column()]

                if (index.column() in [column_index(START_TIME_FORMULA_HDR), column_index(END_TIME_FORMULA_HDR)]):
                    result = self.window.evaluator.evaluate_expression(expression=new_value, dependencies=[], referenceLocation=f"{process_name}:{task_name}:{column_name}", callerProcessTask=f"{process_name}:{task_name}")
                    if (isinstance(result, type(ResultError()))):
                        QMessageBox.critical(self.window, 'Expression Error Encountered',
                            f'errorCode: {result.errorCode}\nerrorMessage: {result.errorMessage}\nerrorReference: {result.errorLocation}')
                else:
                    result = 'n/a'

                debugging.print(f'new_value={new_value}({type(new_value)}), result={result}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')

                # Only recalculate if the value actually changed
                value_changed = False
                try:
                    # Handle string comparison
                    if isinstance(new_value, str) and isinstance(current_value, str):
                        value_changed = (new_value != current_value)
                    # Handle float comparison (including NaN)
                    elif isinstance(new_value, (float, np.float64)) and isinstance(current_value, (float, np.float64)):
                        # Check if both are NaN
                        if pd.isna(new_value) and pd.isna(current_value):
                            value_changed = False
                        else:
                            value_changed = (new_value != current_value)
                    else:
                        # Different types or other cases
                        value_changed = True
                except Exception as e:
                    debugging.print(f'Error comparing values: {e}, assuming changed')
                    value_changed = True

                debugging.print(f'current_value={current_value}, new_value={new_value}, value_changed={value_changed}')

                if value_changed:
                    self.window.set_file_modified(True)  # Mark file as modified
                    self.window.table_view.setUpdatesEnabled(False)
                    QApplication.setOverrideCursor(Qt.WaitCursor)

                    edited_column = COLUMN_NAMES[index.column()]
                    process_name = str(self.window.dataframe.iloc[index.row()][PROCESS_NAME_HDR])
                    task_name = str(self.window.dataframe.iloc[index.row()][TASK_NAME_HDR])
                    if process_name == '' and task_name == '':
                        edited_process_task = f"__empty_row_{index.row()}"
                    else:
                        edited_process_task = f"{process_name}:{task_name}"

                    if edited_column in [PROCESS_NAME_HDR, TASK_NAME_HDR]:
                        # Name changed: the old Process:Task key is gone, the new one
                        # now exists. Capture old dependents before rebuilding the graph,
                        # then recalc edited row + old dependents + new dependents only.
                        old_pt = edited_process_task  # edited_process_task is already the NEW name
                        # Reconstruct old key from current_value and the unchanged half
                        if edited_column == TASK_NAME_HDR:
                            old_pt = f"{process_name}:{current_value}"
                        else:
                            old_pt = f"{current_value}:{task_name}"
                        if process_name == '' and task_name == '':
                            old_pt = f"__empty_row_{index.row()}"

                        old_dependent_pts = []
                        if old_pt in self.window.dependency_graph:
                            old_dependent_rows = self.window.get_dependents(old_pt)
                            old_idx_to_pt = {info['row_index']: pt
                                             for pt, info in self.window.dependency_graph.items()}
                            old_dependent_pts = [old_idx_to_pt[r] for r in old_dependent_rows
                                                 if r in old_idx_to_pt]

                        self.window.build_dependency_graph()

                        new_dependent_pts = []
                        if edited_process_task in self.window.dependency_graph:
                            new_dependent_rows = self.window.get_dependents(edited_process_task)
                            new_idx_to_pt = {info['row_index']: pt
                                             for pt, info in self.window.dependency_graph.items()}
                            new_dependent_pts = [new_idx_to_pt[r] for r in new_dependent_rows
                                                 if r in new_idx_to_pt]

                        self.recalculateRow(index.row())
                        seen = set()
                        for pt in old_dependent_pts + new_dependent_pts:
                            if pt not in seen and pt in self.window.dependency_graph:
                                seen.add(pt)
                                self.recalculateRow(self.window.dependency_graph[pt]['row_index'])

                        self.window.update_processname_completer()

                    elif edited_column in [START_TIME_FORMULA_HDR, END_TIME_FORMULA_HDR]:
                        # Formula changed: rebuild graph (dependency edges may have changed)
                        self.window.build_dependency_graph()
                        # Recalculate this row + all transitive dependents
                        self.recalculateRow(index.row())
                        dependent_rows = self.window.get_dependents(edited_process_task)
                        for row_index in dependent_rows:
                            self.recalculateRow(row_index)
                    else:
                        # Other columns: recalculate this row + dependents
                        self.recalculateRow(index.row())
                        dependent_rows = self.window.get_dependents(edited_process_task)
                        for row_index in dependent_rows:
                            self.recalculateRow(row_index)

                    QApplication.restoreOverrideCursor()
                    self.window.table_view.setUpdatesEnabled(True)
                    self.window.update_status_bar("Ready")
                else:
                    # No change, just update status bar
                    self.window.update_status_bar("Ready")
            debugging.leave()
            return valid
        debugging.leave()
        return super().setData(index, value, role)

    def recalculateRow(self, row):
        debugging.enter(f'row={row}')
        process = self.item(row, column_index(PROCESS_NAME_HDR))
        task = self.item(row, column_index(TASK_NAME_HDR))
        start = self.item(row, column_index(START_TIME_HDR))
        end = self.item(row, column_index(END_TIME_HDR))
        duration = self.item(row, column_index(DURATION_HDR))
        start_formula = self.item(row, column_index(START_TIME_FORMULA_HDR))
        end_formula = self.item(row, column_index(END_TIME_FORMULA_HDR))
        debugging.print(f'Before recalculating row: process={process.text()}, task={task.text()}, start_formula={start_formula.text()}, end_formula={end_formula.text()}, start={start.text()}, end={end.text()}, duration={duration.text()}')

        process_task = f"{process.text()}:{task.text()}"

        # try:
            # start_val = float(start.text()) if start and start.text() else None
            # end_val = float(end.text()) if end and end.text() else None
            # duration_val = float(duration.text()) if duration and duration.text() else None

            # # Apply calculations
            # if start_val is not None and end_val is not None:
                # calculated_duration = end_val - start_val
                # self.setItem(row, column_index(DURATION_HDR), HighlightedStandardItem(str(calculated_duration)))
            # elif start_val is not None and duration_val is not None:
                # calculated_end = start_val + duration_val
                # self.setItem(row, column_index(START_TIME_HDR), HighlightedStandardItem(str(calculated_end)))
            # elif end_val is not None and duration_val is not None:
                # calculated_start = end_val - duration_val
                # self.setItem(row, column_index(END_TIME_HDR), HighlightedStandardItem(str(calculated_start)))

            # # Check if cells need to be highlighted
            # for col in [column_index(PROCESS_NAME_HDR), column_index(TASK_NAME_HDR), column_index(START_TIME_HDR), column_index(END_TIME_HDR), column_index(DURATION_HDR)]:
                # item = self.item(row, col)
                # if item:
                    # item.checkHighlight(col=col)
        # except ValueError:
            # pass

        start = self.window.evaluator.evaluate_expression(expression=start_formula.text(), dependencies=[], referenceLocation=f'{process.text()}:{task.text()}:{START_TIME_FORMULA_HDR}', callerProcessTask=process_task)
        self.setItem(row, column_index(START_TIME_HDR), HighlightedStandardItem(formatStartTime(start), column_index(START_TIME_HDR)))
        debugging.print(f"formatStartTime(start)={formatStartTime(start)}")

        end = self.window.evaluator.evaluate_expression(expression=end_formula.text(), dependencies=[], referenceLocation=f'{process.text()}:{task.text()}:{END_TIME_FORMULA_HDR}', callerProcessTask=process_task)
        self.setItem(row, column_index(END_TIME_HDR), HighlightedStandardItem(formatEndTime(end), column_index(END_TIME_HDR)))
        debugging.print(f"formatEndTime(end)={formatEndTime(end)}")

        try:
            duration = end - start
        except Exception as e:
            duration = ExpressionResultError(errorMessage=f'Exception: {e}', errorLocation=f'{process.text()}:{task.text()}:{DURATION_HDR}')
        self.setItem(row, column_index(DURATION_HDR), HighlightedStandardItem(formatDuration(duration), column_index(DURATION_HDR)))
        debugging.print(f"formatDuration(duration)={formatDuration(duration)}")


        process = self.item(row, column_index(PROCESS_NAME_HDR))
        task = self.item(row, column_index(TASK_NAME_HDR))
        start = self.item(row, column_index(START_TIME_HDR))
        end = self.item(row, column_index(END_TIME_HDR))
        duration = self.item(row, column_index(DURATION_HDR))
        start_formula = self.item(row, column_index(START_TIME_FORMULA_HDR))
        end_formula = self.item(row, column_index(END_TIME_FORMULA_HDR))
        debugging.print(f'After recalculating row: process={process.text()}, task={task.text()}, start_formula={start_formula.text()}, end_formula={end_formula.text()}, start={start.text()}, end={end.text()}, duration={duration.text()}')
        debugging.leave()


class DataFrameEditor(QMainWindow):
    def __init__(self, filename=None, splash=None, splash_label=None, splash_img=None):
        super().__init__()
        debugging.enter(f'filename={filename}')
        self.setWindowTitle(f"{PROGRAM_NAME}")
        # Set window icon
        icon_path = os.path.join(_RES_DIR, f"{PACKAGE_NAME}.ico")
        if Path(icon_path).is_file():
            self.setWindowIcon(QIcon(icon_path))
        
        # Store the filename for loading after UI setup
        self.file_name = filename
        self._splash = splash            # stored so load_file_direct can update it
        self._splash_label = splash_label
        self._splash_img = splash_img
        debugging.print(f'command line file: {self.file_name}')
        
        # self.setWindowState(Qt.WindowMaximized)
        self.create_menu()
        self.setup_ui()
        self.model = DataFrameModel()
        self.model.window = self
        # self.model.setHorizontalHeaderLabels(COLUMN_NAMES)
        self.model.setHorizontalHeaderLabels(TABLE_COLUMN_HEADER_LABELS)
        self.table_view.setModel(self.model)
        self.table_view.selectionModel().selectionChanged.connect(self.update_edit_menu_state)
        self.set_fixed_column_widths()
        # Size the window to the width of the table
        self.suggested_window_width = self.table_view.horizontalHeader().length() + 60
        self.suggested_window_height = QApplication.primaryScreen().size().height() // 2
        self.resize(self.suggested_window_width, self.suggested_window_height)
        self.dataframe = None
        self.dependency_graph = {}
        self.recalc_order = []
        self.pt_to_row_index = {}   # Fast O(1) lookup: process_task -> row_index
        self.workingFilename = None
        self.row_copy = None
        self.open_plot = None    # process object for open plotter
        self.close_plot_on_exit = True
        self.evaluator = ExpressionEvaluator()
        
        self.evaluator.register_function('Start',    self.start_time)
        self.evaluator.register_function('End',      self.end_time)
        self.evaluator.register_function('Duration', self.duration_time)
        self.evaluator.register_function('Value',    self.duration_time)

        self.evaluator.register_multiarg_function('Min',            self.min_values)
        self.evaluator.register_multiarg_function('Max',            self.max_values)

        self.evaluator.register_multiarg_function('IsLessThan',     self.is_less_than)
        self.evaluator.register_multiarg_function('IsGreaterThan',  self.is_greater_than)
        self.evaluator.register_multiarg_function('IsLessEqual',    self.is_less_equal)
        self.evaluator.register_multiarg_function('IsGreaterEqual', self.is_greater_equal)
        self.evaluator.register_multiarg_function('IsEqual',        self.is_equal)
        self.evaluator.register_multiarg_function('IsNotEqual',     self.is_not_equal)

        self.evaluator.register_multiarg_function('If',             self.if_value)
        self.evaluator.register_multiarg_function('Not',            self.not_value)
        self.evaluator.register_multiarg_function('Or',             self.or_values)
        self.evaluator.register_multiarg_function('And',            self.and_values)

        self.evaluator.register_multiarg_function('_grp',           self.grp_value)

        # Track file modifications
        self.file_modified = False

        # Create status bar
        self.status_bar = self.statusBar()
        self.status_label = None  # Will hold general status messages
        self.error_label = None   # Will hold error count
        self.setup_status_bar()
        
        # Load file if provided via command line
        if self.file_name:
            self.load_file_direct(self.file_name)

        # Close splash screen now that window is fully ready
        close_splash(splash)

        debugging.leave()
        
    def set_fixed_column_widths(self):
        debugging.enter()
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(column_index(PROCESS_NAME_HDR), QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(column_index(TASK_NAME_HDR), QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(column_index(START_TIME_FORMULA_HDR), QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(column_index(START_TIME_HDR), QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(column_index(END_TIME_FORMULA_HDR), QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(column_index(END_TIME_HDR), QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(column_index(DURATION_HDR), QHeaderView.ResizeMode.Fixed)
        self.table_view.setColumnWidth(column_index(PROCESS_NAME_HDR), column_width(PROCESS_NAME_HDR))
        self.table_view.setColumnWidth(column_index(TASK_NAME_HDR), column_width(TASK_NAME_HDR))
        self.table_view.setColumnWidth(column_index(START_TIME_FORMULA_HDR), column_width(START_TIME_FORMULA_HDR))
        self.table_view.setColumnWidth(column_index(START_TIME_HDR), column_width(START_TIME_HDR))
        self.table_view.setColumnWidth(column_index(END_TIME_FORMULA_HDR), column_width(END_TIME_FORMULA_HDR))
        self.table_view.setColumnWidth(column_index(END_TIME_HDR), column_width(END_TIME_HDR))
        self.table_view.setColumnWidth(column_index(DURATION_HDR), column_width(DURATION_HDR))
        debugging.leave()
    
    def setup_status_bar(self):
        """Initialize the status bar with general status and error count sections"""
        debugging.enter()
        from PySide6.QtWidgets import QLabel
        
        # Left side: General status messages
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)  # Stretch factor 1
        
        # Right side: Error count (permanent widget)
        self.error_label = QLabel("")
        self.status_bar.addPermanentWidget(self.error_label)
        
        self.update_status_bar()
        debugging.leave()
    
    def count_errors(self):
        """Count the number of errors in the calculated columns"""
        debugging.enter()
        error_count = 0
        
        if self.model is not None:
            for row in range(self.model.rowCount()):
                # Check Start, End, and Duration columns for errors
                for col in [column_index(START_TIME_HDR), column_index(END_TIME_HDR), column_index(DURATION_HDR)]:
                    item = self.model.item(row, col)
                    if item and item.text():
                        text = item.text()
                        # Check if text contains any error code
                        if text.endswith(GENERIC_RESULT_ERROR) or 'ERR' in text:
                            error_count += 1
                            break  # Only count one error per row
        
        debugging.leave(f'error_count={error_count}')
        return error_count
    
    def update_status_bar(self, message=None):
        """Update the status bar with current status and error count"""
        debugging.enter(f'message={message}')
        
        # Update general status message if provided
        if message:
            self.status_label.setText(message)
        
        # Update error count
        error_count = self.count_errors()
        
        if error_count > 0:
            self.error_label.setText(f"Errors: {error_count}")
            self.error_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.error_label.setText("No errors")
            self.error_label.setStyleSheet("color: green;")
        
        debugging.leave(f'error_count={error_count}')
    
    def set_file_modified(self, modified=True):
        """Update the modified flag and window title to show unsaved changes"""
        debugging.enter(f'modified={modified}')
        self.file_modified = modified
        
        # Get base title
        if self.workingFilename:
            title = f"{PROGRAM_NAME} - {self.workingFilename}"
        elif "*Demo*" in self.windowTitle():
            title = f"{PROGRAM_NAME} - *Demo*"
        elif "*New*" in self.windowTitle():
            title = f"{PROGRAM_NAME} - *New*"
        else:
            title = f"{PROGRAM_NAME}"
        
        # Add asterisk if modified
        if modified and not title.endswith(" *"):
            title += " *"
        
        self.setWindowTitle(title)
        debugging.leave(f'title={title}')
    
    def check_unsaved_changes(self):
        """
        Check if file has unsaved changes and prompt user.
        Returns True if it's safe to proceed, False if user cancelled.
        """
        debugging.enter(f'file_modified={self.file_modified}')
        if not self.file_modified:
            debugging.leave('No unsaved changes')
            return True
        
        reply = QMessageBox.question(
            self, 
            'Unsaved Changes',
            'You have unsaved changes. Do you want to save before continuing?',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        
        if reply == QMessageBox.Save:
            self.save_timeline_file()
            # If file_modified is still True, user cancelled the save dialog
            result = not self.file_modified
            debugging.leave(f'Save selected, result={result}')
            return result
        elif reply == QMessageBox.Discard:
            debugging.leave('Discard selected')
            return True
        else:  # Cancel
            debugging.leave('Cancel selected')
            return False
    
    
    def create_menu(self):
        debugging.enter()
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_demo_action = QAction("&Demo", self)
        file_demo_action.triggered.connect(self.demo_timeline_file)
        file_menu.addAction(file_demo_action)
        file_new_action = QAction("&New", self)
        file_new_action.triggered.connect(self.new_timeline_file)
        file_menu.addAction(file_new_action)
        file_menu.addSeparator()
        file_open_pttd_action = QAction("&Open", self)
        file_open_pttd_action.triggered.connect(self.open_timeline_from_pttd)
        file_menu.addAction(file_open_pttd_action)
        file_save_action = QAction("&Save", self)
        file_save_action.setShortcut(QKeySequence.Save)  # Ctrl+S
        file_save_action.triggered.connect(self.save_timeline_file)
        file_menu.addAction(file_save_action)
        file_save_as_action = QAction("Save &As...", self)
        file_save_as_action.triggered.connect(self.save_as_timeline_file)
        file_menu.addAction(file_save_as_action)
        file_menu.addSeparator()
        file_import_csv_action = QAction("&Import CSV", self)
        file_import_csv_action.triggered.connect(self.import_timeline_from_csv)
        file_menu.addAction(file_import_csv_action)
        file_append_csv_action = QAction("&Append CSV", self)
        file_append_csv_action.triggered.connect(self.append_timeline_from_csv)
        file_menu.addAction(file_append_csv_action)
        self.file_export_csv_action = QAction("&Export CSV", self)
        self.file_export_csv_action.triggered.connect(self.export_timeline_to_csv)
        self.file_export_csv_action.setEnabled(False)
        file_menu.addAction(self.file_export_csv_action)
        self.file_export_ods_action = QAction("Export &ODS", self)
        self.file_export_ods_action.triggered.connect(self.export_timeline_to_ods)
        self.file_export_ods_action.setEnabled(False)
        file_menu.addAction(self.file_export_ods_action)
        self.file_export_puml_action = QAction("Export &UML Timing Diagram", self)
        self.file_export_puml_action.triggered.connect(self.export_timeline_to_puml)
        self.file_export_puml_action.setEnabled(False)
        file_menu.addAction(self.file_export_puml_action)
        file_menu.addSeparator()
        file_exit_action = QAction("&Exit", self)
        file_exit_action.triggered.connect(self.exit_app)
        file_menu.addAction(file_exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        # Row submenu
        self.edit_row_submenu = edit_menu.addMenu("Row")

        self.edit_row_move_up_action = QAction("Move Row &Up", self)
        self.edit_row_move_up_action.triggered.connect(lambda: self.execute_row_action('move_up'))
        self.edit_row_submenu.addAction(self.edit_row_move_up_action)

        self.edit_row_move_down_action = QAction("Move Row &Down", self)
        self.edit_row_move_down_action.triggered.connect(lambda: self.execute_row_action('move_down'))
        self.edit_row_submenu.addAction(self.edit_row_move_down_action)

        self.edit_row_submenu.addSeparator()

        self.edit_row_add_above_action = QAction("Add Row &Above", self)
        self.edit_row_add_above_action.triggered.connect(lambda: self.execute_row_action('add_above'))
        self.edit_row_submenu.addAction(self.edit_row_add_above_action)

        self.edit_row_add_below_action = QAction("Add Row &Below", self)
        self.edit_row_add_below_action.triggered.connect(lambda: self.execute_row_action('add_below'))
        self.edit_row_submenu.addAction(self.edit_row_add_below_action)

        self.edit_row_submenu.addSeparator()

        self.edit_row_copy_action = QAction("&Copy Row", self)
        self.edit_row_copy_action.triggered.connect(lambda: self.execute_row_action('copy'))
        self.edit_row_submenu.addAction(self.edit_row_copy_action)

        self.edit_row_paste_action = QAction("&Paste Row", self)
        self.edit_row_paste_action.triggered.connect(lambda: self.execute_row_action('paste'))
        self.edit_row_submenu.addAction(self.edit_row_paste_action)

        self.edit_row_submenu.addSeparator()

        self.edit_row_delete_action = QAction("&Delete Row", self)
        self.edit_row_delete_action.triggered.connect(lambda: self.execute_row_action('delete'))
        self.edit_row_submenu.addAction(self.edit_row_delete_action)

        # All row actions start disabled until a row is selected
        self._set_edit_row_actions_enabled(False)

        view_menu = menu_bar.addMenu("&View")
        self.view_plot_action = QAction("&Plot", self)
        self.view_plot_action.triggered.connect(self.plot_timeline)
        view_menu.addAction(self.view_plot_action)
        
        help_menu = menu_bar.addMenu("&Help")

        help_userguide_action = QAction("&User Guide", self)
        help_userguide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(help_userguide_action)

        help_instructions_action = QAction("&Instructions", self)
        help_instructions_action.setShortcut("F1")
        help_instructions_action.triggered.connect(self.show_help)
        help_menu.addAction(help_instructions_action)

        help_menu.addSeparator()

        help_about_action = QAction("&About", self)
        help_about_action.triggered.connect(self.show_about)
        help_menu.addAction(help_about_action)
        help_sysinfo_action = QAction("&System Information", self)
        help_sysinfo_action.triggered.connect(self.show_system_info)
        help_menu.addAction(help_sysinfo_action)
        
        debugging.leave()

    def setup_ui(self):
        debugging.enter()
        # self.table_view = QTableView()
        self.table_view = EditableTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.processNameDelegate = ProcessNameItemDelegate(self.table_view)
        self.processNameDelegate.setCompleterStrings([])
        self.taskNameDelegate = TaskNameItemDelegate(self.table_view)
        self.startTimeFormulaDelegate = StartTimeFormulaItemDelegate(self.table_view)
        self.startTimeDelegate = StartTimeItemDelegate(self.table_view)
        self.endTimeFormulaDelegate = EndTimeFormulaItemDelegate(self.table_view)
        self.endTimeDelegate = EndTimeItemDelegate(self.table_view)
        self.durationDelegate = DurationItemDelegate(self.table_view)
        self.table_view.setItemDelegateForColumn(column_index(PROCESS_NAME_HDR), self.processNameDelegate)
        self.table_view.setColumnWidth(column_index(PROCESS_NAME_HDR), 500)
        self.table_view.setItemDelegateForColumn(column_index(TASK_NAME_HDR), self.taskNameDelegate)
        self.table_view.setItemDelegateForColumn(column_index(START_TIME_FORMULA_HDR), self.startTimeFormulaDelegate)
        self.table_view.setItemDelegateForColumn(column_index(START_TIME_HDR), self.startTimeDelegate)
        self.table_view.setItemDelegateForColumn(column_index(END_TIME_FORMULA_HDR), self.endTimeFormulaDelegate)
        self.table_view.setItemDelegateForColumn(column_index(END_TIME_HDR), self.endTimeDelegate)
        self.table_view.setItemDelegateForColumn(column_index(DURATION_HDR), self.durationDelegate)
        # Connect context menu to vertical header
        self.table_view.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.verticalHeader().customContextMenuRequested.connect(self.vertical_header_context_menu)
        layout = QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(layout)
        layout.addWidget(self.table_view)
        self.setCentralWidget(central_widget)

        # tableview_dir = dir(self.table_view)
        # tableview_methods = get_object_methods(self.table_view)
        # tableview_not_methods = [item for item in tableview_dir if item not in tableview_methods]
        # debugging.print(f'tableview_methods({len(tableview_methods)}): {str(tableview_methods)}')
        # debugging.print(f'tableview_not_methods({len(tableview_not_methods)}): {str(tableview_not_methods)}')
        
        debugging.leave()

    def is_plotter_running(self):
        debugging.enter()
        # Check if plotter is running
        is_plotter_running = True   # assume it is
        if (self.open_plot is None):
            is_plotter_running = False
        else:
            # Plotter was started but is it still running?
            plotter_returncode = self.open_plot.poll()
            if (plotter_returncode is not None):
                # Plotter has finished
                is_plotter_running = False
                self.open_plot = None
        debugging.print(f'is_plotter_running={is_plotter_running}')
        debugging.leave()
        return (is_plotter_running)
    
    def plot_timeline(self):
        debugging.enter()
        debugging.print(f'self.open_plot={self.open_plot}')
        error_count = self.count_errors()
        if error_count > 0:
            QMessageBox.warning(self, 'Cannot Plot',
                f'There {"is" if error_count == 1 else "are"} {error_count} '
                f'{"error" if error_count == 1 else "errors"} in the timeline.\n'
                f'Please fix all errors before plotting.')
            debugging.leave(f'Plot blocked: {error_count} errors')
            return
        if (self.is_plotter_running()):
            button = QMessageBox.information(self, "Plotter already running","Close plotter to open a new plot")
        else:
            current_dir = os.getcwd()
            python_exe = sys.executable
            exe_name = config["EXTERNAL_PROGRAMS"]['plotter_exe']
            script_name = config["EXTERNAL_PROGRAMS"]['plotter_py']
            
            # Get filename - prompt Save As if file hasn't been saved yet
            if self.workingFilename:
                pttd_filename = self.workingFilename
            else:
                self.save_as_timeline_file()
                pttd_filename = self.workingFilename
                if (not pttd_filename): return

            debugging.print(f'File for plotter: {pttd_filename}')
            # Save current timeline data before starting plotter
            self.save_timeline_to_pttd(pttd_filename)
            
            try:
                if (Path(exe_name).parent == Path('.')):            # If no path specified for exe:
                    exe_name = f"{_APP_DIR}/{exe_name}"                 # Prepend the _APP_DIR location
                is_exe_found = Path(exe_name).is_file()             # Does my executable exist
                if (Path(script_name).parent == Path('.')):         # If no path specified for script:
                    script_name = f"{_APP_DIR}/{script_name}"           # Prepend the _APP_DIR location
                is_script_found = Path(script_name).is_file()       # Does my Python script exist
                is_python_found = Path(python_exe).is_file()        # Can the OS find the Python interpretor
                if (is_exe_found):
                    plotter_process_name = f"<{exe_name}>"
                else:
                    plotter_process_name = f"<{python_exe}> <{script_name}>"
                    if (not is_script_found) or (not is_python_found):
                        raise FileNotFoundError
                debugging.print(f'Running plotter process: {plotter_process_name}')
                if (is_exe_found):
                    self.open_plot = subprocess.Popen([exe_name, pttd_filename])
                else:
                    self.open_plot = subprocess.Popen([python_exe, script_name, pttd_filename])
            except FileNotFoundError:
                # Show a critical error dialog if the executable is missing
                QMessageBox.critical(None, "Plotter Not Found", f"Could not find plotter: {plotter_process_name}")
            except Exception as e:
                # Show any other startup exception
                QMessageBox.critical(None, "Plotter Startup Failed", f"An unexpected error occurred: {str(e)}")
                
        debugging.print(f'self.open_plot={self.open_plot}')
        debugging.leave()

    def show_user_guide(self):
        """Open the PTTEdit User Guide HTML file in the default browser."""
        guide_path = Path(_APP_DIR) / "docs" / "PTTEdit_UserGuide.html"
        if guide_path.is_file():
            webbrowser.open_new_tab(guide_path.as_uri())
        else:
            QMessageBox.warning(self, "User Guide Not Found",
                f"The User Guide could not be found:\n{guide_path}")

    def show_help(self):
        """Show help dialog with keyboard and mouse controls."""
        help_text = """
            <h3>PTTEdit - Controls</h3>

            <h4>File Operations:</h4>
            <ul>
            <li><b>Ctrl + N:</b> New - Create a new timeline data file</li>
            <li><b>Ctrl + O:</b> Open - Load an existing .pttd file</li>
            <li><b>Ctrl + S:</b> Save - Save the current file</li>
            <li><b>Ctrl + Shift + S:</b> Save As - Save to a new file</li>
            </ul>

            <h4>Editing:</h4>
            <ul>
            <li><b>Tab / Shift + Tab:</b> Move to next / previous cell</li>
            <li><b>Enter / Return:</b> Confirm edit and move down</li>
            <li><b>Delete:</b> Clear selected cell(s)</li>
            <li><b>Ctrl + Z:</b> Undo</li>
            <li><b>Ctrl + Y:</b> Redo</li>
            </ul>

            <h4>Keyboard:</h4>
            <ul>
            <li><b>F1:</b> Show this help</li>
            </ul>
            """
        QMessageBox.about(self, "Help - Controls", help_text)

    def show_about(self):
        """Display About dialog with version and copyright information"""
        debugging.enter()
        
        # Create a custom message box instead of using QMessageBox.about()
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"About {PROGRAM_NAME}")
        
        # Load and set the icon (adjust path as needed)
        icon_path = os.path.join(_RES_DIR, f"{PROGRAM_NAME}.ico")
        if Path(icon_path).is_file():
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
        # python_version = sys.version.split()[0]
        python_version, python_details = sys.version.split(' ',1)
        python_build, python_compile = python_details.split(') [',1)
        python_build = python_build + ')'
        python_compile = '[' + python_compile
        
        # Get module versions
        module_list = ['PySide6','pandas','numpy','configparser','platformdirs','json5','configupdater','odfpy']
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
            # Extract build number from platform string
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
            <tr><td><b>Debug<br>Logging:</b></td><td><b>Enabled:</b> {debugging_enabled}<br><b>File:</b> {os.path.basename(debugging_filename)}</td></tr>
            </table>
            """
        QMessageBox.about(self, "System Information", sysinfo_text)
        debugging.leave()

    def demo_timeline_file(self):
        debugging.enter()
        if not self.check_unsaved_changes():
            debugging.leave('Cancelled by user')
            return
        
        self.update_status_bar("Loading demo...")
        QApplication.processEvents()  # Force UI update
        self.workingFilename = None
        self.file_export_csv_action.setEnabled(False)
        self.file_export_ods_action.setEnabled(False)
        self.file_export_puml_action.setEnabled(False)
        self.setWindowTitle(f"{PROGRAM_NAME} - *Demo*")
        self.dependency_graph = {}
        self.recalc_order = []
        self.dataframe = pd.DataFrame([
            {PROCESS_NAME_HDR:'Process1', TASK_NAME_HDR:'Task1', 
                START_TIME_FORMULA_HDR:'0.0',
                START_TIME_HDR:None,
                END_TIME_FORMULA_HDR:'1.0',
                END_TIME_HDR:None, DURATION_HDR:None},
            {PROCESS_NAME_HDR:'Process1', TASK_NAME_HDR:'Task2',
                START_TIME_FORMULA_HDR:'End(Process1:Task1)',
                START_TIME_HDR:None,
                END_TIME_FORMULA_HDR:'Start(Process1:Task2)+Duration(Process1:Task1)',
                END_TIME_HDR:None,
                DURATION_HDR:None},
            {PROCESS_NAME_HDR:'Process1', TASK_NAME_HDR:'Task3',
                START_TIME_FORMULA_HDR:'End(Process1:Task2)',
                START_TIME_HDR:None,
                END_TIME_FORMULA_HDR:'Start(Process1:Task3)+Duration(Process1:Task1)',
                END_TIME_HDR:None,
                DURATION_HDR:None},
            {PROCESS_NAME_HDR:'Process1', TASK_NAME_HDR:'Task4',
                START_TIME_FORMULA_HDR:'End(Process1:Task3)',
                START_TIME_HDR:None,
                END_TIME_FORMULA_HDR:'Start(Process1:Task4)+Duration(Process1:Task1)',
                END_TIME_HDR:None,
                DURATION_HDR:None},
            {PROCESS_NAME_HDR:'Process2', TASK_NAME_HDR:'Task1',
                START_TIME_FORMULA_HDR:'Start(Process1:Task2)',
                START_TIME_HDR:None,
                END_TIME_FORMULA_HDR:'Start(Process2:Task1)+2',
                END_TIME_HDR:None, DURATION_HDR:None},
            ])
        debugging.print(f"\nself.dataframe before set_index(ProcessName,TaskName):")
        debugging.print(f"{self.dataframe}")
        # self.dataframe.set_index(['ProcessName', 'TaskName'], drop=False, inplace=True)     # Set the MultiIndex
        debugging.print(f"\nself.dataframe after set_index(ProcessName,TaskName):")
        debugging.print(f"{self.dataframe}")
        self.apply_rules_and_populate_model()
        self.set_fixed_column_widths()
        self.set_file_modified(False)  # Demo is not considered modified
        debugging.leave()

    def new_timeline_file(self):
        debugging.enter()
        if not self.check_unsaved_changes():
            debugging.leave('Cancelled by user')
            return
        
        self.update_status_bar("Creating new file...")
        QApplication.processEvents()  # Force UI update
        self.workingFilename = None
        self.file_export_csv_action.setEnabled(False)
        self.file_export_ods_action.setEnabled(False)
        self.file_export_puml_action.setEnabled(False)
        self.setWindowTitle(f"{PROGRAM_NAME} - *New*")
        self.dependency_graph = {}
        self.recalc_order = []
        self.dataframe = pd.DataFrame([
            {PROCESS_NAME_HDR:'', TASK_NAME_HDR:'', 
                START_TIME_FORMULA_HDR:'0.0',
                START_TIME_HDR:None,
                END_TIME_FORMULA_HDR:'0.0',
                END_TIME_HDR:None, DURATION_HDR:None},
            ])
        # self.dataframe.set_index(['ProcessName', 'TaskName'], inplace=True)     # Set the MultiIndex
        self.apply_rules_and_populate_model()
        self.set_fixed_column_widths()
        self.set_file_modified(False)  # New file is not modified
        debugging.leave()

    def _load_csv_to_dataframe(self, filename):
        """Load a CSV file and return a dataframe.
        Shared by import_timeline_from_csv and append_timeline_from_csv.
        Future field validation should be added here."""
        debugging.enter(f"filename={filename}")
        df = pd.read_csv(filename, dtype={
                            'ProcessName':      'string',
                            'TaskName':         'string',
                            'StartTimeFormula': 'string',
                            'StartTime':        'float64',
                            'EndTimeFormula':   'string',
                            'EndTime':          'float64',
                            'Duration':         'float64'
                        })
        df = df.fillna('')
        debugging.leave()
        return df

    def _resolve_copy_name(self, process, task, existing_pairs):
        """Return a task name that does not collide with existing_pairs for the
        given process.  Appends _COPY_## (incrementing) if needed.
        Reuses the same rename logic as paste."""
        if (process, task) not in existing_pairs:
            return task
        copy_match = re.match(r'^(.+)_COPY_(\d+)$', task)
        if copy_match:
            base_task = copy_match.group(1)
            copy_num  = int(copy_match.group(2)) + 1
        else:
            base_task = task
            copy_num  = 1
        new_task = f'{base_task}_COPY_{copy_num}'
        while (process, new_task) in existing_pairs:
            copy_num += 1
            new_task = f'{base_task}_COPY_{copy_num}'
        return new_task

    def import_timeline_from_csv(self):
        """File->Import CSV: replace the current dataframe with rows from a CSV file."""
        debugging.enter()
        
        if not self.check_unsaved_changes():
            debugging.leave('Cancelled by user')
            return
        
        # Save original title and show status BEFORE dialog
        original_title = self.windowTitle()
        self.setWindowTitle(f"Open File...")
        QApplication.processEvents()  # Update UI immediately
        
        filename, _ = QFileDialog.getOpenFileName(self, "Import CSV File", "", "CSV Files (*.csv)")
        
        if filename:
            # Show busy cursor and status
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.setWindowTitle(f"Opening {os.path.basename(filename)}...")
            self.update_status_bar("Loading file...")
            QApplication.processEvents()  # Update UI immediately
            
            try:
                self.workingFilename = None     # CSV imports data only. None workingFilename forces "Save As" later.
                self.file_export_csv_action.setEnabled(False)
                self.file_export_ods_action.setEnabled(False)
                self.file_export_puml_action.setEnabled(False)
                self.dependency_graph = {}
                self.recalc_order = []
                self.dataframe = self._load_csv_to_dataframe(filename)
                
                debugging.print(f'Imported CSV File: {filename}')
                debugging.print(f'Dataframe:\n{self.dataframe.to_string()}')
                self.apply_rules_and_populate_model()
                
                # Update window title with filename
                self.setWindowTitle(f"{PROGRAM_NAME} - {filename}")
                self.set_file_modified(True)  # Data changed by import
                
            except Exception as e:
                debugging.print(f'ERROR: CSV File: {filename}, e={e}')
                debugging.print(f'Dataframe: {self.dataframe}')
                QMessageBox.critical(self, 'Error Importing CSV File', 
                    f'File: {filename}\nException: {e}')
                self.setWindowTitle(original_title)  # Restore on error
            finally:
                # Always restore cursor
                QApplication.restoreOverrideCursor()
        else:
            # User cancelled - restore original title
            self.setWindowTitle(original_title)
            
        self.set_fixed_column_widths()
        # Size the window to the width of the table
        self.resize(self.suggested_window_width, self.suggested_window_height)

        debugging.leave()

    def append_timeline_from_csv(self):
        """File->Append CSV: add rows from a CSV file to the end of the current dataframe.
        Resolves ProcessName:TaskName collisions using _COPY_## suffix."""
        debugging.enter()

        # Save original title and show status BEFORE dialog
        original_title = self.windowTitle()
        self.setWindowTitle(f"Open File...")
        QApplication.processEvents()  # Update UI immediately

        filename, _ = QFileDialog.getOpenFileName(self, "Append CSV File", "", "CSV Files (*.csv)")

        if filename:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.setWindowTitle(f"Appending {os.path.basename(filename)}...")
            self.update_status_bar("Appending file...")
            QApplication.processEvents()

            try:
                incoming_df = self._load_csv_to_dataframe(filename)

                # Build the set of existing ProcessName:TaskName pairs from the
                # current dataframe; we grow it as we resolve each incoming row
                # so that multiple colliding rows in the CSV each get unique names.
                existing_pairs = set(
                    zip(self.dataframe[PROCESS_NAME_HDR].astype(str),
                        self.dataframe[TASK_NAME_HDR].astype(str))
                )

                resolved_rows = []
                for _, row in incoming_df.iterrows():
                    process = str(row[PROCESS_NAME_HDR])
                    task    = str(row[TASK_NAME_HDR])
                    safe_task = self._resolve_copy_name(process, task, existing_pairs)
                    if safe_task != task:
                        debugging.print(f'Append auto-renamed: {process}:{task} -> {safe_task}')
                        row = row.copy()
                        row[TASK_NAME_HDR] = safe_task
                    existing_pairs.add((process, safe_task))
                    resolved_rows.append(row)

                appended_df = pd.DataFrame(resolved_rows, columns=incoming_df.columns)
                self.dataframe = pd.concat([self.dataframe, appended_df], ignore_index=True)
                self.dependency_graph = {}
                self.recalc_order = []

                debugging.print(f'Appended CSV File: {filename}')
                debugging.print(f'Dataframe:\n{self.dataframe.to_string()}')
                self.apply_rules_and_populate_model()

                self.setWindowTitle(original_title)  # Keep current file title
                self.set_file_modified(True)  # Data changed by append

            except Exception as e:
                debugging.print(f'ERROR: Append CSV: {filename}, e={e}')
                QMessageBox.critical(self, 'Error Appending CSV File',
                    f'File: {filename}\nException: {e}')
                self.setWindowTitle(original_title)
            finally:
                QApplication.restoreOverrideCursor()
        else:
            self.setWindowTitle(original_title)

        self.set_fixed_column_widths()
        self.resize(self.suggested_window_width, self.suggested_window_height)

        debugging.leave()
        
    def open_timeline_from_pttd(self):
        debugging.enter()
        
        if not self.check_unsaved_changes():
            debugging.leave('Cancelled by user')
            return
        
        # Save original title and show status BEFORE dialog
        original_title = self.windowTitle()
        self.setWindowTitle(f"Open File...")
        QApplication.processEvents()  # Update UI immediately
        
        filename, _ = QFileDialog.getOpenFileName(self, f"Open {DATA_FILE_EXTENSION.upper()} File", "", f"{DATA_FILE_EXTENSION.upper()} Files (*.{DATA_FILE_EXTENSION})")
        
        if filename:
            # Show busy cursor and status
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.setWindowTitle(f"Opening {os.path.basename(filename)}...")
            self.update_status_bar("Loading file...")
            QApplication.processEvents()  # Update UI immediately
            
            try:
                self.workingFilename = filename
                self.file_export_csv_action.setEnabled(True)
                self.file_export_ods_action.setEnabled(True)
                self.file_export_puml_action.setEnabled(True)
                self.dependency_graph = {}
                self.recalc_order = []
                with open(self.workingFilename, 'r') as json_file:
                    config_dataframe_dict = json.load(json_file)
                    # print(config_dataframe_dict['dataframe'])
                self.dataframe = pd.DataFrame.from_dict(config_dataframe_dict['dataframe'], 
                                    # dtype={
                                        # 'ProcessName':      'string',
                                        # 'TaskName':         'string',
                                        # 'StartTimeFormula': 'string',
                                        # 'StartTime':        'float64',
                                        # 'EndTimeFormula':   'string',
                                        # 'EndTime':          'float64',
                                        # 'Duration':         'float64'
                                    # },
                                    orient='index')
                self.dataframe.index = self.dataframe.index.astype(int)     # Convert indexes to integers instead of strings
                self.dataframe = self.dataframe.fillna('')   # Fill missing values with blanks
                # self.dataframe.set_index(['ProcessName', 'TaskName'], inplace=True)     # Set the MultiIndex
                
                debugging.print(f'Opened {DATA_FILE_EXTENSION.upper()} File: {filename}')
                debugging.print(f'Dataframe:\n{self.dataframe.to_string()}')
                # print(f'Dataframe:\n{self.dataframe.to_string()}')
                self.apply_rules_and_populate_model()
                
                # Update window title with filename
                self.setWindowTitle(f"{PROGRAM_NAME} - {filename}")
                self.set_file_modified(False)  # File just loaded, not modified
                
            except Exception as e:
                debugging.print(f'ERROR: {DATA_FILE_EXTENSION.upper()} File: {filename}, e={e}')
                debugging.print(f'Dataframe: {self.dataframe}')
                QMessageBox.critical(self, f'Error Opening {DATA_FILE_EXTENSION.upper()} File', 
                    f'File: {filename}\nException: {e}')
                self.setWindowTitle(original_title)  # Restore on error
            finally:
                # Always restore cursor
                QApplication.restoreOverrideCursor()
        else:
            # User cancelled - restore original title
            self.setWindowTitle(original_title)
            
        self.set_fixed_column_widths()
        # Size the window to the width of the table
        self.resize(self.suggested_window_width, self.suggested_window_height)

        debugging.leave()
        
    def load_file_direct(self, filename):
        """Load a PTTD file directly without user dialog (for command line usage)"""
        debugging.enter(f'filename={filename}')
        
        try:
            self.workingFilename = filename
            self.file_export_csv_action.setEnabled(True)
            self.file_export_ods_action.setEnabled(True)
            self.file_export_puml_action.setEnabled(True)
            self.dependency_graph = {}
            self.recalc_order = []
            update_splash(getattr(self, '_splash', None), getattr(self, '_splash_label', None), getattr(self, '_splash_img', None), 'Loading file...')
            with open(self.workingFilename, 'r') as json_file:
                config_dataframe_dict = json.load(json_file)
            self.dataframe = pd.DataFrame.from_dict(config_dataframe_dict['dataframe'], orient='index')
            self.dataframe.index = self.dataframe.index.astype(int)     # Convert indexes to integers instead of strings
            self.dataframe = self.dataframe.fillna('')   # Fill missing values with blanks
            
            debugging.print(f'Loaded {DATA_FILE_EXTENSION.upper()} File: {filename}')
            debugging.print(f'Dataframe:\n{self.dataframe.to_string()}')
            self.apply_rules_and_populate_model()
            
            # Update window title with filename
            self.setWindowTitle(f"{PROGRAM_NAME} - {filename}")
            self.set_file_modified(False)  # File just loaded, not modified
            
        except Exception as e:
            debugging.print(f'ERROR: {DATA_FILE_EXTENSION.upper()} File: {filename}, e={e}')
            debugging.print(f'Dataframe: {self.dataframe}')
            # For command line usage, we'll print error but not show message box during startup
            print(f'Error loading file {filename}: {e}')
            # Keep the default window title since file loading failed
        
        self.set_fixed_column_widths()
        # Size the window to the width of the table
        self.resize(self.suggested_window_width, self.suggested_window_height)
        
        debugging.leave()
        
    def exit_app(self):
        """Called by File->Exit menu action"""
        debugging.enter()
        self.close()  # This triggers closeEvent
        debugging.leave()
        
    def closeEvent(self, event):
        """Override closeEvent to handle window closing properly"""
        debugging.enter(f'event={event}')
        
        # Check for unsaved changes
        if not self.check_unsaved_changes():
            event.ignore()  # User cancelled, don't close
            debugging.leave('Close cancelled by user')
            return
        
        # Safe to close - terminate plotter if running
        if (self.is_plotter_running() and self.close_plot_on_exit):
            self.open_plot.terminate()
        
        event.accept()  # Accept the close event
        debugging.leave()
    
    def update_processname_completer(self):
        debugging.enter()
        processname_list = []
        for row_index in range(self.dataframe.shape[0]):
            # processname = self.dataframe.iloc[row_index, column_index(PROCESS_NAME_HDR)]
            processname = self.dataframe.iloc[row_index][PROCESS_NAME_HDR]
            if (processname):
                processname_list.append(processname)
        processname_list = sorted(list(set(processname_list)))
        debugging.print(f'processname_list={processname_list}')
        self.processNameDelegate.setCompleterStrings(processname_list)
        debugging.leave()

    def calculate_formula(self, formula):
        debugging.enter()
        value = "ERR:"
        debugging.leave(f'value={value}')
        return(value)
    
    def apply_rules_and_populate_model(self):
        debugging.enter()
        self.table_view.setUpdatesEnabled(False)  # Prevent visual blank during model rebuild
        self.model.clear()
        # self.model.setHorizontalHeaderLabels(COLUMN_NAMES)
        self.model.setHorizontalHeaderLabels(TABLE_COLUMN_HEADER_LABELS)
        self.dependency_graph = {}
        self.recalc_order = []
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # Populate model with raw dataframe strings - recalculateRow() will overwrite
        # Start/End/Duration with correct evaluated values immediately after.
        # No expression evaluation here; doing it here and then again in recalculateRow()
        # was redundant and doubled the evaluation work on every full rebuild.
        debugging.print(f'Before dataframe:\n{self.dataframe.to_string()}')
        for row_index, row in self.dataframe.iterrows():
            debugging.print(f'row_index={row_index}, row=\n{row}')
            processed = [HighlightedStandardItem(str(row[col]) if pd.notnull(row[col]) else "") for col in self.dataframe.columns]
            self.model.appendRow(processed)

        debugging.print(f'After dataframe:\n{self.dataframe.to_string()}')

        # Build dependency graph and compute topological recalculation order
        self.build_dependency_graph()

        for row in self.recalc_order:
            self.model.recalculateRow(row)

        self.table_view.setUpdatesEnabled(True)  # Re-enable table updates
        self.update_status_bar("Ready")
        
        QApplication.restoreOverrideCursor()
        
        self.update_processname_completer()
        debugging.leave()

    def build_dependency_graph(self):
        """Build the dependency graph from all formulas in the dataframe.

        Populates self.dependency_graph with forward and reverse edges,
        and computes self.recalc_order (topological sort of row indexes).
        """
        debugging.enter()
        self.dependency_graph = {}

        # Phase 1: Register all Process:Task nodes
        for row_index, row in self.dataframe.iterrows():
            process = str(self.dataframe.iloc[row_index][PROCESS_NAME_HDR])
            task = str(self.dataframe.iloc[row_index][TASK_NAME_HDR])
            # Use sentinel key for rows with both names empty to avoid collisions
            if process == '' and task == '':
                process_task = f"__empty_row_{row_index}"
            else:
                process_task = f'{process}:{task}'
            self.dependency_graph[process_task] = {
                'row_index': row_index,
                'depends_on': set(),
                'dependents': set(),
            }

        # Phase 2: Extract dependencies from formulas and build edges
        for row_index, row in self.dataframe.iterrows():
            process = str(self.dataframe.iloc[row_index][PROCESS_NAME_HDR])
            task = str(self.dataframe.iloc[row_index][TASK_NAME_HDR])
            if process == '' and task == '':
                process_task = f"__empty_row_{row_index}"
            else:
                process_task = f'{process}:{task}'

            start_formula = str(self.dataframe.iloc[row_index][START_TIME_FORMULA_HDR])
            end_formula = str(self.dataframe.iloc[row_index][END_TIME_FORMULA_HDR])

            # Get dependencies from both formulas
            start_deps = self.evaluator.get_expression_dependencies(start_formula, process_task)
            end_deps = self.evaluator.get_expression_dependencies(end_formula, process_task)
            all_deps = start_deps | end_deps

            # Filter to only valid Process:Task keys that exist in the graph
            valid_deps = all_deps & self.dependency_graph.keys()

            # Remove self-dependencies (a row referencing itself is handled by the evaluator)
            valid_deps.discard(process_task)

            self.dependency_graph[process_task]['depends_on'] = valid_deps

            # Build reverse edges (dependents)
            for dep in valid_deps:
                self.dependency_graph[dep]['dependents'].add(process_task)

        # Phase 3: Compute topological sort
        self.recalc_order = self._topological_sort()

        # Phase 4: Build fast O(1) lookup dict for get_df_row_index()
        # Only include real Process:Task keys (not __empty_row_ sentinels)
        self.pt_to_row_index = {
            pt: info['row_index']
            for pt, info in self.dependency_graph.items()
            if not pt.startswith('__empty_row_')
        }

        debugging.print(f'dependency_graph:\n{self.dependency_graph}')
        debugging.print(f'recalc_order:\n{self.recalc_order}')
        debugging.leave()

    def _topological_sort(self):
        """Compute topological sort of dependency graph using Kahn's algorithm.

        Returns a list of row_indexes in safe recalculation order.
        Rows with no dependencies come first.
        If cycles exist, remaining rows are appended at the end (they will
        produce CIRC_ERR during evaluation, which is already handled).
        """
        debugging.enter()

        # Build in-degree count for each node
        in_degree = {}
        for pt, info in self.dependency_graph.items():
            in_degree[pt] = len(info['depends_on'])

        # Start with nodes that have no dependencies
        queue = [pt for pt, deg in in_degree.items() if deg == 0]
        sorted_order = []

        while queue:
            current = queue.pop(0)
            sorted_order.append(current)

            for dependent in self.dependency_graph[current]['dependents']:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Any remaining nodes are part of cycles - append them
        # (circular reference detection in evaluate_expression will catch these)
        for pt in self.dependency_graph:
            if pt not in sorted_order:
                sorted_order.append(pt)

        # Convert to row indexes
        result = [self.dependency_graph[pt]['row_index'] for pt in sorted_order]
        debugging.leave(f'result={result}')
        return result

    def get_dependents(self, process_task):
        """Get all transitive dependents of a Process:Task in topological order.

        Returns a list of row_indexes that need recalculation (NOT including
        the source row itself), in topological order.
        """
        debugging.enter(f'process_task={process_task}')

        if process_task not in self.dependency_graph:
            debugging.leave(f'process_task not in dependency_graph')
            return []

        # BFS to find all transitive dependents
        visited = set()
        queue = list(self.dependency_graph[process_task]['dependents'])
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current in self.dependency_graph:
                queue.extend(self.dependency_graph[current]['dependents'] - visited)

        # Return in topological order (filter recalc_order to only include visited nodes)
        visited_rows = {self.dependency_graph[pt]['row_index'] for pt in visited}
        result = [idx for idx in self.recalc_order if idx in visited_rows]
        debugging.leave(f'result={result}')
        return result

    def save_timeline_to_csv(self, filename):
        """Write the current dataframe to a CSV file at the given full path (including .csv extension)."""
        debugging.enter(f"filename={filename}")
        data = [[self.model.item(row, col).text() for col in range(self.model.columnCount())] for row in range(self.model.rowCount())]
        # df = pd.DataFrame(data, columns=[self.model.horizontalHeaderItem(i).text() for i in range(self.model.columnCount())])
        df = pd.DataFrame(data, columns=[COLUMN_NAMES[i] for i in range(self.model.columnCount())])
        df.to_csv(filename, index=False, quoting=csv.QUOTE_ALL)
        debugging.leave()

    def _write_csv(self, csv_path):
        """Worker: write the dataframe to csv_path (full path, .csv extension).
        Separated from export_timeline_to_csv so a future FileDialog variant
        can call this directly with a user-chosen path."""
        debugging.enter(f"csv_path={csv_path}")
        try:
            self.save_timeline_to_csv(csv_path)
            QMessageBox.information(self, 'Export CSV',
                f'Exported successfully:\n{csv_path}')
        except Exception as e:
            debugging.print(f'ERROR: Export CSV: {csv_path}, e={e}')
            QMessageBox.critical(self, 'Error Exporting CSV',
                f'File: {csv_path}\nException: {e}')
        debugging.leave()

    def export_timeline_to_csv(self):
        """Called by File->Export CSV. Derives the output path from workingFilename,
        prompts before overwriting, then delegates to _write_csv()."""
        debugging.enter()
        csv_path = str(Path(self.workingFilename).with_suffix('.csv'))
        if Path(csv_path).exists():
            result = QMessageBox.question(self, 'Export CSV',
                f'File already exists:\n{csv_path}\n\nOverwrite?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if result != QMessageBox.StandardButton.Yes:
                debugging.leave('Cancelled by user')
                return
        self._write_csv(csv_path)
        debugging.leave()

    
    def save_timeline_to_ods(self, filename):
        """Write the current dataframe to an ODS file at the given full path (including .ods extension).
        Numeric columns (StartTime, EndTime, Duration) are written as floats so that
        LibreOffice Calc and Excel treat them as numbers rather than text."""
        debugging.enter(f"filename={filename}")
        data = [[self.model.item(row, col).text() for col in range(self.model.columnCount())] for row in range(self.model.rowCount())]
        df = pd.DataFrame(data, columns=[COLUMN_NAMES[i] for i in range(self.model.columnCount())])
        for col in (START_TIME_HDR, END_TIME_HDR, DURATION_HDR):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.to_excel(filename, index=False, engine='odf')
        debugging.leave()

    def _write_ods(self, ods_path):
        """Worker: write the dataframe to ods_path (full path, .ods extension)."""
        debugging.enter(f"ods_path={ods_path}")
        try:
            self.save_timeline_to_ods(ods_path)
            QMessageBox.information(self, 'Export ODS',
                f'Exported successfully:\n{ods_path}')
        except Exception as e:
            debugging.print(f'ERROR: Export ODS: {ods_path}, e={e}')
            QMessageBox.critical(self, 'Error Exporting ODS',
                f'File: {ods_path}\nException: {e}')
        debugging.leave()

    def export_timeline_to_ods(self):
        """Called by File->Export ODS. Derives the output path from workingFilename,
        prompts before overwriting, then delegates to _write_ods()."""
        debugging.enter()
        ods_path = str(Path(self.workingFilename).with_suffix('.ods'))
        if Path(ods_path).exists():
            result = QMessageBox.question(self, 'Export ODS',
                f'File already exists:\n{ods_path}\n\nOverwrite?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if result != QMessageBox.StandardButton.Yes:
                debugging.leave('Cancelled by user')
                return
        self._write_ods(ods_path)
        debugging.leave()

    def generate_puml_content(self):
        """Generate PlantUML timing diagram content from the current dataframe.

        Returns a string containing the full .puml file text.

        Design notes:
          - Each task becomes its own 'concise' lifeline: "ProcessName.TaskName"
          - Two states per lifeline: active and idle
          - Gaps between tasks within a process are filled with idle
          - After the last task on a process the lifeline transitions to complete
          - Tasks within the same process may overlap (PTTimeline allows this);
            overlapping pairs are noted as comments in the output
          - Rows with blank ProcessName or TaskName are silently skipped
          - Times are read from the evaluated StartTime / EndTime columns
        """
        debugging.enter()

        # ── Build working dataframe from model ──────────────────────────────
        data = [[self.model.item(row, col).text()
                 for col in range(self.model.columnCount())]
                for row in range(self.model.rowCount())]
        df = pd.DataFrame(data, columns=COLUMN_NAMES)

        # Keep only rows with non-blank process and task names
        df = df[(df[PROCESS_NAME_HDR].str.strip() != '') &
                (df[TASK_NAME_HDR].str.strip()    != '')].copy()

        # Convert time columns to float; rows that fail become NaN and are dropped
        df[START_TIME_HDR] = pd.to_numeric(df[START_TIME_HDR], errors='coerce')
        df[END_TIME_HDR]   = pd.to_numeric(df[END_TIME_HDR],   errors='coerce')
        df = df.dropna(subset=[START_TIME_HDR, END_TIME_HDR])

        if df.empty:
            debugging.leave('no valid rows')
            return None     # caller will report error

        # ── Lifeline alias: "ProcessName.TaskName" → safe alias ─────────────
        # Build ordered list of (process, task) in first-appearance order
        seen = {}
        ordered_lifelines = []
        for _, row in df.iterrows():
            pt = (row[PROCESS_NAME_HDR], row[TASK_NAME_HDR])
            if pt not in seen:
                seen[pt] = True
                ordered_lifelines.append(pt)

        def alias(process, task):
            # Collapse to alphanumeric + underscore for PlantUML identifier
            raw = f"{process}_{task}"
            return re.sub(r'[^A-Za-z0-9_]', '_', raw)

        def label(process, task):
            return f"{process}.{task}"

        # ── Detect intra-process overlaps ────────────────────────────────────
        overlap_comments = []
        process_groups = df.groupby(PROCESS_NAME_HDR, sort=False)
        for proc, grp in process_groups:
            tasks = grp.sort_values(START_TIME_HDR).reset_index(drop=True)
            for i in range(len(tasks)):
                for j in range(i + 1, len(tasks)):
                    a = tasks.iloc[i]
                    b = tasks.iloc[j]
                    # b starts before a ends → overlap
                    if b[START_TIME_HDR] < a[END_TIME_HDR]:
                        overlap_comments.append(
                            f"' WARNING: overlap in process '{proc}': "
                            f"'{a[TASK_NAME_HDR]}' ({a[START_TIME_HDR]}–{a[END_TIME_HDR]}) "
                            f"overlaps '{b[TASK_NAME_HDR]}' ({b[START_TIME_HDR]}–{b[END_TIME_HDR]})"
                        )
                    else:
                        break   # tasks are sorted; no further j can overlap i

        # ── Collect all unique time points in ascending order ─────────────────
        time_points = sorted(set(
            df[START_TIME_HDR].tolist() + df[END_TIME_HDR].tolist()
        ))

        # ── Build per-lifeline state at each time point ───────────────────────
        # state_map[time][alias] = 'active' | 'idle' | 'complete' | None
        # We only emit a state when it changes from the previous time point.

        # For each lifeline track: last_state, last_task_end
        lifeline_info = {}
        for proc, task in ordered_lifelines:
            al = alias(proc, task)
            task_rows = df[(df[PROCESS_NAME_HDR] == proc) &
                           (df[TASK_NAME_HDR]    == task)].sort_values(START_TIME_HDR)
            lifeline_info[al] = {
                'process':  proc,
                'task':     task,
                'intervals': list(zip(task_rows[START_TIME_HDR], task_rows[END_TIME_HDR])),
                'last_end':  task_rows[END_TIME_HDR].max(),
            }

        def state_at(al, t):
            """Return 'active' if t falls within any interval, else None."""
            for (s, e) in lifeline_info[al]['intervals']:
                if s <= t < e:
                    return 'active'
            return None

        # ── Build the .puml text ─────────────────────────────────────────────
        lines = ['@startuml']

        # Lifeline declarations
        for proc, task in ordered_lifelines:
            al = alias(proc, task)
            lines.append(f'concise "{label(proc, task)}" as {al}')

        # Overlap warnings
        if overlap_comments:
            lines.append('')
            lines.extend(overlap_comments)

        # Initial @0 block — all lifelines start idle
        lines.append('')
        lines.append('@0')
        for proc, task in ordered_lifelines:
            al = alias(proc, task)
            lines.append(f'{al} is idle')

        # Walk time points, emit state changes
        current_state = {alias(p, t): 'idle' for p, t in ordered_lifelines}

        for tp in time_points:
            if tp == 0:
                continue    # already emitted in @0 block

            block_lines = []
            for proc, task in ordered_lifelines:
                al = alias(proc, task)
                info = lifeline_info[al]

                # Determine new state at this time point
                active = state_at(al, tp)
                if active == 'active':
                    new_state = 'active'
                elif tp >= info['last_end']:
                    new_state = 'complete'
                else:
                    new_state = 'idle'

                if new_state != current_state[al]:
                    block_lines.append(f'{al} is {new_state}')
                    current_state[al] = new_state

            if block_lines:
                # Format time: strip trailing zeros after decimal for cleanliness
                tp_str = f'{tp:g}'
                lines.append('')
                lines.append(f'@{tp_str}')
                lines.extend(block_lines)

        lines.append('')
        lines.append('@enduml')
        lines.append('')    # trailing newline

        debugging.leave()
        return '\n'.join(lines)

    def _write_puml(self, puml_path):
        """Worker: generate and write the .puml file to puml_path."""
        debugging.enter(f"puml_path={puml_path}")
        try:
            content = self.generate_puml_content()
            if content is None:
                QMessageBox.warning(self, 'Export UML Timing Diagram',
                    'Nothing to export — no rows with valid process names, '
                    'task names, and evaluated times.')
                debugging.leave('no content')
                return
            with open(puml_path, 'w', encoding='utf-8') as f:
                f.write(content)
            QMessageBox.information(self, 'Export UML Timing Diagram',
                f'Exported successfully:\n{puml_path}')
        except Exception as e:
            debugging.print(f'ERROR: Export PUML: {puml_path}, e={e}')
            QMessageBox.critical(self, 'Error Exporting UML Timing Diagram',
                f'File: {puml_path}\nException: {e}')
        debugging.leave()

    def export_timeline_to_puml(self):
        """Called by File->Export UML Timing Diagram. Derives the output path
        from workingFilename, prompts before overwriting, then delegates to
        _write_puml()."""
        debugging.enter()
        puml_path = str(Path(self.workingFilename).with_suffix('.puml'))
        if Path(puml_path).exists():
            result = QMessageBox.question(self, 'Export UML Timing Diagram',
                f'File already exists:\n{puml_path}\n\nOverwrite?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if result != QMessageBox.StandardButton.Yes:
                debugging.leave('Cancelled by user')
                return
        self._write_puml(puml_path)
        debugging.leave()


    def save_timeline_to_pttd(self, filename):
        global config
        debugging.enter(f"filename={filename}")
        data = [[self.model.item(row, col).text() for col in range(self.model.columnCount())] for row in range(self.model.rowCount())]
        # df = pd.DataFrame(data, columns=[self.model.horizontalHeaderItem(i).text() for i in range(self.model.columnCount())])
        df = pd.DataFrame(data, columns=[COLUMN_NAMES[i] for i in range(self.model.columnCount())])
        df_json = df.to_json(orient ='index', force_ascii=True)
        config_dataframe_dict = {
            'config':config,
            'dataframe':json.loads(df_json)
            }
        with open(f"{filename}", 'w') as json_file:
            json.dump(config_dataframe_dict, json_file, indent=4)

        self.set_file_modified(False)  # File saved, no longer modified 
        debugging.leave()
    
    def save_timeline_file(self):
        debugging.enter()

        # Commit any active cell editor before saving so the current edit is included
        self.table_view.setFocus()

        # If we have a working filename, save directly without prompting
        if self.workingFilename and not self.windowTitle().endswith("*Demo*") and not self.windowTitle().endswith("*New*"):
            # Show busy cursor and status
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.setWindowTitle(f"Saving {os.path.basename(self.workingFilename)}...")
            self.update_status_bar("Saving file...")
            QApplication.processEvents()  # Update UI immediately
            
            try:
                # self.save_timeline_to_csv(self.workingFilename)
                self.save_timeline_to_pttd(self.workingFilename)
                # set_file_modified(False) is called inside save_timeline_to_pttd,
                # which also sets the window title correctly — no manual fixup needed here
                self.update_status_bar("Ready")
                
            except Exception as e:
                debugging.print(f'ERROR: Saving File: {self.workingFilename}, e={e}')
                QMessageBox.critical(self, 'Error Saving File', 
                    f'File: {self.workingFilename}\nException: {e}')
                self.set_file_modified(self.file_modified)  # Restore title to pre-save state
            finally:
                # Always restore cursor
                QApplication.restoreOverrideCursor()
        else:
            # No filename yet, or Demo/New file - use Save As dialog
            self.save_as_timeline_file()
                
        debugging.leave()
    
    def save_as_timeline_file(self):
        debugging.enter()

        # Commit any active cell editor before saving so the current edit is included
        self.table_view.setFocus()
        
        # Save original title and show status BEFORE dialog
        original_title = self.windowTitle()
        self.setWindowTitle(f"Save File...")
        QApplication.processEvents()  # Update UI immediately
        
        fileDialog = QFileDialog()
        if (self.workingFilename):
            path, filename = os.path.split(self.workingFilename)
            fileDialog.setDirectory(path)
            fileDialog.selectFile(filename) # Doesn't seem to work. Might require a custom Save dialog :(
        filename, _ = fileDialog.getSaveFileName(self, "Save PTTD File", "", "PTTD Files (*.pttd)")
        
        if filename:
            # Show busy cursor and status
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.setWindowTitle(f"Saving {os.path.basename(filename)}...")
            self.update_status_bar("Saving file...")
            QApplication.processEvents()  # Update UI immediately
            
            try:
                self.workingFilename = filename
                self.file_export_csv_action.setEnabled(True)
                self.file_export_ods_action.setEnabled(True)
                self.file_export_puml_action.setEnabled(True)
                self.save_timeline_to_pttd(filename)
                # set_file_modified(False) is called inside save_timeline_to_pttd,
                # which also sets the window title correctly — no manual fixup needed here
                self.update_status_bar("Ready")
                
            except Exception as e:
                debugging.print(f'ERROR: Saving File: {filename}, e={e}')
                QMessageBox.critical(self, 'Error Saving File', 
                    f'File: {filename}\nException: {e}')
                self.setWindowTitle(original_title)  # Restore on error
            finally:
                # Always restore cursor
                QApplication.restoreOverrideCursor()
        else:
            # User cancelled - restore original title
            self.setWindowTitle(original_title)
                
        debugging.leave()

    def _swap_model_rows(self, row_a, row_b):
        """Swap all item data between two Qt model rows in-place.

        Also updates the row_index bookkeeping in dependency_graph so that
        the graph remains consistent without a full rebuild.
        No recalculation is needed: formulas reference Process:Task by name,
        not by row position, so calculated values are unaffected by a swap.
        """
        debugging.enter(f'row_a={row_a}, row_b={row_b}')
        num_cols = self.model.columnCount()
        for col in range(num_cols):
            # Take both items out of the model before placing either one back.
            # takeItem() transfers ownership to Python, preventing Qt from
            # deleting the C++ object when setItem() replaces the slot.
            item_a = self.model.takeItem(row_a, col)
            item_b = self.model.takeItem(row_b, col)
            self.model.setItem(row_a, col, item_b)
            self.model.setItem(row_b, col, item_a)

        # Update dependency_graph row_index entries and pt_to_row_index for the two swapped rows
        for pt, info in self.dependency_graph.items():
            if info['row_index'] == row_a:
                info['row_index'] = row_b
                if pt in self.pt_to_row_index:
                    self.pt_to_row_index[pt] = row_b
            elif info['row_index'] == row_b:
                info['row_index'] = row_a
                if pt in self.pt_to_row_index:
                    self.pt_to_row_index[pt] = row_a

        debugging.leave()

    def move_row_up(self, selected_row_index):
        debugging.enter(f'selected_row_index={selected_row_index}')
        move_to_row_index = selected_row_index - 1
        temp = self.dataframe.iloc[selected_row_index].copy()
        self.dataframe.iloc[selected_row_index] = self.dataframe.iloc[move_to_row_index]
        self.dataframe.iloc[move_to_row_index] = temp
        debugging.leave(f'selected_row_index={selected_row_index}, move_to_row_index={move_to_row_index}')

    def move_row_down(self, selected_row_index):
        debugging.enter(f'selected_row_index={selected_row_index}')
        move_to_row_index = selected_row_index + 1
        temp = self.dataframe.iloc[selected_row_index].copy()
        self.dataframe.iloc[selected_row_index] = self.dataframe.iloc[move_to_row_index]
        self.dataframe.iloc[move_to_row_index] = temp
        debugging.leave(f'selected_row_index={selected_row_index}, move_to_row_index={move_to_row_index}')

    def add_row_above(self, selected_row_index):
        rows_before = self.dataframe.shape[0]
        debugging.enter(f'selected_row_index={selected_row_index}, rows_before={rows_before}')
        # Insert empty row into the dataframe
        empty_row = pd.DataFrame({PROCESS_NAME_HDR:'', TASK_NAME_HDR:'', START_TIME_FORMULA_HDR:'0.0', START_TIME_HDR:0.0, END_TIME_FORMULA_HDR:'0.0', END_TIME_HDR:0.0, DURATION_HDR:0.0}, index=[0])
        before_df = self.dataframe.iloc[:selected_row_index]  # Rows before the insertion point
        after_df = self.dataframe.iloc[selected_row_index:]
        after_df.reset_index(drop=True, inplace=True)   # Resetting index to avoid duplicate indexes
        self.dataframe = pd.concat([before_df, empty_row, after_df]).reset_index(drop=True)
        rows_after = self.dataframe.shape[0]
        debugging.leave(f'selected_row_index={selected_row_index}, rows_after={rows_after}')
        
    def add_row_below(self, selected_row_index):
        rows_before = self.dataframe.shape[0]
        debugging.enter(f'selected_row_index={selected_row_index}, rows_before={rows_before}')
        # Insert empty row into the dataframe
        empty_row = pd.DataFrame({PROCESS_NAME_HDR:'', TASK_NAME_HDR:'', START_TIME_FORMULA_HDR:'0.0', START_TIME_HDR:0.0, END_TIME_FORMULA_HDR:'0.0', END_TIME_HDR:0.0, DURATION_HDR:0.0}, index=[0])
        before_df = self.dataframe.iloc[:selected_row_index + 1]  # Rows before the insertion point
        after_df = self.dataframe.iloc[selected_row_index + 1:]
        after_df.reset_index(drop=True, inplace=True)   # Resetting index to avoid duplicate indexes
        self.dataframe = pd.concat([before_df, empty_row, after_df]).reset_index(drop=True)
        rows_after = self.dataframe.shape[0]
        debugging.leave(f'selected_row_index={selected_row_index}, rows_after={rows_after}')
        
    def delete_row_at(self, selected_row_index, row_index_list, dependent_pts=None):
        rows_before = self.dataframe.shape[0]
        debugging.enter(f'selected_row_index={selected_row_index}, rows_before={rows_before}')
        confirm_delete_msg = 'Are you sure you want to delete row(s):'
        for row_index in row_index_list:
            process_name = self.dataframe.iloc[row_index][PROCESS_NAME_HDR]
            task_name = self.dataframe.iloc[row_index][TASK_NAME_HDR]
            line_msg = f'\n  Row {row_index+1}: "{process_name}:{task_name}"'
            confirm_delete_msg += line_msg
        if dependent_pts:
            confirm_delete_msg += '\n\nWARNING: The following rows directly depend on this row!'
            for pt in dependent_pts:
                confirm_delete_msg += f'\n  {pt}'
        debugging.print(f'confirm_delete_msg:\n{confirm_delete_msg}')
        reply = QMessageBox.question(self, 'Delete Confirmation',
                                        confirm_delete_msg,
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            debugging.print('Delete CONFIRMED by user!')
            # Delete row from dataframe
            self.dataframe.drop(selected_row_index, inplace=True)
            self.dataframe.reset_index(drop=True, inplace=True)   # Resetting index to avoid duplicate indexes
            self.set_file_modified(True)  # Mark as modified only if delete confirmed
            rows_after = self.dataframe.shape[0]
            debugging.leave(f'confirmed, rows_after={rows_after}')
            return True
        else:
            debugging.print('Delete CANCELLED by user!')
            rows_after = self.dataframe.shape[0]
            debugging.leave(f'cancelled, rows_after={rows_after}')
            return False
    
    def _set_edit_row_actions_enabled(self, enabled):
        """Enable or disable all Edit > Row submenu actions at once."""
        self.edit_row_move_up_action.setEnabled(enabled)
        self.edit_row_move_down_action.setEnabled(enabled)
        self.edit_row_add_above_action.setEnabled(enabled)
        self.edit_row_add_below_action.setEnabled(enabled)
        self.edit_row_copy_action.setEnabled(enabled)
        self.edit_row_paste_action.setEnabled(enabled)
        self.edit_row_delete_action.setEnabled(enabled)

    def update_edit_menu_state(self):
        """Update Edit > Row action enabled states based on current selection."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows or self.dataframe is None or self.dataframe.shape[0] == 0:
            self._set_edit_row_actions_enabled(False)
            return

        # A row is selected — enable all, then conditionally disable some
        self._set_edit_row_actions_enabled(True)

        row_index = selected_rows[0].row()
        row_max = self.dataframe.shape[0] - 1

        if row_index == 0:
            self.edit_row_move_up_action.setEnabled(False)
        if row_index == row_max:
            self.edit_row_move_down_action.setEnabled(False)
        if self.row_copy is None:
            self.edit_row_paste_action.setEnabled(False)

    def execute_row_action(self, action_name, row_index=None):
        """Execute a row editing action by name.

        If row_index is None, uses the current table selection.
        Called by both the Edit menu and the right-click context menu.
        """
        debugging.enter(f'action_name={action_name}, row_index={row_index}')

        # Get row_index from selection if not provided (Edit menu path)
        if row_index is None:
            selected_rows = self.table_view.selectionModel().selectedRows()
            if not selected_rows:
                debugging.leave('no row selected')
                return
            row_index = selected_rows[0].row()

        if self.dataframe is None or self.dataframe.shape[0] == 0:
            debugging.leave('no dataframe')
            return

        row_max = self.dataframe.shape[0] - 1
        selected_model_indexes = self.table_view.selectedIndexes()
        selected_row_indexes = list(set([index.row() for index in selected_model_indexes]))

        target_row_index = None  # Track which row to navigate to after model rebuild

        debugging.print(f'{action_name}: row_index={row_index}')

        if action_name == 'move_up' and row_index > 0:
            self.move_row_up(row_index)
            self._swap_model_rows(row_index, row_index - 1)
            self.set_file_modified(True)
            target_row_index = row_index - 1
            # Navigate to target row - no rebuild needed
            self.table_view.selectRow(target_row_index)
            self.table_view.scrollTo(self.model.index(target_row_index, column_index(PROCESS_NAME_HDR)))
            self.update_edit_menu_state()
            debugging.leave()
            return
        elif action_name == 'move_down' and row_index < row_max:
            self.move_row_down(row_index)
            self._swap_model_rows(row_index, row_index + 1)
            self.set_file_modified(True)
            target_row_index = row_index + 1
            # Navigate to target row - no rebuild needed
            self.table_view.selectRow(target_row_index)
            self.table_view.scrollTo(self.model.index(target_row_index, column_index(PROCESS_NAME_HDR)))
            self.update_edit_menu_state()
            debugging.leave()
            return
        elif action_name == 'add_above' and row_index >= 0:
            self.add_row_above(row_index)
            self.set_file_modified(True)
            target_row_index = row_index
            # Fast path: insert blank row into model directly, rebuild graph, recalc new row only
            self.table_view.setUpdatesEnabled(False)
            self.model.insertRow(row_index)
            _add_row_init = {
                column_index(PROCESS_NAME_HDR):      '',
                column_index(TASK_NAME_HDR):         '',
                column_index(START_TIME_FORMULA_HDR):'0.0',
                column_index(END_TIME_FORMULA_HDR):  '0.0',
                column_index(START_TIME_HDR):        '',
                column_index(END_TIME_HDR):          '',
                column_index(DURATION_HDR):          '',
            }
            for col in range(self.model.columnCount()):
                self.model.setItem(row_index, col, HighlightedStandardItem(_add_row_init[col], col))
            self.build_dependency_graph()
            self.model.recalculateRow(row_index)
            self.table_view.setUpdatesEnabled(True)
            self.update_status_bar("Ready")
            self.update_processname_completer()
            self.table_view.selectRow(target_row_index)
            self.table_view.scrollTo(self.model.index(target_row_index, column_index(PROCESS_NAME_HDR)))
            self.update_edit_menu_state()
            debugging.leave()
            return
        elif action_name == 'add_below' and row_index >= 0:
            self.add_row_below(row_index)
            self.set_file_modified(True)
            target_row_index = row_index + 1
            # Fast path: insert blank row into model directly, rebuild graph, recalc new row only
            self.table_view.setUpdatesEnabled(False)
            self.model.insertRow(target_row_index)
            _add_row_init = {
                column_index(PROCESS_NAME_HDR):      '',
                column_index(TASK_NAME_HDR):         '',
                column_index(START_TIME_FORMULA_HDR):'0.0',
                column_index(END_TIME_FORMULA_HDR):  '0.0',
                column_index(START_TIME_HDR):        '',
                column_index(END_TIME_HDR):          '',
                column_index(DURATION_HDR):          '',
            }
            for col in range(self.model.columnCount()):
                self.model.setItem(target_row_index, col, HighlightedStandardItem(_add_row_init[col], col))
            self.build_dependency_graph()
            self.model.recalculateRow(target_row_index)
            self.table_view.setUpdatesEnabled(True)
            self.update_status_bar("Ready")
            self.update_processname_completer()
            self.table_view.selectRow(target_row_index)
            self.table_view.scrollTo(self.model.index(target_row_index, column_index(PROCESS_NAME_HDR)))
            self.update_edit_menu_state()
            debugging.leave()
            return
        elif action_name == 'copy' and row_index >= 0:
            self.row_copy = self.dataframe.iloc[row_index].copy()
            debugging.print(f'row_copy: {self.row_copy}')
            # Don't set modified for copy, don't rebuild model
            self.update_edit_menu_state()
            debugging.leave()
            return
        elif action_name == 'paste' and row_index >= 0 and self.row_copy is not None:
            # Auto-rename TaskName to avoid duplicate ProcessName:TaskName
            paste_row = self.row_copy.copy()
            paste_process = paste_row[PROCESS_NAME_HDR]
            paste_task = paste_row[TASK_NAME_HDR]
            if paste_task:  
                existing_pairs = set()
                for check_row in range(self.dataframe.shape[0]):
                    if check_row == row_index:
                        continue
                    existing_pairs.add((self.dataframe.iloc[check_row][PROCESS_NAME_HDR],
                                        self.dataframe.iloc[check_row][TASK_NAME_HDR]))

                if (paste_process, paste_task) in existing_pairs:
                    copy_match = re.match(r'^(.+)_COPY_(\d+)$', paste_task)
                    if copy_match:
                        base_task = copy_match.group(1)
                        copy_num = int(copy_match.group(2)) + 1
                    else:
                        base_task = paste_task
                        copy_num = 1

                    new_task = f'{base_task}_COPY_{copy_num}'
                    while (paste_process, new_task) in existing_pairs:
                        copy_num += 1
                        new_task = f'{base_task}_COPY_{copy_num}'

                    paste_row[TASK_NAME_HDR] = new_task
                    debugging.print(f'Paste auto-renamed: {paste_task} -> {new_task}')

            # Capture old Process:Task key and its dependents before overwriting
            old_process = str(self.dataframe.iloc[row_index][PROCESS_NAME_HDR])
            old_task    = str(self.dataframe.iloc[row_index][TASK_NAME_HDR])
            if old_process == '' and old_task == '':
                old_pt = f'__empty_row_{row_index}'
            else:
                old_pt = f'{old_process}:{old_task}'
            old_dependent_pts = []
            if old_pt in self.dependency_graph:
                old_dependent_rows = self.get_dependents(old_pt)
                old_idx_to_pt = {info['row_index']: pt
                                 for pt, info in self.dependency_graph.items()}
                old_dependent_pts = [old_idx_to_pt[r] for r in old_dependent_rows
                                     if r in old_idx_to_pt]

            self.dataframe.iloc[row_index] = paste_row
            self.row_copy = None
            self.set_file_modified(True)
            target_row_index = row_index

            # Fast path: update model items directly, rebuild graph, targeted recalc
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.table_view.setUpdatesEnabled(False)

            # Update the 7 model items for the pasted row
            for col, col_name in enumerate(COLUMN_NAMES):
                val = paste_row[col_name]
                self.model.setItem(row_index, col,
                                   HighlightedStandardItem(str(val) if pd.notnull(val) else '', col))

            self.build_dependency_graph()

            # Recalculate: pasted row + old dependents (now broken) + new dependents
            new_process = str(paste_row[PROCESS_NAME_HDR])
            new_task    = str(paste_row[TASK_NAME_HDR])
            if new_process == '' and new_task == '':
                new_pt = f'__empty_row_{row_index}'
            else:
                new_pt = f'{new_process}:{new_task}'
            new_dependent_pts = []
            if new_pt in self.dependency_graph:
                new_dependent_rows = self.get_dependents(new_pt)
                new_idx_to_pt = {info['row_index']: pt
                                 for pt, info in self.dependency_graph.items()}
                new_dependent_pts = [new_idx_to_pt[r] for r in new_dependent_rows
                                     if r in new_idx_to_pt]

            # Recalculate pasted row first, then all affected dependents (deduplicated)
            self.model.recalculateRow(row_index)
            seen = set()
            for pt in old_dependent_pts + new_dependent_pts:
                if pt not in seen and pt in self.dependency_graph:
                    seen.add(pt)
                    self.model.recalculateRow(self.dependency_graph[pt]['row_index'])

            self.table_view.setUpdatesEnabled(True)
            self.update_status_bar("Ready")
            QApplication.restoreOverrideCursor()
            self.update_processname_completer()
            self.table_view.selectRow(target_row_index)
            self.table_view.scrollTo(self.model.index(target_row_index, column_index(PROCESS_NAME_HDR)))
            self.update_edit_menu_state()
            debugging.leave()
            return
        elif action_name == 'delete' and row_index >= 0:
            # Capture dependents BEFORE removing the row from the graph so
            # get_dependents() can still find the node.
            process_name = str(self.dataframe.iloc[row_index][PROCESS_NAME_HDR])
            task_name    = str(self.dataframe.iloc[row_index][TASK_NAME_HDR])
            if process_name == '' and task_name == '':
                deleted_pt = f'__empty_row_{row_index}'
            else:
                deleted_pt = f'{process_name}:{task_name}'
            # get_dependents() returns old row indexes; collect the Process:Task
            # keys instead so we can re-look them up after the graph is rebuilt.
            dependent_pts = []
            direct_dependent_pts = []
            if deleted_pt in self.dependency_graph:
                # Direct dependents only — for the warning message
                direct_dependent_pts = sorted(self.dependency_graph[deleted_pt]['dependents'])
                # Full transitive set — for recalculation after delete
                old_dependent_rows = self.get_dependents(deleted_pt)
                old_idx_to_pt = {info['row_index']: pt
                                 for pt, info in self.dependency_graph.items()}
                dependent_pts = [old_idx_to_pt[r] for r in old_dependent_rows
                                 if r in old_idx_to_pt]

            confirmed = self.delete_row_at(row_index, selected_row_indexes, direct_dependent_pts)
            if not confirmed:
                debugging.leave('delete cancelled')
                return

            target_row_index = min(row_index, self.dataframe.shape[0] - 1)

            # Fast path: remove from model directly, rebuild graph, recalc dependents only
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.table_view.setUpdatesEnabled(False)
            self.model.removeRow(row_index)
            self.build_dependency_graph()

            # Recalculate dependents using their new row_index values from the rebuilt graph
            for pt in dependent_pts:
                if pt in self.dependency_graph:
                    self.model.recalculateRow(self.dependency_graph[pt]['row_index'])

            self.table_view.setUpdatesEnabled(True)
            self.update_status_bar("Ready")
            QApplication.restoreOverrideCursor()
            self.update_processname_completer()

            if target_row_index >= 0:
                self.table_view.selectRow(target_row_index)
                self.table_view.scrollTo(self.model.index(target_row_index, column_index(PROCESS_NAME_HDR)))
            self.update_edit_menu_state()
            debugging.leave()
            return
        else:
            debugging.leave(f'action not executed: action_name={action_name}, row_index={row_index}')
            return

        self.apply_rules_and_populate_model()
        self.set_fixed_column_widths()

        # Navigate to target row after model rebuild
        if target_row_index is not None and target_row_index >= 0:
            self.table_view.selectRow(target_row_index)
            new_index = self.model.index(target_row_index, column_index(PROCESS_NAME_HDR))
            self.table_view.scrollTo(new_index)

        debugging.leave()

    def vertical_header_context_menu(self, position):
        debugging.enter(f'position={position}')
        # Convert the position to index
        row_index = self.table_view.verticalHeader().logicalIndexAt(position)
        row_max = self.dataframe.shape[0] - 1
        debugging.print(f'row_index={row_index}, row_max={row_max}')
        self.table_view.selectRow(row_index)

        context_menu = QMenu()
        move_row_up_action = context_menu.addAction("Move Row Up")
        if (row_index == 0): move_row_up_action.setEnabled(False)
        move_row_down_action = context_menu.addAction("Move Row Down")
        if (row_index == row_max): move_row_down_action.setEnabled(False)
        context_menu.addSeparator()
        add_row_above_action = context_menu.addAction("Add Row Above")
        add_row_below_action = context_menu.addAction("Add Row Below")
        context_menu.addSeparator()
        copy_row_action = context_menu.addAction("Copy Row")
        paste_row_action = context_menu.addAction("Paste Row")
        if self.row_copy is None: paste_row_action.setEnabled(False)
        context_menu.addSeparator()
        delete_row_action = context_menu.addAction("Delete Row")

        # Map action objects to action names
        action_map = {
            move_row_up_action: 'move_up',
            move_row_down_action: 'move_down',
            add_row_above_action: 'add_above',
            add_row_below_action: 'add_below',
            copy_row_action: 'copy',
            paste_row_action: 'paste',
            delete_row_action: 'delete',
        }

        action = context_menu.exec(self.table_view.viewport().mapToGlobal(position))
        debugging.print(f'action={action}')

        if action is not None and action in action_map:
            self.execute_row_action(action_map[action], row_index)

        debugging.leave()

    def evaluate(self, expression, referenceLocation, callerReference):
        debugging.enter(f'expression={expression}, referenceLocation={referenceLocation}, callerReference={callerReference}')
        try:
            dependencies = []
            result = self.evaluator.evaluate_expression(expression=expression, dependencies=dependencies, referenceLocation=referenceLocation, callerProcessTask=callerReference)
        except Exception as e:
            debugging.leave(f'evaluate_expression() Exception: {e}')
            raise
        debugging.leave(f'result={result}')
        return(result)
        
    def get_df_row_index(self, process_task, referenceLocation):
        debugging.enter(f'process_task={process_task}, referenceLocation={referenceLocation}')
        row_index = self.pt_to_row_index.get(process_task, None)
        debugging.leave(f'process_task={process_task}, row_index={row_index}')
        return row_index

    def start_time(self, process_task, dependencies, referenceLocation):
        debugging.enter(f'process_task={process_task}, dependencies={dependencies}, referenceLocation={referenceLocation}')
        result = StartTimeResultError(errorMessage=f'StartTime({process_task})', errorLocation=referenceLocation)
        row_index = self.get_df_row_index(process_task, referenceLocation)
        debugging.print(f'get_df_row_index(): row_index={row_index}')
        if (row_index != None):
            val = self.dataframe.iloc[row_index][START_TIME_FORMULA_HDR]
            debugging.print(f'start_time: val={val}')
            try:
                result = float(val)
            except ValueError as e:
                debugging.print(f'float() Exception: {e}')
                try:
                    caller_dependencies = dependencies[:]
                    result = self.evaluator.evaluate_expression(expression=val, dependencies=caller_dependencies, referenceLocation=referenceLocation, callerProcessTask=process_task)
                except CircularReferenceError as e:
                    errorMsg = f'{e} via {process_task}.{START_TIME_FORMULA_HDR}'
                    debugging.leave(f'evaluate_expression({val}) Exception: CircularReferenceError({errorMsg})')
                    raise CircularReferenceError(errorMsg)
                except ValueError as e:
                    errorMsg = f'{e} via {process_task}.{START_TIME_FORMULA_HDR}'
                    debugging.leave(f'evaluate_expression({val}) Exception: ValueError({errorMsg})')
                    raise ValueError(errorMsg)
                except Exception as e:
                    debugging.leave(f'evaluate_expression({val}) Exception: {e}')
                    raise
        debugging.leave(f'result={result}, process_task={process_task}, referenceLocation={referenceLocation}')
        return(result)
        
    def end_time(self, process_task, dependencies, referenceLocation):
        debugging.enter(f'process_task={process_task}, dependencies={dependencies}, referenceLocation={referenceLocation}')
        result = EndTimeResultError(errorMessage=f'EndTime({process_task})', errorLocation=referenceLocation)
        row_index = self.get_df_row_index(process_task, referenceLocation)
        debugging.print(f'get_df_row_index(): row_index={row_index}')
        if (row_index != None):
            val = self.dataframe.iloc[row_index][END_TIME_FORMULA_HDR]
            debugging.print(f'end_time: val={val}')
            try:
                result = float(val)
            except ValueError as e:
                debugging.print(f'float() Exception: {e}')
                try:
                    caller_dependencies = dependencies[:]
                    result = self.evaluator.evaluate_expression(expression=val, dependencies=caller_dependencies, referenceLocation=referenceLocation, callerProcessTask=process_task)
                except CircularReferenceError as e:
                    errorMsg = f'{e} via {process_task}.{END_TIME_FORMULA_HDR}'
                    debugging.leave(f'evaluate_expression({val}) Exception: CircularReferenceError({errorMsg})')
                    raise CircularReferenceError(errorMsg)
                except ValueError as e:
                    errorMsg = f'{e} via {process_task}.{END_TIME_FORMULA_HDR}'
                    debugging.leave(f'evaluate_expression({val}) Exception: ValueError({errorMsg})')
                    raise ValueError(errorMsg)
                except Exception as e:
                    debugging.leave(f'evaluate_expression({val}) Exception: {e}')
                    raise
        debugging.leave(f'result={result}, process_task={process_task}, referenceLocation={referenceLocation}')
        return(result)

    def duration_time(self, process_task, dependencies, referenceLocation):
        debugging.enter(f'process_task={process_task}, dependencies={dependencies}, referenceLocation={referenceLocation}')
        result = DurationResultError(errorMessage=f'Duration({process_task})', errorLocation=referenceLocation)
        start_tm = None
        end_tm = None
        try:
            start_tm = self.start_time(process_task, dependencies, referenceLocation=referenceLocation)
        except Exception as e:
            # debugging.leave(f'start_time({process_task}), Exception: {e}')
            # raise
            pass
        try:
            end_tm = self.end_time(process_task, dependencies, referenceLocation=referenceLocation)
        except Exception as e:
            # debugging.leave(f'end_time({process_task}), Exception: {e}')
            # raise
            pass
        debugging.print(f'duration_time: start_tm={start_tm}')
        debugging.print(f'duration_time: end_tm={end_tm}')
        
        if (isinstance(start_tm, type(ResultError()))):
            result = start_tm
        elif (isinstance(end_tm, type(ResultError()))):
            result = end_tm
        else:
            if ((start_tm != None) and (end_tm != None)):
                try:
                    start_tm = float(start_tm)
                except ValueError as e:
                    # debugging.leave(f'float(start_tm="{start_tm}"), Exception: {e}')
                    # raise   
                    pass
                else:
                    try:
                        end_tm = float(end_tm)
                    except ValueError as e:
                        # debugging.leave(f'float(end_tm="{end_tm}"), Exception: {e}')
                        # raise   
                        pass
                    else:
                        result = end_tm - start_tm
        debugging.leave(f'result={result}, process_task={process_task}, referenceLocation={referenceLocation}')
        return(result)

    def min_values(self, values, dependencies, referenceLocation):
        """Return the minimum of a list of already-evaluated float values."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = min(values)
        debugging.leave(f'result={result}')
        return result

    def max_values(self, values, dependencies, referenceLocation):
        """Return the maximum of a list of already-evaluated float values."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = max(values)
        debugging.leave(f'result={result}')
        return result

    def is_less_than(self, values, dependencies, referenceLocation):
        """Return 1.0 if values[0] < values[1], else 0.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if values[0] < values[1] else 0.0
        debugging.leave(f'result={result}')
        return result

    def is_greater_than(self, values, dependencies, referenceLocation):
        """Return 1.0 if values[0] > values[1], else 0.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if values[0] > values[1] else 0.0
        debugging.leave(f'result={result}')
        return result

    def is_less_equal(self, values, dependencies, referenceLocation):
        """Return 1.0 if values[0] <= values[1], else 0.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if values[0] <= values[1] else 0.0
        debugging.leave(f'result={result}')
        return result

    def is_greater_equal(self, values, dependencies, referenceLocation):
        """Return 1.0 if values[0] >= values[1], else 0.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if values[0] >= values[1] else 0.0
        debugging.leave(f'result={result}')
        return result

    def is_equal(self, values, dependencies, referenceLocation):
        """Return 1.0 if values[0] == values[1], else 0.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if values[0] == values[1] else 0.0
        debugging.leave(f'result={result}')
        return result

    def is_not_equal(self, values, dependencies, referenceLocation):
        """Return 1.0 if values[0] != values[1], else 0.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if values[0] != values[1] else 0.0
        debugging.leave(f'result={result}')
        return result

    def if_value(self, values, dependencies, referenceLocation):
        """Return values[1] (A) if values[0] != 0, else values[2] (B)."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = values[1] if values[0] != 0.0 else values[2]
        debugging.leave(f'result={result}')
        return result

    def not_value(self, values, dependencies, referenceLocation):
        """Return 1.0 if values[0] == 0, else 0.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if values[0] == 0.0 else 0.0
        debugging.leave(f'result={result}')
        return result

    def or_values(self, values, dependencies, referenceLocation):
        """Return 0.0 if all values are 0, else 1.0. Accepts N >= 2 arguments."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 0.0 if all(v == 0.0 for v in values) else 1.0
        debugging.leave(f'result={result}')
        return result

    def and_values(self, values, dependencies, referenceLocation):
        """Return 1.0 if all values are non-zero, else 0.0. Accepts N >= 2 arguments."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = 1.0 if all(v != 0.0 for v in values) else 0.0
        debugging.leave(f'result={result}')
        return result

    def grp_value(self, values, dependencies, referenceLocation):
        """Return the single evaluated value of a parenthesized group, e.g. (3-2) -> 1.0."""
        debugging.enter(f'values={values}, referenceLocation={referenceLocation}')
        result = values[0]
        debugging.leave(f'result={result}')
        return result




def parse_command_line_args():
    """Parse and validate command line arguments before any system initialization"""
    # NOTE: No debugging calls here since debugging system not yet initialized
    
    # Check for too many arguments
    if len(sys.argv) > 2:
        print(f"Usage: PTTEdit [filename | filename.pttd]")
        sys.exit(1)
    
    # Get filename if provided
    filename = None
    if len(sys.argv) == 2:
        # try:
            filename = os.path.abspath(sys.argv[1])
            
            # Auto-append .pttd if not present
            if not filename.lower().endswith('.pttd'):
                filename = f'{filename}.pttd'
            
            # Check if file exists
            if not Path(filename).is_file():
                raise FileNotFoundError(f"{filename}")
                # print(f"Error: File not found: {filename}")
                # sys.exit(1)
                
        # except Exception as e:
            # print(f"Error processing filename '{sys.argv[1]}': {e}")
            # sys.exit(1)
    
    return filename

def main(filename=None, splash=None, splash_label=None, splash_img=None):
    debugging.enter(f'filename={filename}')
    app = QApplication(sys.argv)
    window = DataFrameEditor(filename, splash=splash, splash_label=splash_label, splash_img=splash_img)
    window.show()
    sys.exit(app.exec())
    debugging.leave()

if __name__ == "__main__":
    # Show splash screen FIRST - before any other initialization
    _splash, _splash_label, _splash_img = show_splash()

    # Suppress Qt warning about DPI awareness caused by tkinter splash SetProcessDPIAware() call
    os.environ['QT_LOGGING_RULES'] = 'qt.qpa.window=false'

    # Install crash logger FIRST - before anything else can fail.
    # USER_LOG_PATH is defined at module level via platformdirs.
    crash_logger = CrashLogger(
        app_name     = PROGRAM_NAME,
        app_version  = APP_VERSION,
        log_dir      = USER_LOG_PATH,
        log_filename = 'pttedit_crash_log.txt',
    )
    crash_logger.install()

    # Parse and validate command line arguments FIRST - before any other initialization
    filename = parse_command_line_args()

    # Load User Config/INI file. Handles setup of default and merging if user config is missing entries.
    config = load_edit_config(f'{PROGRAM_FILENAME}.ini', DEFAULT_CONFIG, PROGRAM_NAME)

    debugging_enabled = config['DEBUGGING']['enabled_bool']
    debugging_filename = config['DEBUGGING']['filename']
    if debugging_filename and not os.path.dirname(debugging_filename):
        # Bare filename - place in user log dir
        log_dir = user_log_dir(PACKAGE_NAME, APP_COMPANY)
        os.makedirs(log_dir, exist_ok=True)
        debugging_filename = os.path.join(log_dir, debugging_filename)
    debugging.set_output_filename(debugging_filename)
    debugging.set_enabled(debugging_enabled)

    # Log module versions to debug file
    debugging.log_module_versions(module_list=['PySide6','pandas','numpy','configparser','platformdirs','json5','configupdater'])
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
    main(filename, splash=_splash, splash_label=_splash_label, splash_img=_splash_img)
    debugging.leave()
