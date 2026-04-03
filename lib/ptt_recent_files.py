"""
ptt_recent_files.py — Shared Recent Files manager for PTTimeline apps.

Each app instantiates one (or two, for PTTPlot) RecentFiles objects.
The list is persisted in the app's user INI file under [RECENT_FILES],
using a plain configparser write (no ConfigUpdater — no comments to
preserve in this dynamic-state section).

Usage
-----
    from ptt_recent_files import RecentFiles

    # At startup, after the user INI path is known:
    recent = RecentFiles(user_ini_path, section='RECENT_FILES', max_entries=15)

    # Get the directory to pass to QFileDialog:
    dialog_dir = recent.get_dialog_dir()

    # After a successful open/save:
    recent.add(file_path)

    # Build the QMenu (call from aboutToShow signal):
    menu = recent.build_menu(parent_widget, open_callback)

INI section format
------------------
    [RECENT_FILES]
    file_0=C:\\Users\\Richard\\Documents\\my_project.pttd
    file_1=C:\\Users\\Richard\\Documents\\other.pttd
    ...

The section name is caller-supplied so PTTPlot can maintain two separate
sections ('RECENT_FILES_PTTD' and 'RECENT_FILES_PTTP') in the same INI.
"""

import os
import configparser

from PySide6.QtWidgets import QMenu, QToolTip
from PySide6.QtGui import QAction, QCursor


# Maximum label length for menu display (chars); longer paths are elided
_MAX_DISPLAY_LEN = 60


def _elide_path(path, max_len=_MAX_DISPLAY_LEN):
    """Return a shortened display string for long paths.

    Shows the filename and as much of the leading path as fits, inserting
    '...' in the middle when necessary.

    Examples
    --------
        'C:\\...\\Documents\\my_project.pttd'
    """
    if len(path) <= max_len:
        return path
    basename = os.path.basename(path)
    # Always show the full filename; elide the directory portion
    head = path[:max_len // 2 - 2]
    return f'{head}...{os.sep}{basename}'


class RecentFiles:
    """Manages a single recent-files list for one app / one file type."""

    def __init__(self, ini_path: str, section: str = 'RECENT_FILES',
                 max_entries: int = 15):
        """
        Parameters
        ----------
        ini_path    : Full path to the app's user INI file (e.g. pttedit.ini).
        section     : INI section name.  Use distinct names when one INI holds
                      multiple lists (PTTPlot uses RECENT_FILES_PTTD and
                      RECENT_FILES_PTTP).
        max_entries : Maximum number of entries to keep (default 15).
        """
        self._ini_path    = ini_path
        self._section     = section
        self._max_entries = max_entries
        self._files: list[str] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_list(self) -> list[str]:
        """Return the list of valid (existing) recent file paths, newest first."""
        return list(self._files)

    def get_dialog_dir(self) -> str:
        """Return the directory of the most recent entry, or '' if list is empty."""
        if self._files:
            return os.path.dirname(self._files[0])
        return ''

    def add(self, file_path: str) -> None:
        """Prepend file_path to the list (dedup, trim, save).

        No-op if file_path is already list[0] (same file re-opened).
        """
        file_path = os.path.normpath(os.path.abspath(file_path))

        # No-op if already at the top
        if self._files and self._files[0] == file_path:
            return

        # Remove any existing occurrence (dedup), then prepend
        try:
            self._files.remove(file_path)
        except ValueError:
            pass
        self._files.insert(0, file_path)

        # Trim to max
        self._files = self._files[:self._max_entries]

        self._save()

    def clear(self) -> None:
        """Remove all entries and save."""
        self._files = []
        self._save()

    def build_menu(self, parent_widget, open_callback) -> QMenu:
        """Build and return a populated 'Open Recent' QMenu.

        Parameters
        ----------
        parent_widget : The QWidget that owns the menu (for Qt parenting).
        open_callback : Callable(file_path: str) — called when user clicks
                        an entry.  The caller is responsible for any
                        unsaved-changes check before calling add().

        The returned QMenu should be set as the submenu of the 'Open Recent'
        action; connect the parent menu's aboutToShow to call this and
        re-assign the submenu each time so the list stays current.
        """
        menu = QMenu(parent_widget)

        # Refresh: drop entries that no longer exist on disk
        pruned = [f for f in self._files if os.path.isfile(f)]
        if len(pruned) < len(self._files):
            self._files = pruned
            self._save()
        else:
            self._files = pruned

        if not self._files:
            empty_action = QAction('(empty)', parent_widget)
            empty_action.setEnabled(False)
            menu.addAction(empty_action)
        else:
            for i, file_path in enumerate(self._files):
                display = _elide_path(file_path)
                # Prefix 1–9 with an accelerator digit
                if i < 9:
                    label = f'&{i + 1}  {display}'
                else:
                    label = f'   {display}'
                action = QAction(label, parent_widget)
                # Capture file_path in closure
                action.triggered.connect(
                    lambda checked=False, fp=file_path: open_callback(fp)
                )
                action.hovered.connect(
                    lambda fp=file_path: QToolTip.showText(
                        QCursor.pos(), fp, menu
                    )
                )
                menu.addAction(action)

        menu.addSeparator()
        clear_action = QAction('&Clear Recent Files', parent_widget)
        clear_action.triggered.connect(self.clear)
        menu.addAction(clear_action)

        return menu

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Read the section from the INI file; silently ignore missing file/section."""
        self._files = []
        if not self._ini_path or not os.path.isfile(self._ini_path):
            return

        cfg = configparser.RawConfigParser(
            comment_prefixes=(';',), inline_comment_prefixes=()
        )
        try:
            cfg.read(self._ini_path, encoding='utf-8')
        except Exception:
            return

        if not cfg.has_section(self._section):
            return

        # Read file_0, file_1, … in order, stop at first missing key
        loaded = []
        i = 0
        while True:
            key = f'file_{i}'
            if not cfg.has_option(self._section, key):
                break
            val = cfg.get(self._section, key).strip()
            if val:
                val = os.path.normpath(os.path.abspath(val))
                # Silently drop stale entries (file no longer exists)
                if os.path.isfile(val):
                    loaded.append(val)
            i += 1

        self._files = loaded[:self._max_entries]

        # If any stale entries were dropped, persist the pruned list immediately
        if len(self._files) < i:
            self._save()

    def _save(self) -> None:
        """Write (or overwrite) the section in the INI file.

        Uses a plain RawConfigParser read-modify-write so that other
        sections in the INI are preserved.  No backup is taken — recent
        files change too frequently to warrant one.
        """
        if not self._ini_path:
            return

        cfg = configparser.RawConfigParser(
            comment_prefixes=(';',), inline_comment_prefixes=()
        )
        try:
            if os.path.isfile(self._ini_path):
                cfg.read(self._ini_path, encoding='utf-8')
        except Exception:
            pass

        # Replace the section wholesale
        if cfg.has_section(self._section):
            cfg.remove_section(self._section)
        cfg.add_section(self._section)

        for i, file_path in enumerate(self._files):
            cfg.set(self._section, f'file_{i}', file_path)

        try:
            with open(self._ini_path, 'w', encoding='utf-8') as f:
                cfg.write(f)
        except Exception:
            pass  # Non-fatal — recent files are a convenience, not critical data
