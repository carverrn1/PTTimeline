"""
Application information for PTTimeline applications.

This file is shared by PTTEdit, PTTPlot and PTTView to maintain
consistent version and metadata across the application suite.
"""

# Version tuple - SINGLE SOURCE OF TRUTH
# Update only this tuple when releasing new versions
# 
# Formats:
#   (major, minor, patch)                 -> "major.minor.patch"
#   (major, minor, patch, "suffix")       -> "major.minor.patch-suffix"
#   (major, minor, patch, "suffix", num)  -> "major.minor.patch-suffix.num"
#


APP_VERSION_INFO = (0, 3, 2, "dev", 8)


# APP_VERSION_INFO = (1, 0, 0)              # Stable release
# APP_VERSION_INFO = (0, 9, 0)              # Pre-1.0 (testing)
# APP_VERSION_INFO = (1, 0, 0, "beta")      # Beta release
# APP_VERSION_INFO = (1, 0, 0, "beta", 1)   # Beta 1
# APP_VERSION_INFO = (1, 0, 0, "rc", 1)     # Release Candidate 1
# APP_VERSION_INFO = (1, 0, 0, "dev")       # Development build

# Build version string from tuple
if len(APP_VERSION_INFO) == 3:
    # Standard release: (1, 0, 0) -> "1.0.0"
    APP_VERSION = ".".join(map(str, APP_VERSION_INFO))
elif len(APP_VERSION_INFO) == 4:
    # With suffix: (1, 0, 0, "beta") -> "1.0.0-beta"
    APP_VERSION = ".".join(map(str, APP_VERSION_INFO[:3])) + "-" + str(APP_VERSION_INFO[3])
elif len(APP_VERSION_INFO) >= 5:
    # With suffix and number: (1, 0, 0, "beta", 1) -> "1.0.0-beta.1"
    APP_VERSION = ".".join(map(str, APP_VERSION_INFO[:3])) + "-" + str(APP_VERSION_INFO[3]) + "." + str(APP_VERSION_INFO[4])
else:
    APP_VERSION = "0.0.0"  # Fallback

# Metadata
APP_PACKAGE     = "PTTimeline"
APP_DESCRIPTION = "Process-Task Timeline Editor (PTTEdit),<br>Process-Task Timeline Plotter (PTTPlot) and Process-Task Timeline Viewer (PTTView)"
APP_AUTHOR      = "Richard Carver"
APP_COMPANY     = "RNCSoftware"
APP_DATE        = "2026-03-26"
APP_COPYRIGHT   = f"© 2026 by {APP_AUTHOR}"

APP_ID = "com.RNCSoftware.PTTimeline".lower()   # DON'T CHANGE! Used to locate user specific application data (e.g. %APP_DATA%)

# Semantic versioning: MAJOR.MINOR.PATCH[-PRERELEASE]
# MAJOR: Breaking changes
# MINOR: New features, backward compatible
# PATCH: Bug fixes, backward compatible
# PRERELEASE: alpha, beta, rc (release candidate), dev
#
# Examples:
#   (1, 0, 0)              -> "1.0.0"
#   (0, 9, 0)              -> "0.9.0"          (pre-1.0 testing)
#   (1, 0, 0, "beta")      -> "1.0.0-beta"
#   (1, 0, 0, "beta", 1)   -> "1.0.0-beta.1"
#   (1, 0, 0, "rc", 2)     -> "1.0.0-rc.2"
#   (1, 0, 0, "dev")       -> "1.0.0-dev"
