Flask-RESTy
===========

Flask-RESTy provides building blocks for creating REST APIs with `Flask <http://flask.pocoo.org/>`_ ,
`SQLAlchemy <https://www.sqlalchemy.org/>`_, and `marshmallow <https://marshmallow.readthedocs.io/>`_.

.. code-block:: python

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


   api = Api(app, "/api")
   api.add_resource("/widgets", WidgetListView, WidgetView)

Features
--------

Flask-RESty provides the following functionality out of the box:

* Class-based CRUD views
* Schema-based request validation and response formatting with `marshmallow <https://marshmallow.readthedocs.io/>`_ 
* JWT and JWK authentication, with base classes for implementing your own authentication policies
* Authorization
* Sorting and pagination
* Filtering

Installation
------------

Flask-RESTy requires Python >= 3.6.

::

    $ pip install flask-resty

For JWT support:

::

    $ pip install flask-resty[jwt]

Guide
-----

.. toctree::
    :maxdepth: 2
    
    guide
    special_topics

API Reference
-------------

.. toctree::
   :maxdepth: 2

   api
