# Flask-RESTy [![Travis][build-badge]][build] [![Codecov][codecov-badge]][codecov] [![PyPI][pypi-badge]][pypi] [![marshmallow 3 compatible][marshmallow-badge]][marshmallow-upgrading]

Flask-RESTy provides building blocks for creating REST APIs with [Flask](http://flask.pocoo.org/), [SQLAlchemy](https://www.sqlalchemy.org/), and [marshmallow](https://marshmallow.readthedocs.io/).

```python
from flask_resty import Api, GenericModelView

from . import app, models, schemas


class WidgetViewBase(GenericModelView):
    model = models.Widget
    schema = schemas.WidgetSchema()


class WidgetListView(WidgetViewBase):
    def get(self):
        return self.list()

    def post(self):
        return self.create()


class WidgetView(WidgetViewBase):
    def get(self, id):
        return self.retrieve(id)

    def patch(self, id):
        return self.update(id, partial=True)

    def delete(self, id):
        return self.destroy(id)


api = Api(app, "/api")
api.add_resource("/widgets", WidgetListView, WidgetView)
```

## Documentation

Documentation is available at https://flask-resty.readthedocs.io/.

## Running locally

Ideally, create a virtual env for local development, using your tool of choice, e.g.:

```sh
pyenv virtualenv 3.8.3 flask-resty
pyenv local flask-resty
```

Install dependencies:

```sh
# optionally include [jwt] for the full test suite, but requires cryptography,
# and it's dependent binary libraries
pip install -e .[testing,docs]
```

### Running tests

Tests can be run for your current enviroment by running pytest directly: `pytest`.

Or run `tox` to run the fulle suite of lint checks and tests against flask-resty's supported
environments.

### Building the docs

Run sphinx to build a copy of the docs locally

```sh
sphinx-build docs/ docs/_build
```

For auto rebuilds and watching, `sphinx-autobuild` can be used:

```sh
pip install sphinx-autobuild
sphinx-autobuild --open-browser docs/ docs/_build -z flask_resty -s 2
```

## License

MIT Licensed. See the bundled [LICENSE](https://github.com/4Catalyzer/flask-resty/blob/master/LICENSE) file for more details.

[build-badge]: https://img.shields.io/travis/4Catalyzer/flask-resty/master.svg
[build]: https://travis-ci.org/4Catalyzer/flask-resty
[pypi-badge]: https://img.shields.io/pypi/v/Flask-RESTy.svg
[pypi]: https://pypi.python.org/pypi/Flask-RESTy
[codecov-badge]: https://img.shields.io/codecov/c/github/4Catalyzer/flask-resty/master.svg
[codecov]: https://codecov.io/gh/4Catalyzer/flask-resty
[marshmallow-badge]: https://badgen.net/badge/marshmallow/3
[marshmallow-upgrading]: https://marshmallow.readthedocs.io/en/latest/upgrading.html
