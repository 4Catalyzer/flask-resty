# Flask-RESTy [![Travis][build-badge]][build] [![PyPI][pypi-badge]][pypi]
Building blocks for REST APIs for [Flask](http://flask.pocoo.org/).

[![Codecov][codecov-badge]][codecov]

## Usage

Create a [SQLAlchemy](http://www.sqlalchemy.org/) model and a [marshmallow](http://marshmallow.rtfd.org/) schema, then: 

```python
from flask_resty import Api, GenericModelView

from .models import Widget
from .schemas import WidgetSchema


class WidgetViewBase(GenericModelView):
    model = Widget
    schema = WidgetSchema()


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


api = Api(app, '/api')
api.add_resource('/widgets', WidgetListView, WidgetView)
```
The recommended way of creating models is to use `flask_sqlalchemy` to create a base `Model` class:
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

class Widget(db.Model):
   ...
```

[build-badge]: https://img.shields.io/travis/4Catalyzer/flask-resty/master.svg
[build]: https://travis-ci.org/4Catalyzer/flask-resty

[pypi-badge]: https://img.shields.io/pypi/v/Flask-RESTy.svg
[pypi]: https://pypi.python.org/pypi/Flask-RESTy

[codecov-badge]: https://img.shields.io/codecov/c/github/4Catalyzer/flask-resty/master.svg
[codecov]: https://codecov.io/gh/4Catalyzer/flask-resty
