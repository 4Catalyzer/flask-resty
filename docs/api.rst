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

.. _authentication:

Authentication
--------------

.. autoclass:: AuthenticationBase
  :members:

.. autoclass:: NoOpAuthentication

.. autoclass:: HeaderAuthenticationBase
  :members:

.. autoclass:: HeaderAuthentication

.. _authorization:

Authorization
-------------

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

.. _filtering:

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

.. _pagination:

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

.. _sorting:

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

Routing
-------

.. autoclass:: StrictRule
  :members:
  :inherited-members:

Fields
-------

.. autoclass:: RelatedItem

.. autoclass:: DelimitedList


Testing
-------

.. module:: flask_resty.testing

.. autoclass:: ApiClient

.. autofunction:: assert_shape

.. autofunction:: assert_response
