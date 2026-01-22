import os
import time

# Asset Versions
# Use timestamp in development to prevent caching issues
is_dev = os.getenv("NEBULUS_ENV", "development") == "development"
timestamp = str(int(time.time()))

UI_CSS_VERSION = timestamp if is_dev else "47"
UI_JS_VERSION = timestamp if is_dev else "46"
WORKSPACE_VERSION = timestamp if is_dev else "34"
NOTES_VERSION = timestamp if is_dev else "36"
