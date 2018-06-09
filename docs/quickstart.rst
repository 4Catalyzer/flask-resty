.. _quickstart:

Quickstart
==========

Create a `SQLAlchemy <http://www.sqlalchemy.org/>`__ model and a
`marshmallow <http://marshmallow.rtfd.org/>`__ schema, then::

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
