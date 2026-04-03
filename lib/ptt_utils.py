# ptt_utils.py — Shared utility functions for PTTimeline applications

import os
import re
import shutil
import platform
import urllib.request
import urllib.parse


def backup_file_on_save(filepath: str, backup_folder: str, max_backups: int) -> None:
    """Create a timestamped backup of *filepath* before it is overwritten.

    Backup filenames use the format::

        <original_filename>.<YYYYMMDD-HHMMSS>.bak

    For example::

        project.pttd.20260402-102700.bak

    Backups are written to *backup_folder*.  If *backup_folder* is a relative
    path it is resolved relative to the directory containing *filepath*.  If
    the folder does not exist it is created automatically.  If *backup_folder*
    is blank, backups are placed in the same directory as *filepath*.

    If the file does not yet exist no backup is made (first-time save).

    If *max_backups* is >= 1 and the number of existing backups for this file
    reaches or exceeds the limit, the oldest backup(s) are deleted before the
    new one is written.  Oldest is determined by the timestamp embedded in the
    backup filename, so the sort is reliable regardless of OS file timestamps.
    If *max_backups* is 0 or negative there is no limit.

    Parameters
    ----------
    filepath:
        Absolute or relative path to the file about to be written.
    backup_folder:
        Subfolder name (or path) for backup files.  Surrounding quotes are
        stripped so both ``ptt_backups`` and ``"ptt backups"`` work correctly.
        Pass an empty string to place backups alongside the source file.
    max_backups:
        Maximum number of backup copies to keep.  0 or negative means unlimited.
    """
    from datetime import datetime

    if not os.path.isfile(filepath):
        return  # nothing to back up on a first-time save

    src_dir  = os.path.dirname(os.path.abspath(filepath))
    src_name = os.path.basename(filepath)

    # Strip surrounding quotes from backup_folder (INI courtesy)
    folder = backup_folder.strip().strip('"').strip("'")

    if folder:
        dst_dir = folder if os.path.isabs(folder) else os.path.join(src_dir, folder)
        os.makedirs(dst_dir, exist_ok=True)
    else:
        dst_dir = src_dir

    # Build the timestamped backup filename
    timestamp   = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_name = f'{src_name}.{timestamp}.bak'
    backup_path = os.path.join(dst_dir, backup_name)

    # Enforce max_backups limit: collect existing backups for this source file,
    # sorted by the embedded timestamp (oldest first), and delete the excess.
    if max_backups >= 1:
        import glob
        pattern  = os.path.join(dst_dir, f'{src_name}.????????-??????.bak')
        existing = sorted(glob.glob(pattern))   # lexicographic == chronological
        excess   = len(existing) - (max_backups - 1)
        for old in existing[:excess]:
            try:
                os.remove(old)
            except OSError:
                pass  # best-effort; failure here is non-critical

    shutil.copy2(filepath, backup_path)


def get_os_info() -> str:
    """Return a human-readable OS string with Windows 11 detection.

    Python reports Windows 11 as 'Windows 10' until the build number is
    checked.  This helper inspects the build number and returns the correct
    display string on all supported platforms.
    """
    platform_str = platform.platform()
    os_name      = platform.system()
    os_release   = platform.release()

    if os_name == "Windows" and os_release == "10":
        build_match = re.search(r'10\.0\.(\d+)', platform_str)
        if build_match:
            build_num = int(build_match.group(1))
            if build_num >= 22000:
                return f"Windows 11 (Build {build_num})"
            else:
                return f"Windows 10 (Build {build_num})"
    return f"{os_name} {os_release}"


