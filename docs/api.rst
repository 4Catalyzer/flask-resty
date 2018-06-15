.. _api:

API
===

.. module:: flask_resty

Router
------

.. autoclass:: Api
  :members:

Views
-----

.. autoclass:: ApiView
  :members:

.. autoclass:: GenericModelView
  :members:

.. autoclass:: ModelView
  :members:

.. autofunction:: get_item_or_404

Access Control
--------------

.. autoclass:: AuthenticationBase
  :members:

.. autoclass:: NoOpAuthentication
  :members:

.. autoclass:: AuthorizationBase
  :members:

.. autoclass:: AuthorizeModifyMixin
  :members:

.. autoclass:: HasAnyCredentialsAuthorization
  :members:

.. autoclass:: HasCredentialsAuthorizationBase
  :members:

.. autoclass:: NoOpAuthorization
  :members:

Relationships
-------------

.. autoclass:: Related
  :members:

.. autoclass:: RelatedId
  :members:

.. autoclass:: RelatedItem
  :members:

Filtering
---------

.. autoclass:: ArgFilterBase
  :members:

.. autoclass:: ColumnFilter
  :members:
  :inherited-members:

.. autoclass:: FieldFilterBase
  :members:
  :inherited-members:

.. autoclass:: Filtering
  :members:

.. autofunction:: model_filter

.. autoclass:: ModelFilter
  :members:
  :inherited-members:

Pagination
----------

.. autoclass:: CursorPaginationBase
  :members:
  :inherited-members:

.. autoclass:: LimitOffsetPagination
  :members:
  :inherited-members:

.. autoclass:: LimitPagination
  :members:
  :inherited-members:

.. autoclass:: MaxLimitPagination
  :members:
  :inherited-members:

.. autoclass:: PagePagination
  :members:
  :inherited-members:

.. autoclass:: RelayCursorPagination
  :members:
  :inherited-members:

Sorting
-------

.. autoclass:: FieldSortingBase
  :members:
  :inherited-members:

.. autoclass:: FixedSorting
  :members:
  :inherited-members:

.. autoclass:: Sorting
  :members:
  :inherited-members:

.. autoclass:: SortingBase
  :members:

Exceptions
----------

.. autoclass:: ApiError
  :members:
  :inherited-members:
