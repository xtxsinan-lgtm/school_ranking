"""Parsers return a list of records: dict(college_raw, section, grad_year, period_start, period_end, count).

Registered by name in PARSERS and selected via the `parser` column of data/sources.csv.
"""
from . import html_table, pdf_list

PARSERS = {
    "html_table": html_table.parse,
    "pdf_list": pdf_list.parse,
}
