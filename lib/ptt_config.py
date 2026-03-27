import os
import re
import configparser
import shutil
from datetime import datetime
from platformdirs import user_config_dir
from ptt_appinfo import APP_PACKAGE, APP_COMPANY, APP_VERSION

try:
    from configupdater import ConfigUpdater
    _HAS_CONFIGUPDATER = True
except ImportError:
    _HAS_CONFIGUPDATER = False


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_parser():
    """
    Return a RawConfigParser configured for PTTimeline INI files:
    - Semicolon-only comments so # in hex colors (#1f77b4) is preserved.
    - Keys lowercased (default optionxform) so suffix matching is case-safe.
    """
    return configparser.RawConfigParser(
        comment_prefixes=(';',),
        inline_comment_prefixes=()
    )


def _convert_value(key, raw):
    """
    Convert a raw INI string value to a Python type based on key suffix.
      key ending _bool  -> bool   (uses configparser boolean rules)
      key ending _int   -> int    (or None if raw is 'none')
      key ending _float -> float  (or None if raw is 'none')
      anything else     -> str    (stripped)
    """
    k = key.lower()
    raw = raw.strip() if raw else ''
    if k.endswith('_bool'):
        return raw.lower() in ('1', 'yes', 'true', 'on')
    elif k.endswith('_int'):
        return None if raw.lower() == 'none' else int(raw)
    elif k.endswith('_float'):
        return None if raw.lower() == 'none' else float(raw)
    else:
        return raw


def _parse_defaults(defaults_str):
    """
    Parse the DEFAULT_CONFIG INI string into a configparser object.
    Returns a RawConfigParser loaded from the string.
    """
    cfg = _make_parser()
    cfg.read_string(defaults_str)
    return cfg


def _update_meta(updater, app_name, defaults_cfg):
    """
    Overwrite all [META] section values with current values from defaults_cfg,
    then apply any runtime overrides (app_name, app_version).
    This ensures every META key — including ini_version — stays current.
    """
    if not updater.has_section('META') or not defaults_cfg.has_section('META'):
        return
    meta = updater['META']
    for key, value in defaults_cfg.items('META'):
        if key in meta:
            meta[key].value = value
    # Apply runtime values that differ from the placeholder defaults
    if 'app_name' in meta:
        meta['app_name'].value = app_name
    if 'app_version' in meta:
        meta['app_version'].value = APP_VERSION
    if 'app_package' in meta:
        meta['app_package'].value = APP_PACKAGE


def _write_ini_from_defaults(path, defaults_str):
    """
    Write a new user INI file directly from the defaults string.
    Preserves all comments and formatting from the defaults string.
    """
    with open(path, 'w', encoding='utf-8') as f:
        f.write(defaults_str)


