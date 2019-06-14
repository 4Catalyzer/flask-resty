from werkzeug.routing import RequestSlash, Rule

# -----------------------------------------------------------------------------


class StrictRule(Rule):
    """A Werkzeug rule that does not append missing slashes to paths."""

    def match(self, path, method=None):
        try:
            result = super().match(path, method)
        except RequestSlash:
            return None

        return result
