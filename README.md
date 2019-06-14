# Flask-RESTy [![Travis][build-badge]][build] [![PyPI][pypi-badge]][pypi] [![marshmallow 2/3 compatible][marshmallow-badge]][marshmallow-upgrading]
Building blocks for REST APIs for [Flask](http://flask.pocoo.org/).

[![Codecov][codecov-badge]][codecov]

## Usage

Create a [SQLAlchemy](http://www.sqlalchemy.org/) model and a [marshmallow](http://marshmallow.rtfd.org/) schema, then:

```python
from flask_resty import Api, GenericModelView

from . import app, models, schemas


class WidgetViewBase(GenericModelView):
    model = models.Widget
    schema = models.WidgetSchema()


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

By default, models are expected to have been created using [Flask-SQLAlchemy](http://flask-sqlalchemy.pocoo.org/).

```python
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String

from . import app

db = SQLAlchemy(app)


class Widget(db.Model):
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    color = Column(String, nullable=False)
```

Schemas can be standard marshmallow `Schema` instances or [marshmallow-sqlalchemy](https://marshmallow-sqlalchemy.readthedocs.io/) `TableSchema` instances. They should not be `ModelSchema` instances.

```python
from marshmallow_sqlalchemy import TableSchema

from . import models


class WidgetSchema(TableSchema):
    class Meta:
        table = models.Widget.__table__
```

[build-badge]: https://img.shields.io/travis/4Catalyzer/flask-resty/master.svg
[build]: https://travis-ci.org/4Catalyzer/flask-resty

[pypi-badge]: https://img.shields.io/pypi/v/Flask-RESTy.svg
[pypi]: https://pypi.python.org/pypi/Flask-RESTy

[codecov-badge]: https://img.shields.io/codecov/c/github/4Catalyzer/flask-resty/master.svg
[codecov]: https://codecov.io/gh/4Catalyzer/flask-resty

[marshmallow-badge]: https://badgen.net/badge/marshmallow/2,3?list=1
[marshmallow-upgrading]: https://marshmallow.readthedocs.io/en/latest/upgrading.html
