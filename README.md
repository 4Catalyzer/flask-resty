# flask-jsonapiview [![Travis][build-badge]][build] [![PyPI][pypi-badge]][pypi]
Building blocks for [JSON API](http://jsonapi.org/) endpoints for [Flask](http://flask.pocoo.org/).

[![Coveralls][coveralls-badge]][coveralls]

## Usage

Create a [SQLAlchemy](http://www.sqlalchemy.org/) model and a [marshmallow](http://marshmallow.rtfd.org/) schema, then: 

```python
from flask.ext.jsonapiview import Api, GenericModelView

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

[build-badge]: https://img.shields.io/travis/4Catalyzer/flask-jsonapiview/master.svg
[build]: https://travis-ci.org/4Catalyzer/flask-jsonapiview

[pypi-badge]: https://img.shields.io/pypi/v/Flask-JSONAPIView.svg
[pypi]: https://pypi.python.org/pypi/Flask-JSONAPIView

[coveralls-badge]: https://img.shields.io/coveralls/4Catalyzer/flask-jsonapiview/master.svg
[coveralls]: https://coveralls.io/github/4Catalyzer/flask-jsonapiview
