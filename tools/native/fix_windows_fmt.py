#!/usr/bin/env python3
"""Backport the fmt 11.0.2 format-checker string-view fix for Clang.

Upstream diagnosis: https://github.com/fmtlib/fmt/issues/4177
Use the stored view for both parser and checker, avoiding separate evaluations
of a string literal. Compile-time checking and the formatting ABI are retained.
"""
import argparse
from pathlib import Path


def apply(include):
    path = Path(include) / 'fmt/base.h'
    text = path.read_text()
    if '#define FMT_VERSION 110002' not in text:
        raise ValueError('Expected the pinned fmt 11.0.2 dependency')
    before = 'detail::parse_format_string<true>(str_, checker(s));'
    after = 'detail::parse_format_string<true>(str_, checker(str_));'
    if text.count(after) == 1 and before not in text:
        return
    if text.count(before) != 1 or after in text:
        raise ValueError('Unexpected fmt format-checker context')
    path.write_text(text.replace(before, after))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('include', type=Path)
    apply(parser.parse_args().include)
