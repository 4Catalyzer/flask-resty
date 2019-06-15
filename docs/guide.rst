Building an Application
=======================

Project Structure
-----------------

When building applications with Flask-RESTy, we recommend starting with the following project structure.

::

    example
    ├── __init__.py  # Contains your `Flask` instance
    ├── settings.py  # App settings
    ├── models.py    # SQLAlchemy models
    ├── schemas.py   # marshmallow schemas
    ├── auth.py      # Authn and authz classes
    ├── views.py     # View classes
    └── routes.py    # Route declarations

The ``__init__.py`` file will contain project boilerplate, including your `Flask <flask.Flask>` app instance.

.. literalinclude:: ../example/__init__.py
    :language: python

The ``routes`` import at the bottom of the file is necessary for hooking up the routes.

Models
------

Models are created using `Flask-SQLAlchemy <https://flask-sqlalchemy.palletsprojects.com>`_ .

.. literalinclude:: ../example/models.py
    :language: python

.. seealso::
  See the `Flask-SQLAlchemy documentation <https://flask-sqlalchemy.palletsprojects.com>`_
  for more information on defining models.

Schemas
-------

Schemas are used to validate request input and format response outputs.

.. literalinclude:: ../example/schemas.py
    :language: python

.. seealso::
  See the `marshmallow documentation <https://marshmallow.readthedocs.io>`_
  for more information on defining schemas.

Views
-----

Now to define our views. In simple APIs, most view classes will extend `flask_resty.GenericModelView` which
provides standard CRUD behavior.

Most commonly, you will expose a model with a list endpoint (``/api/authors/``), and a detail
endpoint (``/api/authors/<id>``). To keep your code DRY, we recommend using a common base class both endpoints.

For example:

.. code-block:: python

    # example/views.py

    from flask_resty import GenericModelView

    from . import models, schemas


    class AuthorViewBase(GenericModelView):
        model = models.Author
        schema = schemas.AuthorSchema()
        # authentication, authorization, pagination,
        # sorting, and filtering would also go here


The concrete view classes simply call the appropriate CRUD methods from `GenericModelView <flask_resty.GenericModelView>`.

.. code-block:: python

    class AuthorListView(AuthorViewBase):
        def get(self):
            return self.list()

        def post(self):
            return self.create()


    class AuthorView(AuthorViewBase):
        def get(self, id):
            return self.retrieve(id)

        def patch(self, id):
            return self.update(id, partial=True)

        def delete(self, id):
            return self.destroy(id)

.. note::

    Unimplemented HTTP methods will return ``405 Method not allowed``.


Pagination
----------

Add filtering to your list endpoints by setting the ``pagination`` attribute on the base class.

The following will allow clients to pass a ``page`` parameter in the query string, e.g. ``?page=2``.

.. code-block:: python

    class AuthorViewBase(GenericModelView):
        model = models.Author
        schema = schemas.AuthorSchema()
        pagination = PagePagination(page_size=10)


.. seealso::

    See the :ref:`pagination` section of the API docs for a listing of available pagination classes.


Sorting
-------

Add filtering to your list endpoints by setting the ``pagination`` attribute on the base class.

The following will allow clients to pass a ``sort`` parameter in the query string, e.g. ``?sort=-created_at``.

.. code-block:: python

    class AuthorViewBase(GenericModelView):
        model = models.Author
        schema = schemas.AuthorSchema()
        pagination = PagePagination(page_size=10)
        sorting = Sorting("created_at", default="-created_at")

.. seealso::

    See the :ref:`sorting` section of the API docs for a listing of available sorting classes.

Filtering
---------

Add filtering to your list endpoints by setting the ``filtering`` attribute on the base class.

.. code-block:: python

    class BookViewBase(GenericModelView):
        model = models.Book
        schema = schemas.BookSchema()
        pagination = PagePagination(page_size=10)
        sorting = Sorting("published_at", default="-published_at")
        # An error is returned if author_id is omitted from the query string
        filtering = Filtering(author_id=ColumnFilter(operator.eq, required=True))

.. seealso::

    See the :ref:`filtering` section of the API docs for a listing of available filtering classes.


Authentication
--------------

.. todo:: Add example

Authorization
-------------

.. todo:: Add example

Routes
------

The ``routes.py`` file contains the `Api <flask_resty.Api>` instance with which we can connect
our view classes to URL patterns.

.. literalinclude:: ../example/routes.py
    :language: python

Running the Example Application
-------------------------------

First, populate the database with some dummy data.

::

    $ python -m example.populate_db

Then serve the app on  ``localhost:5000``.

::

    $ FLASK_APP=example FLASK_ENV=development flask run

We can make requests using the `httpie <https://httpie.org/>`_ utility.

::

    $ pip install httpie

::

    $ http ":5000/api/books/?author_id=2"
    HTTP/1.0 200 OK
    Content-Length: 474
    Content-Type: application/json
    Date: Sun, 16 Jun 2019 01:39:04 GMT
    Server: Werkzeug/0.14.1 Python/3.7.3

    {
        "data": [
            {
                "author_id": 2,
                "created_at": "2019-06-16T01:09:33.450768+00:00",
                "id": 2,
                "published_at": "2013-11-05T00:00:00+00:00",
                "title": "The Design of Everyday Things"
            },
            {
                "author_id": 2,
                "created_at": "2019-06-16T01:09:33.450900+00:00",
                "id": 3,
                "published_at": "2010-10-29T00:00:00+00:00",
                "title": "Living With Complexity"
            }
        ],
        "meta": {
            "has_next_page": false
        }
    }
