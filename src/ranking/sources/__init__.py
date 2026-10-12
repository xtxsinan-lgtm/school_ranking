"""Parsers return a list of records: dict(college_raw, section, grad_year, period_start, period_end, count).

Registered by name in PARSERS and selected via the `parser` column of data/sources.csv.
"""
from . import csv_cells, html_headcount, html_lines, html_table, pdf_list, pdf_year_blocks, text_dash_lists

PARSERS = {
    "html_table": html_table.parse,
    "pdf_list": pdf_list.parse,
    "csv_cells": csv_cells.parse,
    "text_dash_lists": text_dash_lists.parse,
    "html_headcount": html_headcount.parse,
    "html_lines": html_lines.parse,
    "pdf_year_blocks": pdf_year_blocks.parse,
}
