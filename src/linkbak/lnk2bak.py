#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script reads a list of links and dumps the corresponding pages in HTML
and PDF. Pages are stored in output directories identified by the sha256 of the
links. An additional JSON index is also written to keep track of which links are
stored in which directory. The content is extracted with `readability`, PDFs are
generated with `chromium` in `headless` mode. Links can be downloaded in
parallel, previous failed attempts can be ignored or retried, and a custom
timeout is supported.

Example: `lnk2bak.py -v -j10 https://github.com/shaarli/Shaarli/releases.atom`

This command downloads HTML and PDFs for each of the links found in the Shaarli
atom feed on Github, allowing up to 10 downloads in parallel.
"""

import argparse
import contextlib
import json
import multiprocessing
import os
from pathlib import Path

from handlers import HTMLHandler, MetadataHandler, PDFHandler
from utils import get_link_path, get_links, get_logger, get_output_dir


def start_link_handler(link, args):
    """
    Retrieve link content, dumps:
    - summary as HTML
    - metadata + in json
    - PDF
    """
    get_logger().warning("Processing %s", link)

    handlers = [PDFHandler, MetadataHandler, HTMLHandler]
    outdir = Path(get_link_path(link))

    if not outdir.exists():
        outdir.mkdir()

    for handler_class in handlers:
        handler_class().run_wrapper(link, args)


def merge_json():
    """
    Merge all JSON files
    """
    results = []

    output_dir = get_output_dir()

    for jsonfile in Path(output_dir).glob("**/*.json"):
        if str(jsonfile) == f"{output_dir}/results.json":
            continue
        get_logger().debug("Appending %s", str(jsonfile))
        with jsonfile.open() as json_fp:
            results.append(json.load(json_fp))

    with open(f'{output_dir}/results.json', 'w') as json_results_fp:
        json.dump(results, json_results_fp, indent=True)


def parse_args():
    """
    Parse arguments
    """
    default_timeout = 60
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        nargs=1,
        help="RSS, Atom, HTML or simple text file containing links. For RSS "
        "and Atom feeds, a URL can be provided.")
    parser.add_argument(
        "-f", "--force", action='store_true', help="Retry failed")
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=default_timeout,
        help="Timeout (seconds, default: %s)" % default_timeout)
    parser.add_argument(
        "-j",
        type=int,
        help="Number of parallel link processing (default: %s)" %
        os.cpu_count())
    parser.add_argument(
        "-v", "--verbose", action='store_true', help="Verbose mode")

    return parser.parse_args()


def setup_logging(args):
    """Setup the logging
    :returns: TODO

    """
    import logging
    handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s %(levelname)8s %(name)s '
                                  '| %(message)s')
    handler.setFormatter(formatter)
    logger = get_logger()
    logger.addHandler(handler)

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


def main():
    """
    Run the script
    """
    args = parse_args()
    setup_logging(args)
    outdir = Path(get_output_dir())

    if not outdir.exists():
        outdir.mkdir()

    nb_workers = args.j if args.j else os.cpu_count()
    get_logger().warning("Using %s workers", nb_workers)

    if nb_workers > 1:
        with contextlib.closing(multiprocessing.Pool(nb_workers)) as pool:
            pool.starmap(start_link_handler,
                         [(l, args) for l in get_links(args.file[0])])
    else:
        for link in get_links(args.file[0]):
            start_link_handler(link, args)

    # Read all individual json files and merge them
    merge_json()


if __name__ == "__main__":
    main()
