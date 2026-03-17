import os
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
    update config in place.  Numeric keys use suffixes:
      linewidth_float, fontsize_float, rotation_float
    String keys (linestyle, color, fontstyle, position) have no suffix.
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

    # Helper: field is blank or equals the default key name
    def _is_default(field_val, default_key_name):
        return not field_val or field_val.lower() == default_key_name.lower()

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
            parts = [p.strip() for p in value.split(',')]
            if len(parts) != 9:
                print(f"WARNING: Marker '{key}' has {len(parts)} fields "
                      f"(expected 9). Skipping.")
                continue

            # Field 0: label (required)
            marker_name = parts[0]
            if not marker_name:
                print(f"WARNING: Marker '{key}' has empty label. Skipping.")
                continue

            # Field 1: time (required)
            time_val = float(parts[1])

            # Field 2: linestyle
            ls_raw = parts[2]
            if _is_default(ls_raw, 'linestyle'):
                ls_raw = config[DEFAULTS_SECTION]['linestyle']
            linestyle = VALID_LINESTYLES.get(ls_raw.lower())
            if linestyle is None:
                print(f"WARNING: Marker '{marker_name}' invalid linestyle '{parts[2]}'. Skipping.")
                continue

            # Field 3: linewidth
            lw_raw = parts[3]
            if _is_default(lw_raw, 'linewidth_float'):
                marker_linewidth = config[DEFAULTS_SECTION]['linewidth_float']
            else:
                try:
                    marker_linewidth = float(lw_raw)
                except ValueError:
                    print(f"WARNING: Marker '{marker_name}' invalid linewidth '{lw_raw}'. Skipping.")
                    continue

            # Field 4: color
            color = parts[4]
            if _is_default(color, 'color'):
                color = config[DEFAULTS_SECTION]['color']
            if not is_color_like(color):
                print(f"WARNING: Marker '{marker_name}' invalid color '{color}'. Skipping.")
                continue

            # Field 5: fontsize
            fs_raw = parts[5]
            if _is_default(fs_raw, 'fontsize_float'):
                marker_fontsize = config[DEFAULTS_SECTION]['fontsize_float']
            else:
                try:
                    marker_fontsize = float(fs_raw)
                except ValueError:
                    print(f"WARNING: Marker '{marker_name}' invalid fontsize '{fs_raw}'. Skipping.")
                    continue

            # Field 6: fontstyle
            fst_raw = parts[6]
            if _is_default(fst_raw, 'fontstyle'):
                marker_fontstyle = config[DEFAULTS_SECTION]['fontstyle']
            else:
                marker_fontstyle = fst_raw.title()
                if _parse_fontstyle(marker_fontstyle) is None:
                    print(f"WARNING: Marker '{marker_name}' invalid fontstyle '{fst_raw}'. Skipping.")
                    continue

            # Field 7: position
            pos_raw = parts[7]
            if _is_default(pos_raw, 'position'):
                pos_raw = config[DEFAULTS_SECTION]['position']
            marker_position = _parse_marker_position(pos_raw)
            if marker_position is None:
                print(f"WARNING: Marker '{marker_name}' invalid position '{parts[7]}'. Skipping.")
                continue

            # Field 8: rotation
            rot_raw = parts[8]
            if _is_default(rot_raw, 'rotation_float'):
                marker_rotation = config[DEFAULTS_SECTION]['rotation_float']
            else:
                try:
                    marker_rotation = float(rot_raw)
                except ValueError:
                    print(f"WARNING: Marker '{marker_name}' invalid rotation '{rot_raw}'. Skipping.")
                    continue

            fontweight, fontstyle = _parse_fontstyle(marker_fontstyle)

            # Replace any existing marker with the same key (e.g. pttp overrides pttplot.ini)
            markers = [m for m in markers if m.get('key') != key]
            markers.append({
                'key':        key,
                'name':       marker_name,
                'time':       time_val,
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