def _provision_user_ini(app_ini_filename, defaults_str, app_name):
    """
    Ensure user config dir and INI file exist, then merge any new keys from
    defaults and keep META current.  Backs up before any write.

    - First run: writes the defaults string verbatim (comments and all).
    - Subsequent runs: uses ConfigUpdater to merge missing sections/keys while
      preserving all existing comments, blank lines, and user edits.
    - META section is always refreshed to current program values.
    - Returns the path to the (possibly updated) user INI file.
    """
    cfg_dir = user_config_dir(APP_PACKAGE, APP_COMPANY, roaming=True)
    os.makedirs(cfg_dir, exist_ok=True)
    user_ini_path = os.path.join(cfg_dir, app_ini_filename)

    # Parse defaults for merge comparison
    defaults_cfg = _parse_defaults(defaults_str)

    if not os.path.isfile(user_ini_path):
        # First run - write defaults verbatim (preserves all comments)
        _write_ini_from_defaults(user_ini_path, defaults_str)
        # Update META with real program values
        if _HAS_CONFIGUPDATER:
            updater = ConfigUpdater(comment_prefixes=';', allow_no_value=True)
            updater.read(user_ini_path, encoding='utf-8')
            _update_meta(updater, app_name, defaults_cfg)
            with open(user_ini_path, 'w', encoding='utf-8') as f:
                f.write(str(updater))
        return user_ini_path

    # Existing file - check for missing sections/keys and stale META
    changed = False

    if _HAS_CONFIGUPDATER:
        updater = ConfigUpdater(comment_prefixes=';', allow_no_value=True)
        updater.read(user_ini_path, encoding='utf-8')

        # Merge missing sections and keys from defaults
        for section in defaults_cfg.sections():
            if not updater.has_section(section):
                updater.add_section(section)
                changed = True
            for key, value in defaults_cfg.items(section):
                if not updater.has_option(section, key):
                    updater[section][key] = value
                    changed = True

        # Always refresh META - snapshot all META keys for change detection
        def _meta_snapshot():
            if not updater.has_section('META'):
                return {}
            return {k: updater['META'][k].value
                    for k in updater['META'] if updater['META'].has_option(k)}
        old_meta = _meta_snapshot()
        _update_meta(updater, app_name, defaults_cfg)
        new_meta = _meta_snapshot()
        if old_meta != new_meta:
            changed = True

        if changed:
            _backup_ini(user_ini_path, app_ini_filename, cfg_dir)
            with open(user_ini_path, 'w', encoding='utf-8') as f:
                f.write(str(updater))
    else:
        # Fallback: plain configparser (no comment preservation)
        user_cfg = _make_parser()
        user_cfg.read(user_ini_path, encoding='utf-8')

        for section in defaults_cfg.sections():
            if not user_cfg.has_section(section):
                user_cfg.add_section(section)
                changed = True
            for key, value in defaults_cfg.items(section):
                if not user_cfg.has_option(section, key):
                    user_cfg.set(section, key, value)
                    changed = True

        # Refresh META - all keys from defaults, plus runtime overrides
        if user_cfg.has_section('META') and defaults_cfg.has_section('META'):
            for key, value in defaults_cfg.items('META'):
                current = user_cfg.get('META', key, fallback=None)
                if current != value:
                    user_cfg.set('META', key, value)
                    changed = True
            # Runtime overrides
            for key, val in [('app_package', APP_PACKAGE),
                              ('app_name',    app_name),
                              ('app_version', APP_VERSION)]:
                if user_cfg.get('META', key, fallback=None) != val:
                    user_cfg.set('META', key, val)
                    changed = True

        if changed:
            _backup_ini(user_ini_path, app_ini_filename, cfg_dir)
            with open(user_ini_path, 'w', encoding='utf-8') as f:
                user_cfg.write(f)

    return user_ini_path


