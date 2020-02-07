from werkzeug.routing import Rule

try:
    from werkzeug.routing import RequestPath
except ImportError:  # pragma: no cover
    # werkzeug<1.0
    from werkzeug.routing import RequestSlash as RequestPath

# -----------------------------------------------------------------------------


class StrictRule(Rule):
    """A Werkzeug rule that does not append missing slashes to paths."""

    def match(self, path, method=None):
        try:
            result = super().match(path, method)
        except RequestPath:
            return None

        return result
