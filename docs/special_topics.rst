Special Topics
==============

Customizing CRUD behavior
-------------------------

You can customize how your model objects are created, updated, and deleted by overriding
the ``(create|update|delete)_item`` and ``(create|update|delete)_item_raw`` hooks on 
`ModelView <flask_resty.ModelView>`.

For example if you want to soft-delete models by setting the ``deleted_at`` column, you
can override `delete_item <ModelView.delete_item>` and `delete_item_raw <ModelView.delete_item_raw>`.

.. code-block:: python

    class SoftDeleteMixin(ModelView):
        def delete_item(self, item):
            if item.deleted_at:
                flask.abort(404)

            super().delete_item(item)

        def delete_item_raw(self, item):
            item.deleted_at = datetime.datetime.now(timezone.utc)

Usage with marshmallow-sqlalchemy
---------------------------------

Schemas may be generated with `marshmallow-sqlalchemy <https://marshmallow-sqlalchemy.readthedocs.io/>`_ .
You may generate schemas from your models using ``TableSchema``. **Do not use ModelSchema**.

.. code-block:: python

    from marshmallow_sqlalchemy import TableSchema

    from . import models


    class AuthorSchema(TableSchema):
        class Meta:
            table = models.Author.__table__


You may also use the ``field_for`` helper.

.. code-block:: python

    from marshmallow import Schema
    from marshmallow_sqlalchemy import field_for

    from . import models


    class BookSchema(Schema):
        id = field_for(models.Book, "id")
        author_id = field_for(models.Book, "author_id", required=True)
        published_at = field_for(models.Book, "published_at", required=True)
        created_at = field_for(models.Book, "created_at", dump_only=True)



.. todo:: Testing

.. todo:: Project organization for larger applications (subpackages)

.. todo:: Loading related data

.. todo:: Prefetching data (base_query_options)
