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
