import os
import sys
import inspect
import platform
import re
import subprocess
import traceback
import ctypes
from datetime import datetime
import importlib.metadata
from importlib.metadata import version, PackageNotFoundError


class CrashLogger:
    """
    Installs a global exception handler that:
      - Writes a crash log (with header, traceback) to the user log directory
      - Shows a tkinter dialog with the log path and an Open Log button
    Works before and after Qt is initialized. Captures both regular exceptions
    and KeyboardInterrupt. Cross-platform: Windows, macOS, Linux.

    Usage (as early as possible in __main__):
        crash_logger = CrashLogger(
            app_name    = PROGRAM_NAME,
            app_version = APP_VERSION,
            log_dir     = USER_LOG_PATH,
            log_filename= 'pttedit_crash.log',
        )
        crash_logger.install()
    """

    def __init__(self, app_name, app_version, log_dir, log_filename):
        self.app_name    = app_name
        self.app_version = app_version
        self.log_dir     = log_dir
        self.log_path    = os.path.join(log_dir, log_filename)

    def install(self):
        """Install sys.excepthook to catch all unhandled exceptions."""
        sys.excepthook = self._handle_exception

    def _os_info(self):
        """Return a human-readable OS string, with Windows 11 detection."""
        os_name    = platform.system()
        os_release = platform.release()
        platform_str = platform.platform()

        if os_name == 'Windows' and os_release == '10':
            build_match = re.search(r'10\.0\.(\d+)', platform_str)
            if build_match:
                build_num = int(build_match.group(1))
                if build_num >= 22000:
                    return f'Windows 11 (Build {build_num})'
                else:
                    return f'Windows 10 (Build {build_num})'
        return f'{os_name} {os_release}'

    def _write_crash_log(self, exc_type, exc_value, exc_tb):
        """Write crash log file, overwriting any previous crash log."""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            python_version = sys.version.split()[0]
            os_info = self._os_info()

            # Format the full traceback
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
            tb_text  = ''.join(tb_lines).rstrip()

            with open(self.log_path, 'w', encoding='utf-8') as f:
                f.write('=' * 60 + '\n')
                f.write(f'{self.app_name} CRASH LOG\n')
                f.write('=' * 60 + '\n')
                f.write(f'Date/Time:  {now}\n')
                f.write(f'App:        {self.app_name} {self.app_version}\n')
                f.write(f'OS:         {os_info}\n')
                f.write(f'Python:     {python_version}\n')
                f.write('\n')
                f.write(tb_text + '\n')
                f.write('=' * 60 + '\n')

        except Exception as e:
            # If we can't write the log, note it but don't suppress the crash
            self.log_path = f'(could not write log: {e})'

    def _open_log_file(self):
        """Open the crash log in the default text editor, cross-platform."""
        try:
            os_name = platform.system()
            if os_name == 'Windows':
                os.startfile(self.log_path)
            elif os_name == 'Darwin':
                subprocess.run(['open', self.log_path])
            else:
                subprocess.run(['xdg-open', self.log_path])
        except Exception:
            pass

    def _show_message_box(self, exc_type, exc_value):
        """Show a tkinter crash dialog with an Open Log button — works with or without Qt.
        Handles both cases: no existing Tk() root (pre-Qt / post-splash) and an existing
        Tk() root (crash during splash or inside main)."""
        try:
            import tkinter as tk

            title        = f'{self.app_name} - Unexpected Error'
            exc_name     = exc_type.__name__ if exc_type else 'Unknown Error'
            exc_msg      = str(exc_value) if exc_value else ''
            error_detail = f'{exc_name}: {exc_msg}' if exc_msg else exc_name
            message = (
                f'{self.app_name} encountered an unexpected error and must close.\n\n'
                f'{error_detail}\n\n'
                f'A crash log has been saved to:\n'
                f'{self.log_path}\n\n'
                f'Please send this file when reporting the problem.'
            )

            # DPI awareness on Windows so the dialog isn't blurry on HiDPI displays
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

            # Use existing Tk() root if one exists (e.g. splash still alive),
            # otherwise create a hidden one. Always build the visible dialog as Toplevel.
            existing_root = tk._default_root
            if existing_root is None:
                root  = tk.Tk()
                root.withdraw()
                owner = root
            else:
                root  = None
                owner = existing_root

            dialog = tk.Toplevel(owner)
            dialog.title(title)
            dialog.resizable(False, False)
            dialog.attributes('-topmost', True)

            # Use system default font at a readable size — cross-platform
            import tkinter.font as tkfont
            default_font = tkfont.nametofont('TkDefaultFont')
            ui_font = (default_font.cget('family'), 14)

            msg_label = tk.Label(
                dialog, text=message,
                justify='left', wraplength=460,
                padx=20, font=ui_font
            )
            msg_label.pack(pady=(20, 10))

            # Button row
            btn_frame = tk.Frame(dialog, pady=10)
            btn_frame.pack()

            open_btn = tk.Button(
                btn_frame, text='Open Log', width=12,
                command=self._open_log_file, font=ui_font
            )
            open_btn.pack(side='left', padx=8)

            close_btn = tk.Button(
                btn_frame, text='Close', width=12,
                command=dialog.destroy, font=ui_font
            )
            close_btn.pack(side='left', padx=8)

            # Centre on primary monitor
            dialog.update_idletasks()
            w = dialog.winfo_reqwidth()
            h = dialog.winfo_reqheight()
            try:
                user32 = ctypes.windll.user32
                sw = user32.GetSystemMetrics(0)
                sh = user32.GetSystemMetrics(1)
            except Exception:
                sw = dialog.winfo_screenwidth()
                sh = dialog.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            dialog.geometry(f'+{x}+{y}')

            if root is not None:
                root.mainloop()       # We own the root — run the event loop
            else:
                dialog.wait_window() # Root is owned elsewhere — block until dialog closes

        except Exception:
            pass  # Last resort — if tkinter fails there's nothing more we can do

    def _handle_exception(self, exc_type, exc_value, exc_tb):
        """sys.excepthook handler — called for all unhandled exceptions."""
        self._write_crash_log(exc_type, exc_value, exc_tb)
        self._show_message_box(exc_type, exc_value)
        sys.exit(1)


