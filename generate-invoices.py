#!/usr/bin/env python3
"""
This module generates invoices for a given date range.
"""

import argparse
import hashlib
import json
import os
import subprocess

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from dateutil.rrule import WEEKLY, rrule


def parse_amount(flag, value):
    """
    Convert a command line amount into a number the invoice format accepts.

    Args:
        flag (str): The name of the command line flag, used in the error message.
        value (str): The amount, with or without thousands separators.

    Returns:
        float: The amount.

    Raises:
        ValueError: If the value is not a number.
    """

    cleaned = str(value).replace(",", "").replace(" ", "").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError as error:
        raise ValueError(
            f"{flag} must be a number, got {value!r}. Write it as 1234.56 or 1,234.56."
        ) from error

def format_number(value):
    """
    Write a number as a YAML scalar the Typst template can parse.

    Args:
        value (float): The number.

    Returns:
        str: The number, without a decimal part when it is a whole number.
    """

    if value.is_integer():
        return str(int(value))
    return repr(value)

def quote(value):
    """
    Write a text as a YAML double-quoted scalar.

    A JSON string is a valid YAML double-quoted scalar, so a colon or a quotation
    mark in the text cannot break the file.

    Args:
        value (str): The text.

    Returns:
        str: The quoted text, with its accents and symbols left as they are.
    """

    return json.dumps(value, ensure_ascii=False)

def parse_item(value):
    """
    Convert a --item value into one line item of the invoice.

    The value holds up to five fields, separated by a vertical bar:
    description, details, quantity, unit price, and VAT rate.
    Only the description is required.

    Args:
        value (str): The value of one --item flag.

    Returns:
        dict: The line item, with the numbers already parsed.

    Raises:
        ValueError: If the value holds too many fields, or no description.
    """

    fields = value.split("|")
    if len(fields) > 5:
        raise ValueError(
            f"--item takes at most 5 fields, got {len(fields)} in {value!r}. "
            "Write it as 'description|details|quantity|unit-price|vat'."
        )

    fields += [""] * (5 - len(fields))
    description, details, quantity, unit_price, vat = (field.strip() for field in fields)

    if not description:
        raise ValueError(f"--item needs a description, got {value!r}.")

    return {
        "description": description,
        "details": details,
        "quantity": parse_amount("--item quantity", quantity) if quantity else 1.0,
        "unit-price": parse_amount("--item unit price", unit_price) if unit_price else 0.0,
        "vat": parse_amount("--item VAT rate", vat) if vat else 0.0,
    }

def generate_invoices(
    name, items, recipient, first, last, template,
    currency="GBP", penalty="£40"
):
    """
    Generate invoices for a given date range.

    Args:
        name (str): The object of the invoice.
        items (list): The line items, as written by --item.
        recipient (str): The recipient of the invoice.
        first (str): The first date of the invoice.
        last (str): The last date of the invoice.
        template (str): The Quarto document to serve as template for the invoice.
        currency (str): The ISO 4217 currency code of the invoice.
        penalty (str): The recovery costs, written with their currency symbol.

    Raises:
        ValueError: If no line item is given.
    """

    line_items = [parse_item(item) for item in items or []]
    if not line_items:
        raise ValueError("At least one --item is needed to write an invoice.")

    start_date = parse(first)
    end_date = parse(last)
    month_counter = 1
    previous_month = start_date.month
    invoice_numbers = []
    for issued_date in rrule(WEEKLY, dtstart=start_date, until=end_date, interval=2):
        if issued_date.month != previous_month:
            month_counter = 1
        invoice_number = f"{issued_date.strftime('%Y%m')}-{month_counter:03d}"
        invoice_numbers.append(invoice_number)
        hash_object = hashlib.sha256(invoice_number.encode())
        hex_dig = hash_object.hexdigest()
        due_date = issued_date + relativedelta(day=31, months=1)

        month_counter += 1
        previous_month = issued_date.month

        filename = f"input/{invoice_number}.yml"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(f"title: {quote(f'{name} {start_date.year}')}\n")
            invoice_start_date = (issued_date - relativedelta(weeks=2)).strftime('%Y/%m/%d')
            invoice_end_date = (issued_date - relativedelta(days=1)).strftime('%Y/%m/%d')
            file.write(f"description: {quote(f'{invoice_start_date} -- {invoice_end_date}')}\n")
            file.write("invoice:\n")
            file.write(f"  number: {quote(invoice_number)}\n")
            file.write(f"  issued: {issued_date.strftime('%Y-%m-%d')}\n")
            file.write(f"  due: {due_date.strftime('%Y-%m-%d')}\n")
            file.write(f"  reference: {quote(hex_dig[:9])}\n")
            file.write(f"  currency: {quote(currency)}\n")
            file.write(f"  penalty: {quote(penalty)}\n")
            file.write("  items:\n")
            for item in line_items:
                file.write(f"    - description: {quote(item['description'])}\n")
                if item["details"]:
                    file.write(f"      details: {quote(item['details'])}\n")
                file.write(f"      quantity: {format_number(item['quantity'])}\n")
                file.write(f"      unit-price: {format_number(item['unit-price'])}\n")
                file.write(f"      vat: {format_number(item['vat'])}\n")

    for invoice in invoice_numbers:
        subprocess.run([
            'quarto', 'render', f'{template}',
            '--metadata-file', f'input/{invoice}.yml',
            '--output', f'INVOICE-N{invoice}-{recipient}.pdf'
        ], check=True)

        os.rename(
            f'INVOICE-N{invoice}-{recipient}.pdf',
            f'output/INVOICE-N{invoice}-{recipient}.pdf'
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="The object of the invoice")
    parser.add_argument(
        "--item",
        action="append",
        help="One line item, as 'description|details|quantity|unit-price|vat'."
             " Repeat the flag for each line item"
    )
    parser.add_argument("--currency", default="GBP", help="The ISO 4217 currency code")
    parser.add_argument(
        "--penalty",
        default="£40",
        help="The recovery costs, written with their currency symbol"
    )
    parser.add_argument("--recipient", help="The recipient of the invoice")
    parser.add_argument("--first", help="The first date of the invoice")
    parser.add_argument("--last", help="The last date of the invoice")
    parser.add_argument("--template", help="The Quarto document to serve as template for the invoice")
    args = parser.parse_args()

    generate_invoices(
        name=args.name,
        items=args.item,
        recipient=args.recipient,
        first=args.first,
        last=args.last,
        template=args.template,
        currency=args.currency,
        penalty=args.penalty
    )
