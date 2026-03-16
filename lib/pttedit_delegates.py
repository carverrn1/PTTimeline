from functools import partial

from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit, QMenu, QTableView, QAbstractItemView, QStyle, QCompleter
from PySide6.QtCore import Qt, QRegularExpression, QStringListModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont, QRegularExpressionValidator

from pttedit_expression_evaluator import ResultError, GENERIC_RESULT_ERROR

debugging = None  # Set by pttedit.py after import: ptt_delegates.debugging = debugging


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

DATA_FILE_EXTENSION = 'pttd'

PROCESS_NAME_HDR        =   'ProcessName'
TASK_NAME_HDR           =   'TaskName'
START_TIME_FORMULA_HDR  =   'StartTimeFormula'
START_TIME_HDR          =   'StartTime'
END_TIME_FORMULA_HDR    =   'EndTimeFormula'
END_TIME_HDR            =   'EndTime'
DURATION_HDR            =   'Duration'

COLUMN_NAMES = [PROCESS_NAME_HDR, TASK_NAME_HDR, START_TIME_FORMULA_HDR, START_TIME_HDR, END_TIME_FORMULA_HDR, END_TIME_HDR, DURATION_HDR]
TABLE_COLUMN_HEADER_LABELS = ['Process', 'Task', 'Start-ƒ (Start Formula)', 'Start', 'End-ƒ (End Formula)', 'End', 'Duration']

def column_index(column_name):
    return(COLUMN_NAMES.index(column_name))

COLUMN_WIDTHS = {
    PROCESS_NAME_HDR:       150,
    TASK_NAME_HDR:          150,
    START_TIME_FORMULA_HDR: 350,
    START_TIME_HDR:         55,
    END_TIME_FORMULA_HDR:   350,
    END_TIME_HDR:           55,
    DURATION_HDR:           60
    }

def column_width(column_name):
    return(COLUMN_WIDTHS[column_name])


DECIMAL_PLACES_START_TIME = 3
DECIMAL_PLACES_ENDTIME = 3
DECIMAL_PLACES_DURATION= 3

def formatStartTime(value):
    debugging.enter(f'value={value}, type(value)={type(value)}')
    if (isinstance(value, float)):
        decimal_places = DECIMAL_PLACES_START_TIME
        formatted_value = f"{value:.{decimal_places}f}"
    else:
        formatted_value = str(value)
    debugging.leave(f'value={value}, type(value)={type(value)}, formatted_value={formatted_value}')
    return(formatted_value)

def formatEndTime(value):
    debugging.enter(f'value={value}, type(value)={type(value)}')
    if (isinstance(value, float)):
        decimal_places = DECIMAL_PLACES_ENDTIME
        formatted_value = f"{value:.{decimal_places}f}"
    else:
        formatted_value = str(value)
    debugging.leave(f'value={value}, type(value)={type(value)}, formatted_value={formatted_value}')
    return(formatted_value)

def formatDuration(value):
    debugging.enter(f'value={value}, type(value)={type(value)}')
    if (isinstance(value, float)):
        decimal_places = DECIMAL_PLACES_DURATION
        formatted_value = f"{value:.{decimal_places}f}"
    else:
        formatted_value = str(value)
    debugging.leave(f'value={value}, type(value)={type(value)}, formatted_value={formatted_value}')
    return(formatted_value)


# ---------------------------------------------------------------------------
# Item delegates
# ---------------------------------------------------------------------------

class ReadOnlyItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        debugging.enter(f'option={type(option)}, index.row()={index.row()}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')
        debugging.leave()
        return

class ProcessNameItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completerModel = QStringListModel()
        self.completer.setModel(self.completerModel)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not index.data():
            painter.save()
            painter.restore()

    def setCompleterStrings(self, strings):
        self.completerModel.setStringList(strings)

    def createEditor(self, parent, option, index):
        debugging.enter(f'option={type(option)}, index.row()={index.row()}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            validator = QRegularExpressionValidator(QRegularExpression(r'^$|[A-Za-z_][A-Za-z0-9_]*'), editor)
            editor.setValidator(validator)
            editor.setCompleter(self.completer)
        debugging.leave()
        return editor

class TaskNameItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not index.data():
            painter.save()
            painter.restore()

    def createEditor(self, parent, option, index):
        debugging.enter(f'option={type(option)}, index.row()={index.row()}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            validator = QRegularExpressionValidator(
                QRegularExpression(r'^$|[A-Za-z_][A-Za-z0-9_]*'), editor
            )
            editor.setValidator(validator)
        debugging.leave()
        return editor

class FormulaItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        debugging.enter(f'option={type(option)}, index.row()={index.row()}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            validator = QRegularExpressionValidator(
                QRegularExpression(r'^[A-Za-z0-9_():+\-\*\/\.\$, ]*$'), editor
            )
            editor.setValidator(validator)
        debugging.leave()
        return editor

class PosFloatItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        debugging.enter(f'option={type(option)}, index.row()={index.row()}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            validator = QRegularExpressionValidator(
                QRegularExpression(r'^$|[0-9]*\.?[0-9]+'), editor
            )
            editor.setValidator(validator)
        debugging.leave()
        return editor

class AnyFloatItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        debugging.enter(f'option={type(option)}, index.row()={index.row()}, index.column()={index.column()}:{COLUMN_NAMES[index.column()]}')
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            validator = QRegularExpressionValidator(
                QRegularExpression(r'^$|[-]?[0-9]*\.?[0-9]+'), editor
            )
            editor.setValidator(validator)
        debugging.leave()
        return editor

class StartTimeFormulaItemDelegate(FormulaItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not index.data():
            painter.save()
            painter.setOpacity(0.5)
            painter.setPen(QColor(Qt.gray))
            placeholder_text = "Start Time Formula (s)"
            painter.drawText(option.rect.adjusted(5, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, placeholder_text)
            painter.restore()

class StartTimeItemDelegate(ReadOnlyItemDelegate):
    def paint(self, painter, option, index):
        # Override selection background to maintain gray for read-only cells
        if option.state & QStyle.State_Selected:
            option.backgroundBrush = QColor('#d0d0d0')  # Slightly darker gray for selected
        elif option.state & QStyle.State_MouseOver:
            option.backgroundBrush = QColor('#f0f0f0')  # Lighter gray for hover
        else:
            option.backgroundBrush = QColor('#e8e8e8')

        # CRITICAL: Always set text color to ensure visibility
        option.palette.setColor(option.palette.ColorRole.Text, QColor('#333333'))
        option.palette.setColor(option.palette.ColorRole.HighlightedText, QColor('#333333'))

        # Set font to italic for read-only cells
        font = option.font
        font.setItalic(True)
        option.font = font

        super().paint(painter, option, index)

        if not index.data():
            painter.save()
            painter.setOpacity(0.5)
            painter.setPen(QColor(Qt.gray))
            placeholder_text = "Start Time (s)"
            painter.drawText(option.rect.adjusted(5, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, placeholder_text)
            painter.restore()

class EndTimeFormulaItemDelegate(FormulaItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not index.data():
            painter.save()
            painter.setOpacity(0.5)
            painter.setPen(QColor(Qt.gray))
            placeholder_text = "End Time Formula (s)"
            painter.drawText(option.rect.adjusted(5, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, placeholder_text)
            painter.restore()

class EndTimeItemDelegate(ReadOnlyItemDelegate):
    def paint(self, painter, option, index):
        # Override selection background to maintain gray for read-only cells
        if option.state & QStyle.State_Selected:
            option.backgroundBrush = QColor('#d0d0d0')  # Slightly darker gray for selected
        elif option.state & QStyle.State_MouseOver:
            option.backgroundBrush = QColor('#f0f0f0')  # Lighter gray for hover
        else:
            option.backgroundBrush = QColor('#e8e8e8')

        # CRITICAL: Always set text color to ensure visibility
        option.palette.setColor(option.palette.ColorRole.Text, QColor('#333333'))
        option.palette.setColor(option.palette.ColorRole.HighlightedText, QColor('#333333'))

        # Set font to italic for read-only cells
        font = option.font
        font.setItalic(True)
        option.font = font

        super().paint(painter, option, index)

        if not index.data():
            painter.save()
            painter.setOpacity(0.5)
            painter.setPen(QColor(Qt.gray))
            placeholder_text = "End Time (s)"
            painter.drawText(option.rect.adjusted(5, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, placeholder_text)
            painter.restore()

class DurationItemDelegate(ReadOnlyItemDelegate):
    def paint(self, painter, option, index):
        # Override selection background to maintain gray for read-only cells
        if option.state & QStyle.State_Selected:
            option.backgroundBrush = QColor('#d0d0d0')  # Slightly darker gray for selected
        elif option.state & QStyle.State_MouseOver:
            option.backgroundBrush = QColor('#f0f0f0')  # Lighter gray for hover
        else:
            option.backgroundBrush = QColor('#e8e8e8')

        # CRITICAL: Always set text color to ensure visibility
        option.palette.setColor(option.palette.ColorRole.Text, QColor('#333333'))
        option.palette.setColor(option.palette.ColorRole.HighlightedText, QColor('#333333'))

        # Set font to italic for read-only cells
        font = option.font
        font.setItalic(True)
        option.font = font

        super().paint(painter, option, index)

        if not index.data():
            painter.save()
            painter.setOpacity(0.5)
            painter.setPen(QColor(Qt.gray))
            placeholder_text = "Duration (s)"
            painter.drawText(option.rect.adjusted(5, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, placeholder_text)
            painter.restore()


# ---------------------------------------------------------------------------
# Model item with highlighting
# ---------------------------------------------------------------------------

class HighlightedStandardItem(QStandardItem):
    def __init__(self, text, col=None):
        super().__init__(text)
        debugging.enter(f"text={text}, type(text)={type(text)}, self.text()={self.text()}, type(self.text())={type(self.text())}, self.column()={self.column()}, col={col}")
        self.checkHighlight(col=col)
        debugging.leave()

    def checkHighlight(self, col=None):
        debugging.enter(f'self.text()={self.text()}, self.column()={self.column()}, col={col}, type(self.text())={type(self.text())}')
        selected_highlight = None
        if (self.text()):
            if (col in [column_index(START_TIME_HDR), column_index(END_TIME_HDR), column_index(DURATION_HDR)]):
                # These are calculated/read-only columns
                if (self.text().endswith(GENERIC_RESULT_ERROR)):
                    # Error condition - gray background with red text
                    selected_highlight = 3
                    self.setBackground(QColor('#e8e8e8'))  # Gray background to match read-only cells
                    self.setForeground(Qt.red)  # Red text for error
                elif (col in [column_index(DURATION_HDR)]):
                    try:
                        if float(self.text()) < 0:
                            # Negative duration - light yellow warning background with bold dark red text
                            selected_highlight = -1
                            self.setBackground(QColor('lightyellow'))
                            self.setForeground(QColor('darkred'))
                            font = self.font()
                            font.setBold(True)
                            self.setFont(font)
                        else:
                            # Normal calculated value - light gray background (read-only appearance)
                            selected_highlight = 1
                            self.setBackground(QColor('#e8e8e8'))  # Light gray
                            self.setForeground(QColor('#333333'))  # Darker text
                    except ValueError:
                        # Can't parse as float - error
                        selected_highlight = 3
                        self.setBackground(QColor('#e8e8e8'))  # Gray background to match read-only cells
                        self.setForeground(Qt.red)  # Red text for error
                else:
                    # START_TIME and END_TIME columns - read-only appearance
                    selected_highlight = 1
                    self.setBackground(QColor('#e8e8e8'))  # Light gray
                    self.setForeground(QColor('#333333'))  # Darker text
            elif (col in [column_index(PROCESS_NAME_HDR), column_index(TASK_NAME_HDR)]):
                    # Editable columns - normal white background
                    selected_highlight = 2
                    self.setBackground(Qt.white)
                    self.setForeground(Qt.black)
            else:
                # Formula columns and other editable columns - normal white background
                self.setBackground(Qt.white)
                self.setForeground(Qt.black)
        else:
            selected_highlight = 0
            # Empty cells
            if (col in [column_index(START_TIME_HDR), column_index(END_TIME_HDR), column_index(DURATION_HDR)]):
                # Empty calculated cells - still show as read-only
                self.setBackground(QColor('#e8e8e8'))
                self.setForeground(QColor('#333333'))
        debugging.leave(f'selected_highlight={selected_highlight}')


# ---------------------------------------------------------------------------
# Custom table view
# ---------------------------------------------------------------------------

class EditableTableView(QTableView):
    def __init__(self, parent=None):
        debugging.enter()
        super(EditableTableView, self).__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        # Disable hover highlighting to prevent gray background when scrolling
        self.setMouseTracking(False)

        self.setStyleSheet(
            """
            QTableView {
                font-size: 10px;
            }
            QTableView::item:hover {
                background-color: transparent;
                color: #333333;
            }
            QTableView::item:selected:hover {
                color: #333333;
            }
            """
        )

        # Define editable columns in tab order
        self.editable_columns = [
            column_index(PROCESS_NAME_HDR),      # 0
            column_index(TASK_NAME_HDR),         # 1
            column_index(START_TIME_FORMULA_HDR),# 2
            column_index(END_TIME_FORMULA_HDR)   # 4
        ]

        debugging.leave()

    def moveCursor(self, cursorAction, modifiers):
        """Override cursor movement to skip read-only columns when using Tab"""
        debugging.enter(f'cursorAction={cursorAction}')

        current = self.currentIndex()

        # Handle Tab key (MoveNext)
        if cursorAction == QAbstractItemView.CursorAction.MoveNext:
            current_col = current.column()
            current_row = current.row()

            debugging.print(f'MoveNext from row={current_row}, col={current_col}')

            # Find current position in editable columns list
            if current_col in self.editable_columns:
                current_pos = self.editable_columns.index(current_col)

                # Move to next editable column
                if current_pos < len(self.editable_columns) - 1:
                    # Move to next editable column in same row
                    next_col = self.editable_columns[current_pos + 1]
                    next_row = current_row
                else:
                    # We're at the last editable column, wrap to first column of next row
                    next_row = current_row + 1
                    if next_row >= self.model().rowCount():
                        next_row = 0  # Wrap to first row
                    next_col = self.editable_columns[0]

                next_index = self.model().index(next_row, next_col)
                debugging.print(f'Moving to row={next_row}, col={next_col}')
                debugging.leave()
                return next_index

        # Handle Shift+Tab (MovePrevious)
        elif cursorAction == QAbstractItemView.CursorAction.MovePrevious:
            current_col = current.column()
            current_row = current.row()

            debugging.print(f'MovePrevious from row={current_row}, col={current_col}')

            # Find current position in editable columns list
            if current_col in self.editable_columns:
                current_pos = self.editable_columns.index(current_col)

                # Move to previous editable column
                if current_pos > 0:
                    # Move to previous editable column in same row
                    prev_col = self.editable_columns[current_pos - 1]
                    prev_row = current_row
                else:
                    # We're at the first editable column, wrap to last column of previous row
                    prev_row = current_row - 1
                    if prev_row < 0:
                        prev_row = self.model().rowCount() - 1  # Wrap to last row
                    prev_col = self.editable_columns[-1]

                prev_index = self.model().index(prev_row, prev_col)
                debugging.print(f'Moving to row={prev_row}, col={prev_col}')
                debugging.leave()
                return prev_index

        # For all other cursor movements, use default behavior
        debugging.leave('Using default behavior')
        return super().moveCursor(cursorAction, modifiers)

    def showContextMenu(self, position):
        debugging.enter(f'position={position}')
        index = self.indexAt(position)
        if (index.column() == column_index(PROCESS_NAME_HDR)):
            menu = QMenu()
            if index.isValid():
                debugging.print(f'index.row()={index.row()}, index.column()={index.column()}')
                column_data = [self.model().data(self.model().index(row, index.column()), Qt.DisplayRole)
                               for row in range(self.model().rowCount())]
                unique_data = sorted(set(filter(None, column_data)))  # Remove empty strings and sort
                debugging.print(f'unique_data={unique_data}')
                for data in unique_data:
                    action = menu.addAction(data)
                    action.triggered.connect(partial(self.setModelData, index, data))
            menu.exec(self.viewport().mapToGlobal(position))
        debugging.leave()

    def setModelData(self, index, text):
        debugging.enter(f'index.row()={index.row()}, index.column()={index.column()}, text={text}')
        self.model().setData(index, text, Qt.EditRole)
        debugging.leave()
