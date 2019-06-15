# example/views.py

import operator

from flask_resty import (
    ColumnFilter,
    Filtering,
    GenericModelView,
    PagePagination,
    Sorting,
)

from . import models, schemas


class AuthorViewBase(GenericModelView):
    model = models.Author
    schema = schemas.AuthorSchema()
    pagination = PagePagination(page_size=10)
    sorting = Sorting("created_at", default="-created_at")


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


class BookViewBase(GenericModelView):
    model = models.Book
    schema = schemas.BookSchema()
    pagination = PagePagination(page_size=10)
    sorting = Sorting("published_at", default="-published_at")
    filtering = Filtering(author_id=ColumnFilter(operator.eq, required=True))


class BookListView(BookViewBase):
    def get(self):
        return self.list()

    def post(self):
        return self.create()


class BookView(BookViewBase):
    def get(self, id):
        return self.retrieve(id)

    def patch(self, id):
        return self.update(id, partial=True)

    def delete(self, id):
        return self.destroy(id)