def html_to_plain_text(html: str) -> str:
    """Convert an HTML string to readable plain text.

    Replaces block-level tags with newlines, decodes common HTML entities,
    strips all remaining tags, and collapses runs of blank lines so the
    result is suitable for pasting into a bug report or email.
    """
    # Replace table cell boundaries with a tab for column separation
    html = re.sub(r'</td>\s*<td[^>]*>', '\t', html, flags=re.IGNORECASE)

    # Replace block-level / line-break tags with newlines before stripping
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?(p|div|h[1-6]|tr|li)[^>]*>', '\n', html, flags=re.IGNORECASE)

    # Strip all remaining tags
    html = re.sub(r'<[^>]+>', '', html)

    # Decode common HTML entities
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&mdash;', '\u2014')
    html = html.replace('&ndash;', '\u2013')
    html = html.replace('&#39;', "'")
    html = html.replace('&quot;', '"')

    # Strip leading/trailing whitespace from each line
    html = '\n'.join(line.strip() for line in html.splitlines())

    # Collapse runs of more than one consecutive newline to one
    html = re.sub(r'\n{2,}', '\n', html)

    return html.strip()


def build_issue_url(repo_url: str, template_name: str,
                    context: dict[str, str] | None = None) -> str:
    """Fetch a GitHub issue template and return a pre-filled new-issue URL.

    Fetches the raw template from the repository's main branch, strips the
    YAML frontmatter, then injects live values into any recognised bold-heading
    fields before building the URL.

    Injection works by finding a ``**Heading:**`` line and replacing the
    content on the line immediately after it with the supplied value.  For
    headings whose placeholder text is on the *same* line (e.g.
    ``**Application:** PTTEdit / PTTPlot / PTTView``), the text after the
    colon-space is replaced instead.

    Parameters
    ----------
    repo_url : str
        Base repository URL, e.g. ``"https://github.com/owner/repo"``.
    template_name : str
        Filename of the issue template, e.g. ``"bug_report.md"``.
    context : dict[str, str] or None
        Mapping of bold-heading text (without ``**`` markers or trailing
        colon) to the replacement value, e.g.::

            {
                "Application":       "PTTEdit",
                "Version":           "v0.5.0-dev",
                "Operating System":  "Windows 11 (Build 26100)",
                "System Information": "<multiline plain-text block>",
                "Which application(s)?": "PTTEdit",
            }

        Pass ``None`` (or omit) when no injection is needed.

    Returns
    -------
    str
        The fully-constructed URL ready for ``webbrowser.open_new_tab()``.

    Raises
    ------
    Exception
        Re-raises any network or HTTP error so the caller can display a
        user-facing warning dialog.
    """
    raw_url = (
        repo_url.replace("https://github.com/", "https://raw.githubusercontent.com/")
        + f"/main/.github/ISSUE_TEMPLATE/{template_name}"
    )

    with urllib.request.urlopen(raw_url, timeout=10) as response:
        raw = response.read().decode("utf-8")

    # Strip YAML frontmatter (--- ... --- block at the top)
    body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', raw, count=1, flags=re.DOTALL).strip()

    if context:
        for heading, value in context.items():
            # Escape backslashes in the replacement value once, for re.sub
            safe_value = value.replace('\\', '\\\\')

            # Build a regex that matches the bold heading (with optional trailing ?)
            heading_pat = re.escape(f"**{heading}:**") if not heading.endswith('?') \
                          else re.escape(f"**{heading}**")

            # Case 1: placeholder is on the NEXT line
            #   **Heading:**
            #   placeholder text
            next_line_pat = rf'({heading_pat}\s*\n)([^\n]*)'
            if re.search(next_line_pat, body):
                body = re.sub(next_line_pat, rf'\g<1>{safe_value}', body)
                continue

            # Case 2: placeholder is on the SAME line after the colon-space
            #   **Heading:** placeholder text
            same_line_pat = rf'({heading_pat} ?)([^\n]+)'
            if re.search(same_line_pat, body):
                body = re.sub(same_line_pat, rf'\g<1>{safe_value}', body)

    new_issue_url = (
        f"{repo_url}/issues/new"
        f"?template={urllib.parse.quote(template_name)}"
        f"&body={urllib.parse.quote(body)}"
    )
    return new_issue_url
