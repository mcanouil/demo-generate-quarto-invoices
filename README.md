# Generate Quarto Invoices

This is a simple script to generate biweekly invoices using Quarto/Typst.  
It first generates YAML files for each invoice, then generates the invoices from one single Quarto document.

## Usage

```bash
uv run generate-invoices.py \
  --name="Consulting" \
  --item="Strategy workshop|Two-day on-site facilitation.|2|1500|20" \
  --item="Written report|A summary of the workshop.|1|450|20" \
  --currency="GBP" \
  --penalty="£40" \
  --recipient="Company-Inc" \
  --first="2024-01-15"\
  --last="2024-01-31" \
  --template="template.qmd"
```

Give one `--item` for each line of the invoice, with up to five fields separated by a vertical bar:

```text
description|details|quantity|unit-price|vat
```

Only the description is required.
The other fields default to an empty text, `1`, `0`, and `0`.
The unit price excludes VAT, and the VAT rate is a percentage.
An amount can be written with thousands separators, as `1,234.56`.

`--currency` is optional and defaults to `GBP`, which matches the `lang` and `region` of `template.qmd`.
`--penalty` is the charge for recovery costs.
It is optional and defaults to `£40`.
The invoice format writes it as given, so it must carry its own currency symbol.

Under the hood, this will generate a YAML file for each invoice, then generate the invoices from one single Quarto document using the `quarto render` command.

```bash
uv run quarto render template.qmd --metadata-file input/202401-001.yml --output output/INVOICE-N202401-001-Company-Inc.pdf
```

Each YAML file holds an `invoice.items` list.
The invoice format builds the totals table from it and computes the amounts, so `template.qmd` holds no table of its own.

Every invoice of one run gets the same line items.
The two files under `input/` were written by hand to show two different invoices, so the command above replaces them.

## Requirements

- Python >=3.14: <https://www.python.org/>
- Quarto >=1.9.37: <https://quarto.org>
- Invoice (Typst) 2.0.2: <https://github.com/mcanouil/quarto-invoice>
