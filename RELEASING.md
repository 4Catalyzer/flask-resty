# Releasing

_Replace x.y.z below with the new version._

1. Bump the `__version__` in `flask_resty/__init__.py`.
2. Commit: `git commit -m "vx.y.z"`
3. Tag the commit: `git tag vx.y.z`
4. Push the tag: `git push --tags origin master`

GitHub Actions will take care of releasing to PyPI.
