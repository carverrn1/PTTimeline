# ptt_utils.py — Shared utility functions for PTTimeline applications

import re


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
