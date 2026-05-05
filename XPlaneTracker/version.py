import os

SCHEMA_VERSION = "2.0.0"

_ver_file = os.path.join(os.path.dirname(__file__), "version.txt")
if os.path.exists(_ver_file):
    with open(_ver_file) as _f:
        _v = _f.read().strip()
    APP_VERSION = _v if _v else "dev"
else:
    APP_VERSION = os.environ.get("APP_VERSION", "dev")
