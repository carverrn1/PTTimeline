#!/usr/bin/env python3
"""
PTTimeline Image Viewer - Standalone image viewer for PTTimeline exports and other images

Usage: python pttimelineviewer.py <image_file>

A minimal, focused image viewer designed for viewing PTTimeline exports and other images
with zoom and pan capabilities.

Supported formats: PDF (rendered), SVG, PNG, JPG, JPEG, BMP, GIF, TIFF, WEBP

Mouse Controls:
- Wheel: Vertical panning
- Shift + Wheel: Horizontal panning  
- Ctrl + Wheel: Zoom in/out (centered on cursor)

Keyboard Shortcuts:
- Ctrl + Plus/Minus: Zoom in/out
- Ctrl + 0: Fit to window
- Ctrl + 1: Actual size
- Arrow keys: Pan up/down/left/right
- F1: Show help dialog
- F11: Toggle fullscreen
- Escape: Close
"""

import sys
import os
import re
import contextlib
import webbrowser
from pathlib import Path
from io import StringIO
from importlib.metadata import version as get_module_version
import platform

# Optional high-resolution PDF rendering via PyMuPDF
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

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
    return _show_splash('pttview_splash.png', _RES_DIR)

# Setup program name and version information
PROGRAM_FILENAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]
capitalize_first_four = lambda s: s[:4].upper() + s[4:]     # Capitalize first 4 letters
from ptt_appinfo import APP_VERSION, APP_COPYRIGHT, APP_AUTHOR, APP_COMPANY, APP_DATE, APP_DESCRIPTION, APP_PACKAGE, APP_ID, APP_REPO_URL
from ptt_utils import html_to_plain_text, build_issue_url, get_os_info
PROGRAM_NAME    = capitalize_first_four(PROGRAM_FILENAME)
PACKAGE_NAME    = APP_PACKAGE

from platformdirs import user_config_dir, user_log_dir
USER_LOG_PATH = user_log_dir(PACKAGE_NAME, APP_COMPANY)
from ptt_debugging import CrashLogger

window_icon_path = os.path.join(_RES_DIR, f"{PACKAGE_NAME}.ico")
program_icon_path = os.path.join(_RES_DIR, f"{PROGRAM_NAME}.ico")

# Suppress Qt SVG and screen warnings before importing Qt modules
os.environ['QT_LOGGING_RULES'] = 'qt.svg.warning=false;qt.svg.critical=false;qt.svg.debug=false;qt.qpa.screen=false;qt.qpa.window=false'

# Backup: Filter stderr to hide Qt SVG warnings if environment approach fails
class StderrFilter:
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
    
    def write(self, text):
        # Filter out Qt SVG warnings
        if 'qt.svg:' not in text and '<use> element' not in text:
            self.original_stderr.write(text)
    
    def flush(self):
        self.original_stderr.flush()

# Apply stderr filter
sys.stderr = StderrFilter(sys.stderr)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QVBoxLayout, QHBoxLayout, 
    QWidget, QPushButton, QLabel, QMessageBox, QStatusBar, QToolBar, QInputDialog, QDialog, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, QPointF, Signal
from PySide6.QtGui import QKeySequence, QAction, QIcon, QPixmap, QPainter, QImage


class PDFScaling:
    MIN_DPI = 24.0
    LOGICAL_DPI = 96.0   # Reference DPI for original_size and zoom math (screen resolution)

def render_pdf_page_to_pixmap(pdf_path: str, page_num: int = 0, dpi: int = 200) -> QPixmap:
    """Render a PDF page to a QPixmap at the requested DPI using PyMuPDF."""
    if fitz is None:
        raise ImportError("PyMuPDF (pymupdf) is required to render PDFs at higher resolution. Install with: pip install pymupdf")
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_num)
        scale = dpi / PDFScaling.MIN_DPI  # PDF points are # DPI units
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg.copy())  # copy() so QImage owns its memory
    finally:
        doc.close()

class ZoomLimits:
    MIN = 0.05      # 5%
    MAX = 5.0       # 500%