# =============================================================================

class Debugging:
    def __init__(self, enabled = False):
        self._level = 0
        self.exclude = {}
        self.enabled = enabled
        self.output_filename = None        # if output to other than stdout
        self.output_file = sys.stdout      # default output file is stdout
        return
        
    def __del__(self):
        if ((self.output_file != None) and (self.output_file != sys.stdout)): self.output_file.close()
        return

    def set_enabled(self, enabled):
        self.enabled = enabled
        return
        
    def set_output_filename(self, output_filename):
        if (output_filename == None):
            self.output_filename = None
            if ((self.output_file != None) and (self.output_file != sys.stdout)): self.output_file.close()
            self.output_file = sys.stdout
        else:
            self.output_filename = output_filename
            self.output_file = None
        return

    def exclude_add(self, className, methodName):
        if (className is None) or (methodName is None): return
        if (className not in self.exclude):
            self.exclude[className] = set()
        self.exclude[className].add(methodName)
        return
        
    def exclude_remove(self, className, methodName):
        if (className is None) or (methodName is None): return
        if (className in self.exclude):
            if (methodName == '*'):
                self.exclude.pop(className)
            elif (methodName in self.exclude[className]):
                self.exclude[className].remove(methodName)
                if (not self.exclude[className]):
                    self.exclude.pop(className)
        return
        
    def is_excluded(self, className, methodName):
        if (className in self.exclude):
            if (('*' in self.exclude[className]) or (methodName in self.exclude[className])):
                return(True)
        return(False)
        
    def _print(self, output_line):
        if ((self.output_file == None) and (self.output_filename != None)):
            try:
                self.output_file = open(self.output_filename, 'w', encoding='utf-8')
            except Exception as e:  # revert to stdout if output file can not be opened
                self.output_file = sys.stdout
                self.output_filename = None
        print(output_line, file=self.output_file)
        self.output_file.flush()
        return
        
    def print(self, msg=''):
        if (self.enabled == False): return
        indent = '  '*self._level
        stack = inspect.stack()
        try:
            the_file = os.path.basename(stack[1].filename)
        except Exception:
            the_file = ''
        try:
            the_lineno = stack[1].lineno
        except Exception:
            the_lineno = ''
        try:
            the_class = stack[1][0].f_locals["self"].__class__.__name__
        except KeyError:
            the_class = ''
        the_method = stack[1][0].f_code.co_name
        if (self.is_excluded(the_class, the_method)): return
        self._print(f'{indent}{the_file}#{the_lineno}::{the_class}::{the_method}: {msg}')
        return
        
    def enter(self, msg=''):
        if (self.enabled == False): return
        indent = '  '*self._level
        self._level += 1
        stack = inspect.stack()
        try:
            the_file = os.path.basename(stack[1].filename)
        except Exception:
            the_file = ''
        try:
            the_lineno = stack[1].lineno
        except Exception:
            the_lineno = ''
        try:
            the_class = stack[1][0].f_locals["self"].__class__.__name__
        except KeyError:
            the_class = ''
        the_method = stack[1][0].f_code.co_name
        if (self.is_excluded(the_class, the_method)): return
        self._print(f'{indent}{the_file}#{the_lineno}::{the_class}::{the_method}:Enter: {msg}')
        return

    def leave(self, msg=''):
        if (self.enabled == False): return
        if (self._level > 0): self._level -= 1
        indent = '  '*self._level
        stack = inspect.stack()
        try:
            the_file = os.path.basename(stack[1].filename)
        except Exception:
            the_file = ''
        try:
            the_lineno = stack[1].lineno
        except Exception:
            the_lineno = ''
        try:
            the_class = stack[1][0].f_locals["self"].__class__.__name__
        except KeyError:
            the_class = ''
        the_method = stack[1][0].f_code.co_name
        if (self.is_excluded(the_class, the_method)): return
        self._print(f'{indent}{the_file}#{the_lineno}::{the_class}::{the_method}:Leave: {msg}')
        return

    def log_module_versions(self, module_list=None):
        """
        Log versions of imported modules to the debug output.
        
        Args:
            module_list: Optional list of module names to check. 
                        If None, checks common modules: PySide6, pandas, numpy, matplotlib, configparser
        """
        if (self.enabled == False): return
        
        self._print("=" * 60)
        self._print("MODULE VERSION INFORMATION")
        self._print("=" * 60)
        self._print(f"Python: {sys.version}")
        self._print("")
        
        # Default module list if none provided
        if module_list is None:
            module_list = ['PySide6', 'pandas', 'numpy', 'matplotlib', 'configparser']
        
        # Log each module version
        for module_name in module_list:
            try:
                # Try to get version using importlib.metadata (works for installed packages)
                ver = version(module_name)
                self._print(f"{module_name}: {ver}")
            except PackageNotFoundError:
                # Module not installed or not found
                if module_name in sys.modules:
                    # Module is loaded but version not available via metadata
                    mod = sys.modules[module_name]
                    if hasattr(mod, '__version__'):
                        self._print(f"{module_name}: {mod.__version__}")
                    else:
                        self._print(f"{module_name}: (loaded, version unknown)")
                else:
                    self._print(f"{module_name}: (not loaded)")
            except Exception as e:
                self._print(f"{module_name}: (error getting version: {e})")
        
        self._print("=" * 60)
        self._print("")
        return

    def log_all_loaded_modules(self, include_builtins=False):
        """
        Log all currently loaded modules and their versions.
        
        Args:
            include_builtins: If True, include built-in modules (can be very long)
        """
        if (self.enabled == False): return
        
        self._print("=" * 60)
        self._print("ALL LOADED MODULES")
        self._print("=" * 60)
        
        # Get all loaded modules
        loaded_modules = sorted(sys.modules.keys())
        
        for module_name in loaded_modules:
            # Skip built-in modules if requested
            if not include_builtins and module_name.startswith('_'):
                continue
                
            try:
                module = sys.modules[module_name]
                
                # Try to get version
                version_str = "unknown"
                if hasattr(module, '__version__'):
                    version_str = module.__version__
                else:
                    try:
                        # Try package name (sometimes different from module name)
                        version_str = version(module_name)
                    except:
                        pass
                
                # Get file location if available
                location = "built-in"
                if hasattr(module, '__file__') and module.__file__:
                    location = module.__file__
                
                self._print(f"{module_name}: v{version_str} ({location})")
                
            except Exception as e:
                self._print(f"{module_name}: (error: {e})")
        
        self._print("=" * 60)
        self._print("")
        return

#end class Debugging
