import marshmallow

# Field.missing is deprecated in favor of Field.load_default in marshmallow 3.13.0
USE_LOAD_DEFAULT = marshmallow.__version_info__ >= (3, 13)

LOAD_DEFAULT_KWARG = "load_default" if USE_LOAD_DEFAULT else "missing"
