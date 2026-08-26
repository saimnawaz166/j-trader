# J. Gold Traders

Django-based inventory management system: stock in/out, suppliers,
customers, sales invoices, expenses, reports and a dashboard, behind
username/password login.

## Setup

```bash
cd inventory_system
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open `http://127.0.0.1:8000/` — you'll be redirected to the login page.

## Apps

- **accounts** — login/logout, and (superuser-only) staff account management
  under Settings.
- **dashboard** — the site root (`/`): revenue, pending payments, this
  month's sales/purchases/expenses, customer/supplier counts, and the 5 most
  recent invoices.
- **inventory** — Suppliers, Customers, Stock In, Stock Out, and Invoices.
  There is no product catalog: each Stock In/Stock Out/invoice line is just
  a free-text item name typed in at the time, with no quantity-on-hand
  tracking. Every Stock In automatically creates a matching **Purchase**
  invoice (supplier); every Stock Out automatically creates a matching
  **Sale** invoice (customer). Both types share the same `Invoice` model
  and the same Invoices page (distinguished by a Type badge); a sales
  invoice can also be created directly (multi-line item form) from the
  Invoices page.
- **expenses** — simple categorized expense tracking with a monthly
  breakdown.
- **reports** — inventory valuation, monthly P&L estimate, category and
  expense breakdowns, low-stock table.

## Notes

- There is no `Product` model or catalog. Stock In, Stock Out and invoice
  line items each store a plain `item_name` text field instead of a
  foreign key to a shared product table — this was a deliberate
  simplification, not an oversight. As a result there is no stock-on-hand
  tracking or low-stock alerting anywhere in the app.
- The "estimated profit" figure on the Reports page is a rough monthly
  estimate (sales − this month's purchasing − this month's expenses), not a
  precise cost-of-goods-sold calculation.
- Every create/edit view validates input through a Django `Form`/`ModelForm`
  in `forms.py` for its app, rather than parsing `request.POST` by hand.
