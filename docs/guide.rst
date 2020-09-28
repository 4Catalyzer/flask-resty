Building an Application
=======================

Project Structure
-----------------

When building applications with Flask-RESTy, we recommend starting with the following project structure.

::

    example
    ├── __init__.py
    ├── settings.py  # App settings
    ├── models.py    # SQLAlchemy models
    ├── schemas.py   # marshmallow schemas
    ├── auth.py      # Authn and authz classes
    ├── views.py     # View classes
    └── routes.py    # Route declarations

The ``__init__.py`` file initializes the `Flask <flask.Flask>` app and hooks up the routes.

.. literalinclude:: ../example/__init__.py
    :language: python

.. note::
    `# noqa: F401 isort:skip` prevents Flake8 and isort from reporting a misplaced import.

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

Most view classes will extend `flask_resty.GenericModelView` which
provides standard CRUD behavior.

Typically, you will expose a model with a list endpoint (``/api/authors/``), and a detail
endpoint (``/api/authors/<id>``). To keep your code DRY, we recommend using a common base class for both endpoints.

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

Add pagination to your list endpoints by setting the ``pagination`` attribute on the base class.

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

Add sorting to your list endpoints by setting the ``sorting`` attribute on the base class.

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

Filtering natively handles multiple values. Specify values in a comma separated string to the query parameter, e.g., ``/books?author_id=1,2``.

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

Add authentication by setting the ``authentication`` attribute on the base class. We'll use `NoOpAuthentication <flask_resty.NoOpAuthentication>`
for this example. Flask-RESTy also includes a `JwtAuthentication <flask_resty.JwtAuthentication>` class for authenticating with
`JSON Web Tokens <https://jwt.io/>`_ .


.. code-block:: python

    class AuthorViewBase(GenericModelView):
        model = models.Author
        schema = schemas.AuthorSchema()

        authentication = NoOpAuthentication()

        pagination = PagePagination(page_size=10)
        sorting = Sorting("created_at", default="-created_at")

.. seealso::

    See the :ref:`authentication` section of the API docs for a listing of available authentication classes.

Authorization
-------------

Add authorization by setting the ``authorization`` attribute on the base class. We'll use `NoOpAuthorization <flask_resty.NoOpAuthorization>`
for this example. You will likely need to implement your own subclasses of `AuthorizationBase <flask_resty.AuthorizationBase>`
for your applications.


.. code-block:: python

    class AuthorViewBase(GenericModelView):
        model = models.Author
        schema = schemas.AuthorSchema()

        authentication = NoOpAuthentication()
        authorization = NoOpAuthorization()

        pagination = PagePagination(page_size=10)
        sorting = Sorting("created_at", default="-created_at")

.. seealso::

    See the :ref:`authorization` section of the API docs for a listing of available authorization classes.

Routes
------

The ``routes.py`` file contains the `Api <flask_resty.Api>` instance with which we can connect
our view classes to URL patterns.

.. literalinclude:: ../example/routes.py
    :language: python

Testing
-------

Flask-RESTy includes utilities for writing integration tests for your applications.
Here's how you can use them with `pytest <https://docs.pytest.org>`_.

.. literalinclude:: ../example/test_example.py
    :language: python
    :lines: 1-32

The first two fixtures ensure that we start with a clean database for each test.
The third fixture constructs an `ApiClient <flask_resty.testing.ApiClient>` for
sending requests within our tests.

Let's test that we can create an author. Here we use `assert_response <flask_resty.testing.assert_response>`
to check the status code of the response and `assert_shape <flask_resty.testing.assert_shape>` to
validate the shape of the response body.

.. code-block:: python

    def test_create_author(client):
        response = client.post("/authors/", data={"name": "Fred Brooks"})
        data = assert_response(response, 201)
        assert_shape(data, {"id": ANY, "name": "Fred Brooks", "created_at": ANY})

