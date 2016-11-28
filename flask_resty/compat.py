import sys

# -----------------------------------------------------------------------------

PY2 = int(sys.version_info[0]) == 2

# -----------------------------------------------------------------------------

if PY2:
    basestring = basestring  # noqa
else:
    basestring = (str, bytes)
