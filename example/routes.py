# example/routes.py

from flask_resty import Api

from . import app, views

api = Api(app, prefix="/api")

api.add_resource("/authors/", views.AuthorListView, views.AuthorView)
api.add_resource("/books/", views.BookListView, views.BookView)
api.add_ping("/ping/")
