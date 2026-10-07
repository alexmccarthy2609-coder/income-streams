import argparse
import sys

from . import bulk_rename, clean_csv, excel_merge, pdf_tools, scrape_table


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="officekit", description="Automate the boring parts of office work.")
    sub = parser.add_subparsers(dest="command", required=True)
    for mod in (excel_merge, pdf_tools, bulk_rename, clean_csv, scrape_table):
        mod.add_parser(sub)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (ValueError, FileNotFoundError, PermissionError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