We can test both the response code and the data shape using a single call. The following snippet
is equivalent to the above.

.. code-block:: python

    def test_create_author(client):
        response = client.post("/authors/", data={"name": "Fred Brooks"})
        data = assert_response(response, 201)
        assert_response(
            response, 201, {"id": ANY, "name": "Fred Brooks", "created_at": ANY}
        )

Running the Example Application
-------------------------------

To run the example application, clone the Flask-RESTy repo.

::

    $ git clone https://github.com/4Catalyzer/flask-resty.git
    $ cd flask-resty

Populate the database with some dummy data.

::

    $ python -m example.populate_db

Then serve the app on  ``localhost:5000``.

::

    $ FLASK_APP=example FLASK_ENV=development flask run

You can make requests using the `httpie <https://httpie.org/>`_ utility.

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
                "created_at": "2019-06-16T01:09:33.450768",
                "id": 2,
                "published_at": "2013-11-05T00:00:00",
                "title": "The Design of Everyday Things"
            },
            {
                "author_id": 2,
                "created_at": "2019-06-16T01:09:33.450900",
                "id": 3,
                "published_at": "2010-10-29T00:00:00",
                "title": "Living With Complexity"
            }
        ],
        "meta": {
            "has_next_page": false
        }
    }

The naive datetimes in the response are only because the example uses SQLite. A real application would use a timezone-aware datetime column in the database, and would have a UTC offset in the response.

Running the Shell
-----------------

Flask-RESTy includes an enhanced ``flask shell`` command that automatically imports all SQLAlchemy models and marshmallow schemas.
It will also automatically use IPython, BPython, or ptpython if they are installed.

::

    $ FLASK_APP=example flask shell
    3.8.5 (default, Jul 24 2020, 12:48:45)
    [Clang 11.0.3 (clang-1103.0.32.62)]

    _____ _           _         ____  _____ ____ _____
    |  ___| | __ _ ___| | __    |  _ \| ____/ ___|_   _|   _
    | |_  | |/ _` / __| |/ /____| |_) |  _| \___ \ | || | | |
    |  _| | | (_| \__ \   <_____|  _ <| |___ ___) || || |_| |
    |_|   |_|\__,_|___/_|\_\    |_| \_\_____|____/ |_| \__, |
                                                        |___/
    Flask app: example, Database: sqlite:///example.db

    Flask:
    app, g

    Schemas:
    AuthorSchema, BookSchema, Schema

    Models:
    Author, Book, commit, db, flush, rollback, session

    In [1]: Author
    Out[1]: example.models.Author

    In [2]: AuthorSchema
    Out[2]: example.schemas.AuthorSchema

.. note::
    Pass the ``--sqlalchemy-echo`` option to see database queries printed within your shell session.

The following app configuration options are available for customizing ``flask shell``:

- ``RESTY_SHELL_CONTEXT``: Dictionary of additional variables to include in the shell context.
- ``RESTY_SHELL_LOGO``: Custom logo.
- ``RESTY_SHELL_PROMPT``: Custom input prompt.
- ``RESTY_SHELL_OUTPUT``: Custom output prompt.
- ``RESTY_SHELL_CONTEXT_FORMAT``: Format to display shell context. May be ``'full'``, ``'short'``, or a function that receives the context dictionary as input and returns a string.
- ``RESTY_SHELL_IPY_AUTORELOAD``: Whether to load and enable the IPython autoreload extension (must be using ``ipython`` shell).
- ``RESTY_SHELL_IPY_EXTENSIONS``: List of IPython extension names to load (must be using ``ipython`` shell).
- ``RESTY_SHELL_IPY_COLORS``: IPython color style.
- ``RESTY_SHELL_IPY_HIGHLIGHTING_STYLE``: IPython code highlighting style.
- ``RESTY_SHELL_PTPY_VI_MODE``: Enable vi mode (must be using ``ptpython`` shell).
