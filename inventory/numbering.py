import re


def next_invoice_number(prefix, digits=7):
    """The next auto-generated invoice number for the given prefix.

    Looks at every invoice number already used anywhere (Stock In, Stock
    Out, and Invoice records) that matches "<prefix><digits>", and returns
    one past the highest one found - e.g. next_invoice_number("INV") might
    return "INV0000007". Starts at 1 (e.g. "INV0000001") if none exist yet.
    """

    from .models import Invoice, StockIn, StockOut

    pattern = re.compile(rf"^{re.escape(prefix)}(\d{{{digits}}})$")

    max_n = 0

    for queryset in (
        StockIn.objects.filter(invoice_number__startswith=prefix),
        StockOut.objects.filter(invoice_number__startswith=prefix),
        Invoice.objects.filter(invoice_number__startswith=prefix),
    ):
        for number in queryset.values_list("invoice_number", flat=True):
            match = pattern.match(number)
            if match:
                max_n = max(max_n, int(match.group(1)))

    n = max_n + 1
    candidate = f"{prefix}{n:0{digits}d}"

    # Extremely unlikely, but guard against a manually-typed number (from
    # before auto-numbering, or entered directly via /admin/) colliding
    # with the one we're about to hand out.
    while (
        StockIn.objects.filter(invoice_number=candidate).exists()
        or StockOut.objects.filter(invoice_number=candidate).exists()
        or Invoice.objects.filter(invoice_number=candidate).exists()
    ):
        n += 1
        candidate = f"{prefix}{n:0{digits}d}"

    return candidate