def _backup_ini(user_ini_path, app_ini_filename, cfg_dir):
    """Create a timestamped backup of the user INI before overwriting."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base = os.path.splitext(app_ini_filename)[0]
    backup_path = os.path.join(cfg_dir, f'{base}.{timestamp}.bak')
    shutil.copy2(user_ini_path, backup_path)


def _load_user_ini(user_ini_path):
    """Load and return a RawConfigParser from the user INI path."""
    cfg = _make_parser()
    cfg.read(user_ini_path, encoding='utf-8')
    return cfg


# ─────────────────────────────────────────────────────────────────────────────
# PTTEdit config loader
# ─────────────────────────────────────────────────────────────────────────────

def load_edit_config(app_ini_filename, defaults_str, app_name):
    """
    Provision user config dir and INI file for PTTEdit, then return a
    populated config dict with suffix-based type conversion:
      _bool  -> bool
      _int   -> int  (or None)
      _float -> float (or None)
      other  -> str
    """
    user_ini_path = _provision_user_ini(app_ini_filename, defaults_str, app_name)
    defaults_cfg  = _parse_defaults(defaults_str)
    user_cfg      = _load_user_ini(user_ini_path)

    result = {}
    for section in defaults_cfg.sections():
        result[section] = {}
        for key, default_raw in defaults_cfg.items(section):
            raw = user_cfg.get(section, key, fallback=default_raw)
            result[section][key] = _convert_value(key, raw)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PTTPlot config loader and supporting functions
# ─────────────────────────────────────────────────────────────────────────────

def _parse_fontstyle(fontstyle_str):
    """
    Parse a fontstyle string into (fontweight, fontstyle) for matplotlib.
    Returns the tuple, or None if invalid.
    """
    FONTSTYLE_MAP = {
        'normal':      ('normal', 'normal'),
        'bold':        ('bold',   'normal'),
        'italic':      ('normal', 'italic'),
        'bold italic': ('bold',   'italic'),
    }
    return FONTSTYLE_MAP.get(fontstyle_str.lower().strip(), None)


def _parse_marker_position(position_str):
    """
    Parse a marker label position string into a float in [0.0, 1.0].
    Accepts: 'Top', 'Bottom', 'Center', or '<number>%'.
    Returns None if invalid.
    """
    val = position_str.strip().lower()
    if val == 'top':
        return 1.0
    elif val == 'bottom':
        return 0.0
    elif val == 'center':
        return 0.5
    elif val.endswith('%'):
        try:
            pct = float(val[:-1])
            return pct / 100.0 if 0.0 <= pct <= 100.0 else None
        except ValueError:
            return None
    return None


def _load_markers_from_ini(ini_cfg, config):
    """
    Parse marker definitions from [ANNOTATIONS.MARKERS] in ini_cfg and
    update config in place.

    Marker format: semicolon-separated named parameters.
    Only label= and time= are required; all other parameters are
    optional and inherit from [ANNOTATIONS.MARKER_DEFAULTS] if omitted.

      markerN = label=Text; time=0.0; linestyle=dashed; linewidth_float=1;
                color=red; fontsize_float=7; fontstyle=Normal; position=Top; rotation_float=0

    time= accepts either a numeric float or a task reference formula:
      time=Start(ProcessName:TaskName)
      time=End(ProcessName:TaskName)
    Supported function names (must match exactly, same as PTTEdit):
                               Start, End.
    Formula references are resolved at plot time against task_plot_positions.
    If the referenced task is not found in the plot data, the marker is skipped
    with a debug warning.

    An empty value (markerN =) removes any existing marker with that key.
    Unknown parameter names emit a warning and are ignored.
    Returns updated config.
    """
    from matplotlib.colors import is_color_like

    SECTION          = 'ANNOTATIONS.MARKERS'
    DEFAULTS_SECTION = 'ANNOTATIONS.MARKER_DEFAULTS'

    VALID_LINESTYLES = {
        'solid':   'solid',  '-':   'solid',
        'dashed':  'dashed', '--':  'dashed',
        'dashdot': 'dashdot','-.':  'dashdot',
        'dotted':  'dotted', ':':   'dotted',
        'none':    'None',
    }

    VALID_PARAM_NAMES = {
        'label', 'time', 'linestyle', 'linewidth_float',
        'color', 'fontsize_float', 'fontstyle', 'position', 'rotation_float'
    }

    # Regex for task reference formulas — explicit variants match PTTEdit's registered functions exactly.
    _TIME_REF_RE = re.compile(
        r'^(Start|End)\s*\(\s*(.*?)\s*:\s*(.+?)\s*\)$'
    )

    def _get(key, fallback):
        return ini_cfg.get(DEFAULTS_SECTION, key, fallback=fallback) if ini_cfg.has_section(DEFAULTS_SECTION) else fallback

    def _getfloat(key, fallback):
        try:
            return ini_cfg.getfloat(DEFAULTS_SECTION, key, fallback=fallback) if ini_cfg.has_section(DEFAULTS_SECTION) else fallback
        except (ValueError, TypeError):
            return fallback

    # Update defaults from [ANNOTATIONS.MARKER_DEFAULTS] in INI
    config[DEFAULTS_SECTION]['linestyle']       = _get('linestyle',       config[DEFAULTS_SECTION]['linestyle'])
    config[DEFAULTS_SECTION]['linewidth_float'] = _getfloat('linewidth_float', config[DEFAULTS_SECTION]['linewidth_float'])
    config[DEFAULTS_SECTION]['color']           = _get('color',           config[DEFAULTS_SECTION]['color'])
    config[DEFAULTS_SECTION]['fontsize_float']  = _getfloat('fontsize_float',  config[DEFAULTS_SECTION]['fontsize_float'])
    config[DEFAULTS_SECTION]['position']        = _get('position',        config[DEFAULTS_SECTION]['position'])
    config[DEFAULTS_SECTION]['rotation_float']  = _getfloat('rotation_float',  config[DEFAULTS_SECTION]['rotation_float'])

    fontstyle_str = _get('fontstyle', config[DEFAULTS_SECTION]['fontstyle']).strip().title()
    if _parse_fontstyle(fontstyle_str) is None:
        print(f"WARNING: Invalid fontstyle '{fontstyle_str}', using Normal")
        fontstyle_str = 'Normal'
    config[DEFAULTS_SECTION]['fontstyle'] = fontstyle_str

    # Start with existing markers so per-file INI can merge over pttplot.ini markers
    markers = list(config[SECTION].get('_markers', []))

    if not ini_cfg.has_section(SECTION):
        config[SECTION]['_markers'] = markers
        return config

    for key in ini_cfg.options(SECTION):
        # marker<N> keys: 'marker' followed immediately by a digit
        if not (key.startswith('marker') and len(key) > 6 and key[6].isdigit()):
            continue

        value = ini_cfg.get(SECTION, key)
        if not value.strip():
            # Empty value removes any existing marker with this key
            markers = [m for m in markers if m.get('key') != key]
            continue

        try:
            # Parse semicolon-separated named parameters
            params = {}
            for token in value.split(';'):
                token = token.strip()
                if not token:
                    continue
                if '=' not in token:
                    print(f"WARNING: Marker '{key}' has token without '=': '{token}'. Ignoring.")
                    continue
                param_name, _, param_val = token.partition('=')
                param_name = param_name.strip().lower()
                param_val  = param_val.strip()
                if param_name not in VALID_PARAM_NAMES:
                    print(f"WARNING: Marker '{key}' has unknown parameter '{param_name}'. Ignoring.")
                    continue
                params[param_name] = param_val

            # label= and time= are required
            marker_name = params.get('label', '').strip()
            if not marker_name:
                print(f"WARNING: Marker '{key}' missing required label=. Skipping.")
                continue

            time_raw = params.get('time', '')
            if not time_raw:
                print(f"WARNING: Marker '{key}' missing required time=. Skipping.")
                continue

            # time= accepts a literal float or a task reference formula
            time_val = None
            time_ref = None
            try:
                time_val = float(time_raw)
            except ValueError:
                m = _TIME_REF_RE.match(time_raw)
                if m:
                    func_name  = m.group(1).lower()   # normalise: start/starttime/end/endtime
                    ref_proc   = m.group(2).strip()
                    ref_task   = m.group(3).strip()
                    ref_edge   = 'start' if func_name.startswith('start') else 'end'
                    time_ref   = (ref_edge, ref_proc, ref_task)
                else:
                    print(f"WARNING: Marker '{key}' invalid time='{time_raw}'. "
                          f"Expected a float or Start/End(Process:Task). Skipping.")
                    continue

            # linestyle — default if absent
            ls_raw = params.get('linestyle', config[DEFAULTS_SECTION]['linestyle'])
            linestyle = VALID_LINESTYLES.get(ls_raw.lower())
            if linestyle is None:
                print(f"WARNING: Marker '{marker_name}' invalid linestyle='{ls_raw}'. Skipping.")
                continue

            # linewidth_float — default if absent
            lw_raw = params.get('linewidth_float', '')
            if not lw_raw:
                marker_linewidth = config[DEFAULTS_SECTION]['linewidth_float']
            else:
                try:
                    marker_linewidth = float(lw_raw)
                except ValueError:
                    print(f"WARNING: Marker '{marker_name}' invalid linewidth_float='{lw_raw}'. Skipping.")
                    continue

            # color — default if absent
            color = params.get('color', config[DEFAULTS_SECTION]['color'])
            if not is_color_like(color):
                print(f"WARNING: Marker '{marker_name}' invalid color='{color}'. Skipping.")
                continue

            # fontsize_float — default if absent
            fs_raw = params.get('fontsize_float', '')
            if not fs_raw:
                marker_fontsize = config[DEFAULTS_SECTION]['fontsize_float']
            else:
                try:
                    marker_fontsize = float(fs_raw)
                except ValueError:
                    print(f"WARNING: Marker '{marker_name}' invalid fontsize_float='{fs_raw}'. Skipping.")
                    continue

            # fontstyle — default if absent
            fst_raw = params.get('fontstyle', '')
            if not fst_raw:
                marker_fontstyle = config[DEFAULTS_SECTION]['fontstyle']
            else:
                marker_fontstyle = fst_raw.strip().title()
                if _parse_fontstyle(marker_fontstyle) is None:
                    print(f"WARNING: Marker '{marker_name}' invalid fontstyle='{fst_raw}'. Skipping.")
                    continue

            # position — default if absent
            pos_raw = params.get('position', config[DEFAULTS_SECTION]['position'])
            marker_position = _parse_marker_position(pos_raw)
            if marker_position is None:
                print(f"WARNING: Marker '{marker_name}' invalid position='{pos_raw}'. Skipping.")
                continue

            # rotation_float — default if absent
            rot_raw = params.get('rotation_float', '')
            if not rot_raw:
                marker_rotation = config[DEFAULTS_SECTION]['rotation_float']
            else:
                try:
                    marker_rotation = float(rot_raw)
                except ValueError:
                    print(f"WARNING: Marker '{marker_name}' invalid rotation_float='{rot_raw}'. Skipping.")
                    continue

            fontweight, fontstyle = _parse_fontstyle(marker_fontstyle)

            # Replace any existing marker with the same key (e.g. pttp overrides pttplot.ini)
            markers = [m for m in markers if m.get('key') != key]
            markers.append({
                'key':        key,
                'name':       marker_name,
                'time':       time_val,
                'time_ref':   time_ref,
                'linestyle':  linestyle,
                'linewidth':  marker_linewidth,
                'color':      color,
                'fontsize':   marker_fontsize,
                'fontweight': fontweight,
                'fontstyle':  fontstyle,
                'position':   marker_position,
                'rotation':   marker_rotation,
            })

        except Exception as e:
            print(f"ERROR parsing marker '{key}': {e}")

    config[SECTION]['_markers'] = markers
    return config


def _apply_ini_config(ini_cfg, config):
    """
    Apply settings from a RawConfigParser ini_cfg onto the runtime config dict.
    Uses suffix-based type conversion via _convert_value().
    Only keys already present in config are updated (no new keys added).
    Returns updated config.
    """
    import json5 as json

    SKIP_SECTIONS = {'META', 'ANNOTATIONS.MARKER_DEFAULTS', 'ANNOTATIONS.MARKERS'}

    for section in config:
        if section in SKIP_SECTIONS:
            continue
        if not ini_cfg.has_section(section):
            continue
        for key in config[section]:
            if key.startswith('_'):          # runtime-only keys like _markers
                continue
            if not ini_cfg.has_option(section, key):
                continue
            raw = ini_cfg.get(section, key)

            # exclude_hbar_groups is a JSON list stored as a string
            if key == 'exclude_hbar_groups':
                raw = raw.strip()
                try:
                    config[section][key] = json.loads(raw) if raw else []
                except Exception:
                    config[section][key] = []
                continue

            # PRESENTATION validated-choice keys
            if section == 'PRESENTATION':
                CHOICES = {
                    'hbar_stacking':            ['Unstacked', 'Stacked'],
                    'hbar_label_justified':     ['Center', 'Left'],
                    'hbar_label_rotation':      ['Horizontal', 'Slanted', 'Vertical'],
                    'dependency_arrow_mode':    ['Time', 'Task'],
                }
                if key in CHOICES:
                    val = raw.strip().title()
                    config[section][key] = val if val in CHOICES[key] else CHOICES[key][0]
                    continue

            config[section][key] = _convert_value(key, raw)

    # ANNOTATIONS.MARKERS handled separately
    _load_markers_from_ini(ini_cfg, config)

    return config


def _build_runtime_config(defaults_str):
    """
    Build a runtime config dict from the defaults INI string using
    suffix-based type conversion.  Adds the _markers list to
    ANNOTATIONS.MARKERS for runtime use.
    """
    defaults_cfg = _parse_defaults(defaults_str)
    config = {}
    for section in defaults_cfg.sections():
        config[section] = {}
        for key, raw in defaults_cfg.items(section):
            config[section][key] = _convert_value(key, raw)
    # Add runtime-only marker list
    if 'ANNOTATIONS.MARKERS' in config:
        config['ANNOTATIONS.MARKERS']['_markers'] = []
    return config


def load_plot_config(app_ini_filename, defaults_str, app_name):
    """
    Provision user config dir and INI file for PTTPlot, then return a fully
    populated runtime config dict.

    - _provision_user_ini() handles first-run write, key merging, META refresh,
      and backup — all via ConfigUpdater to preserve comments.
    - Runtime config is built from defaults_str via suffix-based type conversion.
    - User INI overrides are applied on top via _apply_ini_config().
    - Returns the populated config dict.
    """
    user_ini_path = _provision_user_ini(app_ini_filename, defaults_str, app_name)
    config        = _build_runtime_config(defaults_str)
    user_ini_cfg  = _load_user_ini(user_ini_path)
    _apply_ini_config(user_ini_cfg, config)
    return config
