import importlib.metadata

import packaging.version

# Field.missing is deprecated in favor of Field.load_default in marshmallow 3.13.0
_MARSHMALLOW_VERSION = importlib.metadata.version("marshmallow")
USE_LOAD_DEFAULT = packaging.version.parse(
    _MARSHMALLOW_VERSION
) > packaging.version.parse("3.13")

LOAD_DEFAULT_KWARG = "load_default" if USE_LOAD_DEFAULT else "missing"
