import marshmallow

# Field.missing is deprecated in favor of Field.load_default in marshmallow 3.13.0
try:
    USE_LOAD_DEFAULT = marshmallow.__version_info__ >= (3, 13)
except AttributeError:
    USE_LOAD_DEFAULT = False

LOAD_DEFAULT_KWARG = "load_default" if USE_LOAD_DEFAULT else "missing"
