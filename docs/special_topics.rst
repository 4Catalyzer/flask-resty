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
You may generate schemas from your models using ``SQLAlchemySchema`` or ``SQLAlchemyAutoSchema``. **Do not use ModelSchema**.

.. code-block:: python

    from marshmallow_sqlalchemy import SQLAlchemySchema

    from . import models


    class AuthorSchema(SQLAlchemySchema):
        class Meta:
            model = models.Author
            include_fk = True


You can also use the ``auto_field`` helper.

.. code-block:: python

    from marshmallow import Schema
    from marshmallow_sqlalchemy import SQLAlchemySchema

    from . import models


    class BookSchema(SQLAlchemySchema):
        class Meta:
            model = models.Book

        id = auto_field()
        author_id = auto_field()
        published_at = auto_field()
        created_at = auto_field(dump_only=True)

Filter-only Fields
------------------

If you have a field that should only be used for filtering, you can
set both ``load_only`` and ``dump_only`` to `True` on the schema field.

.. code-block:: python

    class SoftDeletedObjectSchema(Schema):
        # Only used for filtering
        is_deleted = fields.Boolean(load_only=True, dump_only=True)

Filter-only fields will be validated when used as a filter
but will not be returned in the response body.

Recommendations for Larger Applications
---------------------------------------

.. todo:: Subpackages


Loading Related Data
--------------------

.. todo:: Document `Related`

Pre-fetching Data
-----------------

.. todo:: Document `base_query_options` and `Schema.get_query_options`
