"""Shared helper for server-side DataTables endpoints.

Used by any app's views to answer a jQuery DataTables "server-side
processing" AJAX request: https://datatables.net/manual/server-side

The client (see the generic init script in templates/base.html) reads
`data-field="..."` off each `<th>` to build the column list, so a view
only needs to supply, per row, a dict keyed by those same field names.
"""
from django.db.models import Q
from django.http import JsonResponse


def datatable_response(request, queryset, row_fn, search_fields, order_fields):
    """Build the JSON response DataTables expects.

    - queryset: base (unfiltered, unsearched) queryset for this table.
    - row_fn: callable(obj) -> dict of {field_name: cell value/html}.
    - search_fields: ORM lookup strings (without the __icontains suffix)
      used to build the OR filter for the global search box.
    - order_fields: list of ORM field names, index-aligned with the
      client's column order (None for a column that can't be sorted,
      e.g. an "Actions" column with no backing field).
    """

    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search_value = (request.GET.get("search[value]") or "").strip()

    records_total = queryset.count()

    filtered_qs = queryset

    if search_value and search_fields:
        search_q = Q()
        for field in search_fields:
            search_q |= Q(**{f"{field}__icontains": search_value})
        filtered_qs = filtered_qs.filter(search_q)

    records_filtered = filtered_qs.count()

    order_col_index = request.GET.get("order[0][column]")
    order_dir = request.GET.get("order[0][dir]", "asc")

    order_field = None
    if order_col_index is not None:
        try:
            order_field = order_fields[int(order_col_index)]
        except (ValueError, IndexError, TypeError):
            order_field = None

    if order_field:
        if order_dir == "desc":
            order_field = f"-{order_field}"
        filtered_qs = filtered_qs.order_by(order_field)

    if length == -1:
        page_qs = filtered_qs[start:]
    else:
        page_qs = filtered_qs[start:start + length]

    data = [row_fn(obj) for obj in page_qs]

    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data,
    })