class ZoomableImageWidget(QWidget):
    """Image widget with mouse wheel zoom support for both SVG and raster images"""
    
    # Signal emitted when zoom level changes
    zoomChanged = Signal(float)  # Emits the new scale factor
    
    def __init__(self, image_file):
        super().__init__()
        self.image_file = image_file
        self.scale_factor = 1.0
        self.setMinimumSize(100, 100)
        self.min_zoom = ZoomLimits.MIN
        self.max_zoom = ZoomLimits.MAX

        # Determine file type and create appropriate widget
        self.is_svg = image_file.lower().endswith(('.svg', '.svgz'))
        self.is_pdf = image_file.lower().endswith('.pdf')
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)


        if self.is_svg:
            from PySide6.QtSvgWidgets import QSvgWidget
            # Load SVG content and strip DOCTYPE to avoid Qt network DTD fetch issues
            with open(image_file, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            import re
            svg_content = re.sub(r'<!DOCTYPE[^>]*>', '', svg_content)
            self.image_widget = QSvgWidget()
            self.image_widget.load(svg_content.encode('utf-8'))
            self.original_size = self.image_widget.renderer().defaultSize()
        else:
            self.image_widget = QLabel()

            if self.is_pdf:
                self.pdf_page_num = 0
                self.pdf_base_dpi = 300
                self.pdf_dpi_cap = 600
                # Render at logical (screen) DPI so original_size is screen-sized;
                # zoom math then produces sensible percentages (e.g. ~60-100% fit).
                self.base_pixmap = render_pdf_page_to_pixmap(
                    image_file, self.pdf_page_num, int(PDFScaling.LOGICAL_DPI)
                )
                if self.base_pixmap.isNull():
                    raise Exception(f"Could not render PDF: {image_file}")
                self.original_pixmap = self.base_pixmap
                self.current_pixmap = self.base_pixmap
            else:
                self.original_pixmap = QPixmap(image_file)
                if self.original_pixmap.isNull():
                    raise Exception(f"Could not load image: {image_file}")
                self.current_pixmap = self.original_pixmap

            self.image_widget.setPixmap(self.current_pixmap)
            self.image_widget.setAlignment(Qt.AlignCenter)
            self.original_size = self.original_pixmap.size()

        layout.addWidget(self.image_widget)
        self.setFixedSize(self.original_size)
        
    def wheelEvent(self, event):
        """Handle mouse wheel with modifiers - matches GIMP/Inkscape/IrfanView behavior"""
        modifiers = event.modifiers()
        delta = event.angleDelta().y()
        
        if modifiers == Qt.ControlModifier:
            # Ctrl + Wheel = Zoom (centered on cursor)
            zoom_in = delta > 0
            zoom_factor = 1.15 if zoom_in else 1 / 1.15
            mouse_pos = event.position()
            self.zoom_at_point(zoom_factor, mouse_pos)
            
        elif modifiers == Qt.ShiftModifier:
            # Shift + Wheel = Horizontal panning
            self.pan_horizontal(delta)
            
        else:
            # Wheel alone = Vertical panning  
            self.pan_vertical(delta)
            
    def pan_horizontal(self, delta):
        """Pan horizontally using the scroll bar"""
        scroll_area = self.parent()
        while scroll_area and not hasattr(scroll_area, 'horizontalScrollBar'):
            scroll_area = scroll_area.parent()
            
        if scroll_area:
            h_scroll = scroll_area.horizontalScrollBar()
            # Pan amount proportional to delta (negative for natural direction)
            pan_amount = -delta // 3  # Adjust sensitivity as needed
            new_value = h_scroll.value() + pan_amount
            h_scroll.setValue(new_value)
            
    def pan_vertical(self, delta):
        """Pan vertically using the scroll bar"""
        scroll_area = self.parent()
        while scroll_area and not hasattr(scroll_area, 'horizontalScrollBar'):
            scroll_area = scroll_area.parent()
            
        if scroll_area:
            v_scroll = scroll_area.verticalScrollBar()
            # Pan amount proportional to delta (negative for natural direction)
            pan_amount = -delta // 3  # Adjust sensitivity as needed  
            new_value = v_scroll.value() + pan_amount
            v_scroll.setValue(new_value)
        
    
    def zoom(self, factor):
        """Zoom by the given factor"""
        old_scale = self.scale_factor
        target_scale = old_scale * factor

        # clamp to [min_zoom, max_zoom]
        target_scale = max(self.min_zoom, min(self.max_zoom, target_scale))

        # if clamped causes no effective change, bail
        if abs(target_scale - old_scale) < 1e-9:
            return

        # recompute factor so downstream math stays correct
        factor = target_scale / old_scale
        self.scale_factor = target_scale

        # Apply scaling based on widget type
        if self.is_svg:
            new_size = self.original_size * self.scale_factor
            self.image_widget.setFixedSize(new_size)
            self.setFixedSize(new_size)

        elif self.is_pdf:
            # Render DPI scales from LOGICAL_DPI with zoom, capped at pdf_dpi_cap.
            # scale_factor is relative to original_size (rendered at LOGICAL_DPI),
            # so scale_factor=1.0 → LOGICAL_DPI, scale_factor=2.0 → 2×LOGICAL_DPI, etc.
            dpi = int(PDFScaling.LOGICAL_DPI * self.scale_factor)
            dpi = max(PDFScaling.MIN_DPI, min(self.pdf_dpi_cap, dpi))

            self.current_pixmap = render_pdf_page_to_pixmap(self.image_file, self.pdf_page_num, dpi)

            # Display size always matches true zoom level (so scroll/map math stays correct).
            # Always scale to target_size: at very low zoom MIN_DPI may produce a larger
            # pixmap, and past the cap we upscale from the capped render.
            target_size = self.original_size * self.scale_factor
            display_pixmap = self.current_pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.image_widget.setPixmap(display_pixmap)
            self.setFixedSize(target_size)
    
        else:
            # Raster image scaling
            scaled_pixmap = self.original_pixmap.scaled(
                self.original_size * self.scale_factor,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_widget.setPixmap(scaled_pixmap)
    
            # Update widget size
            new_size = self.original_size * self.scale_factor
            self.setFixedSize(new_size)
    
        # Emit signal for status bar update
        self.zoomChanged.emit(self.scale_factor)
            
    def zoom_at_point(self, factor, point):
        """Zoom by the given factor, keeping the specified point stationary"""

        # Find the scroll area (may be parent or grandparent)
        scroll_area = self.parent()
        while scroll_area and not hasattr(scroll_area, 'horizontalScrollBar'):
            scroll_area = scroll_area.parent()

        if not scroll_area:
            self.zoom(factor)
            return

        h_scroll = scroll_area.horizontalScrollBar()
        v_scroll = scroll_area.verticalScrollBar()
        old_h = h_scroll.value()
        old_v = v_scroll.value()

        old_scale = self.scale_factor

        # Apply the zoom first (this updates self.scale_factor and widget size)
        self.zoom(factor)

        scale_change = self.scale_factor / old_scale
        if scale_change == 1.0:
            return

        # Decide whether 'point' is in viewport coords or widget/content coords.
        # If the point is inside the viewport bounds, treat it as viewport coords.
        vp = scroll_area.viewport()
        in_viewport = (0 <= point.x() <= vp.width()) and (0 <= point.y() <= vp.height())

        if in_viewport:
            # point is viewport coords -> convert to content coords before zoom
            content_x = old_h + point.x()
            content_y = old_v + point.y()

            # After zoom, that content point moves by scale_change. Keep it under cursor:
            new_h = (content_x * scale_change) - point.x()
            new_v = (content_y * scale_change) - point.y()
        else:
            # point already content/widget coords (your old behavior)
            new_h = old_h + (point.x() * (scale_change - 1))
            new_v = old_v + (point.y() * (scale_change - 1))

        h_scroll.setValue(int(new_h))
        v_scroll.setValue(int(new_v))

        
    def zoom_to_fit(self, container_size):
        """Zoom to fit the container"""
        if self.original_size.width() == 0 or self.original_size.height() == 0:
            return
            
        # Calculate scale factors for width and height
        width_scale = (container_size.width() - 20) / self.original_size.width()
        height_scale = (container_size.height() - 20) / self.original_size.height()
        
        # Use the smaller scale factor to ensure it fits
        scale_factor = min(width_scale, height_scale)
        
        # Reset to original size first
        self.scale_factor = 1.0
        self.setFixedSize(self.original_size)
        
        # Apply fit scaling
        self.zoom(scale_factor)
        # Note: zoom() already emits the signal, so no need to emit again
        
    
    def zoom_actual_size(self):
        """Reset to actual size (100%)"""
        self.scale_factor = 1.0

        if self.is_svg:
            self.image_widget.setFixedSize(self.original_size)
            self.setFixedSize(self.original_size)

        elif self.is_pdf:
            # Back to base DPI render
            self.current_pixmap = self.original_pixmap  # base pixmap
            self.image_widget.setPixmap(self.current_pixmap)
            self.setFixedSize(self.current_pixmap.size())

        else:
            self.image_widget.setPixmap(self.original_pixmap)
            self.setFixedSize(self.original_size)

        self.zoomChanged.emit(self.scale_factor)

        
    
    def set_zoom_percentage(self, percentage):
        """Set zoom to specific percentage (e.g., 150 for 150%)"""
        target_scale = percentage / 100.0
        target_scale = max(self.min_zoom, min(self.max_zoom, target_scale))

        if self.is_pdf:
            self.scale_factor = max(0.01, target_scale)

            dpi = int(PDFScaling.LOGICAL_DPI * self.scale_factor)
            dpi = max(PDFScaling.MIN_DPI, min(self.pdf_dpi_cap, dpi))

            self.current_pixmap = render_pdf_page_to_pixmap(self.image_file, self.pdf_page_num, dpi)

            target_size = self.original_size * self.scale_factor
            display_pixmap = self.current_pixmap.scaled(
                target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            self.image_widget.setPixmap(display_pixmap)
            self.setFixedSize(target_size)
            self.zoomChanged.emit(self.scale_factor)
            return

        # Reset to original size first
        self.scale_factor = 1.0
        if self.is_svg:
            self.image_widget.setFixedSize(self.original_size)
        else:
            self.image_widget.setPixmap(self.original_pixmap)
        self.setFixedSize(self.original_size)

        # Apply the target scaling
        if target_scale != 1.0:
            self.zoom(target_scale)
        else:
            self.zoomChanged.emit(self.scale_factor)

        
    
    def is_valid(self):
        """Check if the image loaded successfully"""
        if self.is_svg:
            return self.image_widget.renderer().isValid()
        elif self.is_pdf:
            return hasattr(self, 'original_pixmap') and (self.original_pixmap is not None) and (not self.original_pixmap.isNull())
        else:
            return hasattr(self, 'original_pixmap') and (self.original_pixmap is not None) and (not self.original_pixmap.isNull())

    def generate_thumbnail(self, max_size=400):
        """Generate a thumbnail of the original image for map navigation"""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap, QPainter

        # Calculate thumbnail size maintaining exact aspect ratio
        original_size = self.original_size
        aspect_ratio = original_size.width() / original_size.height() if original_size.height() else 1.0

        if aspect_ratio > 1.0:  # Wider than tall
            thumb_width = max_size
            thumb_height = int(round(max_size / aspect_ratio))
        else:  # Taller than wide
            thumb_height = max_size
            thumb_width = int(round(max_size * aspect_ratio))

        thumbnail = QPixmap(thumb_width, thumb_height)
        thumbnail.fill(Qt.white)

        if self.is_svg:
            # Render SVG to thumbnail
            painter = QPainter(thumbnail)
            renderer = self.image_widget.renderer()
            renderer.render(painter)
            painter.end()
        else:
            # Scale raster image (including rendered PDF pixmap) to thumbnail
            thumbnail = self.original_pixmap.scaled(
                thumb_width, thumb_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

        return thumbnail

class NavigatorDialog(QDialog):
    """Map navigation dialog showing thumbnail with click-to-navigate"""
    
    def __init__(self, image_widget, scroll_area, parent=None):
        super().__init__(parent)
        self.image_widget = image_widget
        self.scroll_area = scroll_area
        self.thumbnail = None
        self.thumbnail_label = None
        self.clicked_position = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the navigator dialog UI"""
        self.setWindowTitle("Map Navigator")
        self.setModal(True)
        self.setFixedSize(450, 550)  # Initial size, will adjust based on thumbnail
        
        # Set window icon
        if os.path.isfile(window_icon_path):
            self.setWindowIcon(QIcon(window_icon_path))
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instruction_label = QLabel("Click on the thumbnail to navigate to that location:")
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)
        
        # Generate and display thumbnail
        self.thumbnail = self.image_widget.generate_thumbnail(400)
        self.thumbnail_label = ClickableLabel()
        self.thumbnail_label.setPixmap(self.thumbnail)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.clicked.connect(self.on_thumbnail_click)
        
        layout.addWidget(self.thumbnail_label)
        
        # Adjust dialog size to thumbnail
        dialog_width = max(400, self.thumbnail.width() + 40)
        dialog_height = max(250, self.thumbnail.height() + 120)
        self.setFixedSize(dialog_width, dialog_height)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
    def on_thumbnail_click(self, position):
        """Handle click on thumbnail - navigate to that position"""
        # Get the actual thumbnail and label sizes
        thumb_size = self.thumbnail.size()
        label_size = self.thumbnail_label.size()
        
        # Account for thumbnail centering within label (QLabel centers the pixmap)
        # Calculate exactly where the thumbnail starts within the label
        offset_x = max(0, (label_size.width() - thumb_size.width()) // 2)
        offset_y = max(0, (label_size.height() - thumb_size.height()) // 2)
        
        # Adjust click position to be relative to actual thumbnail
        thumb_x = position.x() - offset_x
        thumb_y = position.y() - offset_y
        
        # Clamp to thumbnail bounds (ensure we're within the actual image)
        thumb_x = max(0.0, min(float(thumb_size.width() - 1), thumb_x))
        thumb_y = max(0.0, min(float(thumb_size.height() - 1), thumb_y))
        
        # Convert thumbnail coordinates to original image coordinates using exact ratios
        original_size = self.image_widget.original_size
        
        # Use precise floating point ratios
        ratio_x = thumb_x / (thumb_size.width() - 1) if thumb_size.width() > 1 else 0.0
        ratio_y = thumb_y / (thumb_size.height() - 1) if thumb_size.height() > 1 else 0.0
        
        # Convert to original image coordinates
        original_x = ratio_x * (original_size.width() - 1)
        original_y = ratio_y * (original_size.height() - 1)
        
        # Scale by current zoom factor to get current widget coordinates
        current_x = original_x * self.image_widget.scale_factor
        current_y = original_y * self.image_widget.scale_factor
        
        # Center the view on this point
        self.center_view_on_point(current_x, current_y)
        
        # Close dialog
        self.accept()
        
    def center_view_on_point(self, x, y):
        """Center the scroll area view on the given point"""
        # Get scroll bars
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        
        # Get viewport size
        viewport = self.scroll_area.viewport()
        viewport_width = viewport.width()
        viewport_height = viewport.height()
        
        # Calculate new scroll positions to center on the point (use float division for precision)
        new_h_value = x - viewport_width / 2.0
        new_v_value = y - viewport_height / 2.0
        
        # Clamp to valid scroll ranges
        new_h_value = max(h_scroll.minimum(), min(h_scroll.maximum(), new_h_value))
        new_v_value = max(v_scroll.minimum(), min(v_scroll.maximum(), new_v_value))
        
        # Apply new scroll positions
        h_scroll.setValue(int(round(new_h_value)))
        v_scroll.setValue(int(round(new_v_value)))

class ClickableLabel(QLabel):
    """QLabel that emits clicked signal with position"""
    
    # Custom signal for mouse clicks
    clicked = Signal(object)  # Emits QPoint
    
    def mousePressEvent(self, event):
        """Handle mouse press and emit clicked signal with position"""
        if event.button() == Qt.LeftButton:
            # Emit the position relative to the label
            self.clicked.emit(event.position())
        super().mousePressEvent(event)

class ImageViewer(QMainWindow):
    def __init__(self, image_file=None, splash=None, splash_label=None, splash_img=None):
        super().__init__()
        self.image_file = image_file
        self._splash = splash
        self._splash_label = splash_label
        self._splash_img = splash_img
        self.setup_ui()
        self.setup_actions()
        # Load image if valid file provided, otherwise show open dialog
        if image_file and os.path.isfile(image_file):
            self.load_image()
        else:
            # No file or file doesn't exist - go straight to open dialog
            self.setWindowTitle(f"{PROGRAM_NAME}")
            QTimer.singleShot(100, self.open_file_dialog)  # Delay to ensure window is shown first
        close_splash(self._splash)
        
    def setup_ui(self):
        """Setup the user interface"""
        # Window setup
        if self.image_file:
            title = f"{PROGRAM_NAME} - {os.path.basename(self.image_file)}"
        else:
            title = f"{PROGRAM_NAME}"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 1000, 700)
        
        # Set window icon
        if os.path.isfile(window_icon_path):
            self.setWindowIcon(QIcon(window_icon_path))
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create menu bar
        self.create_menus()

        # Create toolbar
        self.create_toolbar()
        
        # Create scroll area for SVG
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)  # Important: don't resize the SVG widget
        self.scroll_area.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scroll_area)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.zoom_label = QLabel("Zoom: 100%")
        self.status_bar.addPermanentWidget(self.zoom_label)

    def create_menus(self):
        """Create the menu bar (File / Help)."""
        menubar = self.menuBar()

        # ----- File menu -----
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)  # Ctrl+O
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)  # Ctrl+Q
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ----- Help menu -----
        help_menu = menubar.addMenu("&Help")

        help_userguide_action = QAction("&User Guide", self)
        help_userguide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(help_userguide_action)

        instructions_action = QAction("&Instructions", self)
        instructions_action.setShortcut("F1")
        instructions_action.triggered.connect(self.show_help)
        help_menu.addAction(instructions_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        system_info_action = QAction("&System Information", self)
        system_info_action.triggered.connect(self.show_system_info)
        help_menu.addAction(system_info_action)

        help_menu.addSeparator()

        support_menu = help_menu.addMenu("S&upport")

        support_discussions_action = QAction("&Discussions", self)
        support_discussions_action.triggered.connect(self.open_discussions)
        support_menu.addAction(support_discussions_action)

        support_issues_action = QAction("&Issues", self)
        support_issues_action.triggered.connect(self.open_issues)
        support_menu.addAction(support_issues_action)

        support_menu.addSeparator()

        support_bug_action = QAction("Submit &Bug Report", self)
        support_bug_action.triggered.connect(self.submit_bug_report)
        support_menu.addAction(support_bug_action)

        support_feature_action = QAction("Submit &Feature Request", self)
        support_feature_action.triggered.connect(self.submit_feature_request)
        support_menu.addAction(support_feature_action)

        
    def create_toolbar(self):
        """Create the toolbar with zoom controls"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        # Zoom In button
        zoom_in_action = QAction("Zoom In (+)", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        # Zoom Out button  
        zoom_out_action = QAction("Zoom Out (-)", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        toolbar.addSeparator()
        
        # Fit to Window
        fit_action = QAction("Fit to Window", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self.zoom_fit)
        toolbar.addAction(fit_action)
        
        # Actual Size
        actual_action = QAction("Actual Size", self)
        actual_action.setShortcut("Ctrl+1")
        actual_action.triggered.connect(self.zoom_actual)
        toolbar.addAction(actual_action)
        
        # Scale (custom zoom percentage)
        scale_action = QAction("Scale...", self)
        scale_action.setShortcut("Ctrl+Shift+S")
        scale_action.triggered.connect(self.zoom_scale_dialog)
        toolbar.addAction(scale_action)
        
        # Center image
        center_action = QAction("Center", self)
        center_action.setShortcut("Ctrl+Shift+C")
        center_action.triggered.connect(self.center_image)
        toolbar.addAction(center_action)
        
        # Map navigator
        map_action = QAction("Map", self)
        map_action.setShortcut("Ctrl+M")
        map_action.triggered.connect(self.show_map_navigator)
        toolbar.addAction(map_action)
        
    def setup_actions(self):
        """Setup keyboard shortcuts and actions"""
        # Close window
        self.close_action = QAction("Close", self)
        self.close_action.setShortcut("Escape")
        self.close_action.triggered.connect(self.close)
        self.addAction(self.close_action)
        
        # Enable mouse tracking for panning info
        self.setMouseTracking(True)
        
    def load_image(self):
        """Load and display the image file"""
        update_splash(getattr(self, '_splash', None), getattr(self, '_splash_label', None), getattr(self, '_splash_img', None), 'Loading file...')
        if not self.image_file or not os.path.exists(self.image_file):
            if self.image_file:  # Only show error if a file was specified
                QMessageBox.critical(self, "File Not Found", 
                    f"Image file not found:\n{self.image_file}")
            return
            
        try:
            # Create image widget
            self.image_widget = ZoomableImageWidget(self.image_file)
            
            if not self.image_widget.is_valid():
                QMessageBox.critical(self, "Invalid Image", 
                    f"Could not load image file:\n{self.image_file}")
                return
                
            # Connect zoom change signal to status bar update
            self.image_widget.zoomChanged.connect(self.on_zoom_changed)
                
            # Add to scroll area - this establishes the parent relationship needed for zoom
            self.scroll_area.setWidget(self.image_widget)
            
            # Auto-fit after a short delay to ensure window is properly sized
            QTimer.singleShot(100, self.initial_fit)
            
            self.status_bar.showMessage(f"Loaded: {os.path.basename(self.image_file)} | Press F1 for help")
            self.update_zoom_label()
            
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Image", 
                f"Error loading image file:\n{str(e)}")
            
    def initial_fit(self):
        """Perform initial fit-to-window"""
        if hasattr(self, 'image_widget'):
            self.zoom_fit()
        
    def zoom_in(self):
        """Zoom in by 15% centered on visible area"""
        if not hasattr(self, 'image_widget'):
            return
        # Get center of visible area
        center = self.get_visible_center()
        self.image_widget.zoom_at_point(1.15, center)
        # Note: zoom label updated automatically via signal
        
    def zoom_out(self):
        """Zoom out by 15% centered on visible area"""
        if not hasattr(self, 'image_widget'):
            return
        # Get center of visible area  
        center = self.get_visible_center()
        self.image_widget.zoom_at_point(1 / 1.15, center)
        # Note: zoom label updated automatically via signal
        
    def get_visible_center(self):
        """Get the center point of the currently visible area"""
        if not hasattr(self, 'image_widget'):
            return QPointF(0, 0)
        
        # Get scroll area viewport size
        viewport_size = self.scroll_area.viewport().size()
        
        # Get current scroll positions
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        
        # Calculate center point in widget coordinates
        center_x = h_scroll.value() + viewport_size.width() / 2
        center_y = v_scroll.value() + viewport_size.height() / 2
        
        return QPointF(center_x, center_y)
        
    def zoom_fit(self):
        """Fit image to window size"""
        if not hasattr(self, 'image_widget'):
            return
        container_size = self.scroll_area.size()
        self.image_widget.zoom_to_fit(container_size)
        # Note: zoom label updated automatically via signal
        
    def zoom_actual(self):
        """Reset to actual size (100%)"""
        if not hasattr(self, 'image_widget'):
            return
        self.image_widget.zoom_actual_size()
        # Note: zoom label updated automatically via signal
        
    def update_zoom_label(self):
        """Update the zoom percentage in status bar"""
        if hasattr(self, 'image_widget'):
            zoom_percent = int(self.image_widget.scale_factor * 100)
            self.zoom_label.setText(f"Zoom: {zoom_percent}%")
        else:
            self.zoom_label.setText("Zoom: --")
        
    def on_zoom_changed(self, scale_factor):
        """Handle zoom change signal from image widget"""
        zoom_percent = int(scale_factor * 100)
        self.zoom_label.setText(f"Zoom: {zoom_percent}%")
        
    def zoom_scale_dialog(self):
        """Show dialog for manual zoom percentage entry"""
        if not hasattr(self, 'image_widget'):
            return
        # Get current zoom percentage
        current_percent = int(self.image_widget.scale_factor * 100)
        
        # Show input dialog
        percentage, ok = QInputDialog.getInt(
            self, 
            "Set Zoom Scale",
            f"Enter zoom percentage ({int(ZoomLimits.MIN*100)}-{int(ZoomLimits.MAX*100)}):", 
            value=current_percent,
            minValue=ZoomLimits.MIN*100,
            maxValue=ZoomLimits.MAX*100,  # Allow up to 500% zoom
            step=1
        )
        
        if ok:
            self.image_widget.set_zoom_percentage(percentage)
            
    def center_image(self):
        """Center the image in the scroll area at current zoom level"""
        if not hasattr(self, 'image_widget'):
            return
        # Get image widget size (current zoom size)
        image_size = self.image_widget.size()
        
        # Get scroll area viewport size
        viewport_size = self.scroll_area.viewport().size()
        
        # Calculate center positions
        center_x = max(0, (image_size.width() - viewport_size.width()) // 2)
        center_y = max(0, (image_size.height() - viewport_size.height()) // 2)
        
        # Set scroll bar positions to center the image
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        
        h_scroll.setValue(center_x)
        v_scroll.setValue(center_y)
        
    def show_map_navigator(self):
        """Show the map navigator dialog"""
        if hasattr(self, 'image_widget'):
            navigator = NavigatorDialog(self.image_widget, self.scroll_area, self)
            navigator.exec()
            
    def open_file_dialog(self):
        """Show file dialog to open a new image file"""
        # Create file filter for supported formats
        file_filter = "Image Files (*.svg *.svgz *.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp);;"\
                     "SVG Files (*.svg *.svgz);;"\
                     "PNG Files (*.png);;"\
                     "JPEG Files (*.jpg *.jpeg);;"\
                     "Bitmap Files (*.bmp);;"\
                     "GIF Files (*.gif);;"\
                     "TIFF Files (*.tiff *.tif);;"\
                     "WebP Files (*.webp);;"\
                     "All Files (*.*)"
        
        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image File",
            "",
            file_filter
        )
        
        if file_path:
            self.load_new_image(file_path)
            
    def load_new_image(self, file_path):
        """Load a new image file"""
        try:
            # Update the image file path
            self.image_file = file_path
            
            # Create new image widget
            new_image_widget = ZoomableImageWidget(file_path)
            
            if not new_image_widget.is_valid():
                QMessageBox.critical(self, "Invalid Image", 
                    f"Could not load image file:\n{file_path}")
                return
            
            # Replace the old image widget
            if hasattr(self, 'image_widget'):
                # Disconnect old signals
                self.image_widget.zoomChanged.disconnect()
                
            self.image_widget = new_image_widget
            
            # Connect zoom change signal to status bar update
            self.image_widget.zoomChanged.connect(self.on_zoom_changed)
            
            # Add to scroll area
            self.scroll_area.setWidget(self.image_widget)
            
            # Update window title
            self.setWindowTitle(f"{PROGRAM_NAME} - {os.path.basename(file_path)}")
            
            # Auto-fit after a short delay
            QTimer.singleShot(100, self.initial_fit)
            
            # Update status
            self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)} | Press F1 for help")
            self.update_zoom_label()
            
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Image", 
                f"Error loading image file:\n{str(e)}")

    def show_about_OLD(self):
        """Display About dialog with version and copyright information."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"About {PROGRAM_NAME}")

        # Set icon if available
        window_icon_path = os.path.join(_RES_DIR, f"{PROGRAM_NAME}.ico")
        if os.path.isfile(window_icon_path):
            icon = QIcon(window_icon_path)
            msg_box.setIconPixmap(icon.pixmap(48, 48))

        about_text = f"""
        <b>{PROGRAM_NAME}</b><br>
        Version {APP_VERSION}<br>
        {APP_DESCRIPTION}<br><br>
        <b>Author:</b> {APP_AUTHOR}<br>
        <b>Company:</b> {APP_COMPANY}<br>
        <b>Date:</b> {APP_DATE}<br>
        <br>
        {APP_COPYRIGHT}
        """

        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(about_text.strip())
        msg_box.exec()

    def show_about(self):
        """Display About dialog with version and copyright information"""
        # debugging.enter()

        about_text = f"""
            <h2>{PROGRAM_NAME}</h2>
            <p><b>Version:</b> {APP_VERSION}</p>
            <p><b>Description:</b> {APP_DESCRIPTION}</p>
            <p><b>Author:</b> {APP_AUTHOR}</p>
            <p><b>Company:</b> {APP_COMPANY}</p>
            <p><b>Date:</b> {APP_DATE}</p>
            <p>{APP_COPYRIGHT}</p>
            """

        dlg = QDialog(self)
        dlg.setWindowTitle(f"About {PROGRAM_NAME}")

        icon_path = os.path.join(_RES_DIR, f"{PROGRAM_NAME}.ico")
        icon_exists = os.path.isfile(icon_path)
        if icon_exists:
            icon = QIcon(icon_path)
            dlg.setWindowIcon(icon)

        icon_label = QLabel()
        if icon_exists:
            icon_label.setPixmap(icon.pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignTop)

        content = QLabel()
        content.setTextFormat(Qt.RichText)
        content.setText(about_text)
        content.setWordWrap(True)
        content.setOpenExternalLinks(True)

        body_layout = QHBoxLayout()
        body_layout.addWidget(icon_label)
        body_layout.addWidget(content)

        copy_btn  = QPushButton("Copy to Clipboard")
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)

        def copy_to_clipboard():
            QApplication.clipboard().setText(html_to_plain_text(about_text))
            copy_btn.setText("Copied")
            QTimer.singleShot(1500, lambda: copy_btn.setText("Copy to Clipboard"))

        copy_btn.clicked.connect(copy_to_clipboard)
        close_btn.clicked.connect(dlg.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(close_btn)

        layout = QVBoxLayout(dlg)
        layout.addLayout(body_layout)
        layout.addLayout(btn_layout)

        dlg.exec()
        # debugging.leave()

    def show_system_info_OLD(self):
        """Display System Information dialog with Python and module versions."""
        python_version = sys.version.split()[0]

        module_list = ['PySide6', 'pandas', 'numpy', 'matplotlib', 'configparser']
        module_versions = []
        for module_name in module_list:
            try:
                ver = get_module_version(module_name)
            except Exception:
                ver = "(version not found)"
            module_versions.append(f"<tr><td>{module_name}</td><td>{ver}</td></tr>")

        system_text = f"""
            <b>Application</b><br>
            {PROGRAM_NAME} {APP_VERSION}<br><br>

            <b>Python</b><br>
            {python_version}<br><br>

            <b>Platform</b><br>
            {platform.platform()}<br><br>

            <b>Executable</b><br>
            {sys.executable}<br><br>

            <b>Working Directory</b><br>
            {os.getcwd()}<br><br>

            <b>Modules</b><br>
            <table border="1" cellspacing="0" cellpadding="3">
                <tr><th>Module</th><th>Version</th></tr>
                {''.join(module_versions)}
            </table>
            """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("System Information")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(system_text.strip())
        msg_box.exec()

    def _build_sysinfo_html(self) -> str:
        """Build and return the System Information HTML string."""
        # Get Python version
        python_version, python_details = sys.version.split(' ', 1)
        python_build, python_compile = python_details.split(') [', 1)
        python_build = python_build + ')'
        python_compile = '[' + python_compile

        # Get module versions
        module_list = ['PySide6', 'platformdirs']
        module_versions = []
        for module_name in module_list:
            try:
                ver = get_module_version(module_name)
                module_versions.append(f"<tr><td>&nbsp;&nbsp;{module_name}</td><td>&nbsp;{ver}</td></tr>")
            except Exception:
                module_versions.append(f"<tr><td>&nbsp;&nbsp;{module_name}</td><td>&nbsp;<i>(version not found)</i></td></tr>")

        os_info      = get_os_info()
        platform_str = platform.platform()
        current_dir  = os.getcwd()
        script_path  = os.path.dirname(os.path.abspath(__file__))
        config_path  = user_config_dir(APP_PACKAGE, APP_COMPANY, roaming=True)
        log_path     = user_log_dir(APP_PACKAGE, APP_COMPANY)

        return f"""
            <h3>System Information</h3>
            <p><b>Application:</b> {PROGRAM_NAME} v{APP_VERSION}</p>

            <p><b>Operating System:</b> {os_info}</p>
            <p><b>Platform:</b> {platform_str}</p>

            <p><b>Python Version:</b> {python_version}<br>&nbsp;&nbsp;{python_build}<br>&nbsp;&nbsp;{python_compile}</p>
            <p><b>Third-Party Packages:</b></p>
            <table border="0" cellpadding="0">
            {''.join(module_versions)}
            </table>

            <p><b>File Paths:</b></p>
            <table border="0" cellpadding="3">
            <tr><td><b>Working Directory:</b></td><td>{current_dir}</td></tr>
            <tr><td><b>Script Directory:</b></td><td>{script_path}</td></tr>
            <tr><td><b>Config Directory:</b></td><td>{config_path}</td></tr>
            <tr><td><b>Log Directory:</b></td><td>{log_path}</td></tr>
            </table>
            """

    def show_system_info(self):
        """Display System Information dialog with Python and module versions"""

        sysinfo_text = self._build_sysinfo_html()

        dlg = QDialog(self)
        dlg.setWindowTitle("System Information")

        icon_path = os.path.join(_RES_DIR, f"{PROGRAM_NAME}.ico")
        icon_exists = os.path.isfile(icon_path)
        if icon_exists:
            icon = QIcon(icon_path)
            dlg.setWindowIcon(icon)

        icon_label = QLabel()
        if icon_exists:
            icon_label.setPixmap(icon.pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignTop)

        content = QLabel()
        content.setTextFormat(Qt.RichText)
        content.setText(sysinfo_text)
        content.setWordWrap(True)

        body_layout = QHBoxLayout()
        body_layout.addWidget(icon_label)
        body_layout.addWidget(content)

        copy_btn  = QPushButton("Copy to Clipboard")
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)

        def copy_to_clipboard():
            QApplication.clipboard().setText(html_to_plain_text(sysinfo_text))
            copy_btn.setText("Copied")
            QTimer.singleShot(1500, lambda: copy_btn.setText("Copy to Clipboard"))

        copy_btn.clicked.connect(copy_to_clipboard)
        close_btn.clicked.connect(dlg.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(close_btn)

        layout = QVBoxLayout(dlg)
        layout.addLayout(body_layout)
        layout.addLayout(btn_layout)

        dlg.exec()

    def open_discussions(self):
        """Open the PTTimeline GitHub Discussions page in the default browser."""
        webbrowser.open_new_tab(f"{APP_REPO_URL}/discussions")

    def open_issues(self):
        """Open the PTTimeline GitHub Issues page in the default browser."""
        webbrowser.open_new_tab(f"{APP_REPO_URL}/issues")

    def submit_bug_report(self):
        """Open a pre-filled GitHub bug report issue form in the default browser."""
        try:
            context = {
                "Which Application(s)?": PROGRAM_NAME,
                "Version":               f"v{APP_VERSION}",
                "Operating System":      get_os_info(),
                "System Information":    html_to_plain_text(self._build_sysinfo_html()),
            }
            url = build_issue_url(APP_REPO_URL, "bug_report.md", context)
            webbrowser.open_new_tab(url)
        except Exception as e:
            QMessageBox.warning(self, "Network Error",
                f"Could not reach GitHub to open the bug report form.\n\nPlease check your internet connection and try again.\n\nDetails: {e}")

    def submit_feature_request(self):
        """Open a pre-filled GitHub feature request issue form in the default browser."""
        try:
            context = {
                "Which application(s)?": PROGRAM_NAME,
                "Version":               f"v{APP_VERSION}",
                "Operating System":      get_os_info(),
            }
            url = build_issue_url(APP_REPO_URL, "feature_request.md", context)
            webbrowser.open_new_tab(url)
        except Exception as e:
            QMessageBox.warning(self, "Network Error",
                f"Could not reach GitHub to open the feature request form.\n\nPlease check your internet connection and try again.\n\nDetails: {e}")

        
    def show_user_guide(self):
        """Open the PTTView User Guide HTML file in the default browser."""
        guide_path = Path(_APP_DIR) / "docs" / "PTTView_UserGuide.html"
        if guide_path.is_file():
            webbrowser.open_new_tab(guide_path.as_uri())
        else:
            QMessageBox.warning(self, "User Guide Not Found",
                f"The User Guide could not be found:\n{guide_path}")

    def show_help(self):
        """Show help dialog with mouse and keyboard controls"""
        help_text = """
            <h3>PTTimeline Image Viewer - Controls</h3>

            <p><b>Supported formats:</b> SVG, PNG, JPG, JPEG, BMP, GIF, TIFF, WEBP</p>

            <p><b>Note:</b> Complex SVG files may show checkerboard patterns for unsupported elements due to Qt SVG renderer limitations.</p>

            <h4>File Operations:</h4>
            <ul>
            <li><b>Ctrl + O:</b> Open - Select and load image file</li>
            </ul>

            <h4>Mouse Controls:</h4>
            <ul>
            <li><b>Mouse Wheel:</b> Vertical panning</li>
            <li><b>Shift + Mouse Wheel:</b> Horizontal panning</li>
            <li><b>Ctrl + Mouse Wheel:</b> Zoom in/out (centered on cursor)</li>
            </ul>

            <h4>Keyboard Shortcuts:</h4>
            <ul>
            <li><b>Ctrl + Plus/Minus:</b> Zoom in/out (centered on view)</li>
            <li><b>Ctrl + 0:</b> Fit to window</li>
            <li><b>Ctrl + 1:</b> Actual size (100%)</li>
            <li><b>Ctrl + Shift + S:</b> Scale - Set custom zoom percentage</li>
            <li><b>Ctrl + Shift + C:</b> Center - Center image at current zoom</li>
            <li><b>Ctrl + M:</b> Map - Navigate with thumbnail overview</li>
            <li><b>Arrow Keys:</b> Pan up/down/left/right</li>
            <li><b>F11:</b> Toggle fullscreen</li>
            <li><b>F1:</b> Show this help</li>
            <li><b>Escape:</b> Close viewer</li>
            </ul>
                    """
        
        QMessageBox.about(self, "Help - Controls", help_text)
        
    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F1:
            # Show help
            self.show_help()
        elif event.key() == Qt.Key_F11:
            # Toggle fullscreen
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Left:
            # Pan left
            if hasattr(self, 'image_widget'):
                self.pan_horizontal(120)  # Positive for left
        elif event.key() == Qt.Key_Right:
            # Pan right  
            if hasattr(self, 'image_widget'):
                self.pan_horizontal(-120)  # Negative for right
        elif event.key() == Qt.Key_Up:
            # Pan up
            if hasattr(self, 'image_widget'):
                self.pan_vertical(120)  # Positive for up
        elif event.key() == Qt.Key_Down:
            # Pan down
            if hasattr(self, 'image_widget'):
                self.pan_vertical(-120)  # Negative for down
        else:
            super().keyPressEvent(event)
            
    def pan_horizontal(self, delta):
        """Pan horizontally using the scroll bar"""
        h_scroll = self.scroll_area.horizontalScrollBar()
        new_value = h_scroll.value() + delta
        h_scroll.setValue(new_value)
        
    def pan_vertical(self, delta):
        """Pan vertically using the scroll bar"""
        v_scroll = self.scroll_area.verticalScrollBar()
        new_value = v_scroll.value() + delta
        v_scroll.setValue(new_value)

def parse_command_line_args():
    """Parse and validate command line arguments before any system initialization"""
    # NOTE: No debugging calls here since debugging system not yet initialized
    
    # Check for too many arguments
    if len(sys.argv) > 2:
        print("Usage: PTTView [filename.<svg|png|jpg|jpeg|bmp|gif|tiff|webp>]")
        sys.exit(1)
    
    # Get filename if provided
    filename = None
    if len(sys.argv) == 2:
        # try:
            filename = os.path.abspath(sys.argv[1])
            
            # Check if file exists (don't auto-append any extension)
            if not os.path.isfile(filename):
                raise FileNotFoundError(f"{filename}")
                # print(f"Error: File not found: {filename}")
                # sys.exit(1)
                
        # except Exception as e:
            # print(f"Error processing filename '{sys.argv[1]}': {e}")
            # sys.exit(1)
    
    return filename

def main(filename=None, splash=None, splash_label=None, splash_img=None):
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application icon (used by message boxes and system dialogs)
    if os.path.isfile(window_icon_path):
        app.setWindowIcon(QIcon(window_icon_path))
    
    # Create and show viewer
    viewer = ImageViewer(filename, splash=splash, splash_label=splash_label, splash_img=splash_img)
    viewer.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    # Show splash screen FIRST - before any other initialization
    _splash, _splash_label, _splash_img = show_splash()

    # Install crash logger FIRST - before anything else can fail.
    # USER_LOG_PATH is defined at module level via platformdirs.
    crash_logger = CrashLogger(
        app_name     = PROGRAM_NAME,
        app_version  = APP_VERSION,
        log_dir      = USER_LOG_PATH,
        log_filename = 'pttview_crash_log.txt',
    )
    crash_logger.install()

    # Parse and validate command line arguments FIRST - before any other initialization
    filename = parse_command_line_args()
    
    main(filename, splash=_splash, splash_label=_splash_label, splash_img=_splash_img)
