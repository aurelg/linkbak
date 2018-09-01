"""
Handlers
"""

import json
from pathlib import Path
from subprocess import PIPE, run

import requests
from readability import Document

from utils import get_link_hash, get_link_path, get_logger


class BaseHandler:
    """
    Baseclass providing minimal mandatory functions for handlers
    """

    output = ''

    def get_outfile(self, link):
        """ Returns the name of the expected output file for this particular handler
        """
        link_path = get_link_path(link)

        return f"{link_path}/{self.output}"

    def run_wrapper(self, link, args):
        """
        Base class runner: check if the expected output file exists and if not,
        starts the runner. If the runner fails, a logfile is created with a
        specific name '.log'. The handler is also started if such a log file is
        found (reflecting a previous attempt that failed) if the -f/--force flag
        is found.
        """

        # Skip if the target file already exists
        target_file = self.get_outfile(link)
        logfile = f"{target_file}.log"

        if Path(target_file).exists():
            get_logger().debug("Skipping %s", target_file)

            return

        if Path(logfile).exists():

            if args.force:
                get_logger().debug("%s found, retrying...", logfile)
                Path(logfile).unlink()
            else:
                get_logger().debug("Skipping %s...", logfile)

                return

        try:
            # Run it
            self.run(link, args)
        except Exception as exception:
            # Dump log if it fails
            with open(f"{target_file}.log", 'w') as logfile_fp:
                logfile_fp.write(str(exception))

    def run(self, link, args):
        """
        Placeholder for the real run method
        """
        raise NotImplementedError()


class PDFHandler(BaseHandler):
    """
    Handler using Chrome/Chromium to create a PDF out of a link
    """

    output = 'output.pdf'

    def run(self, link, args):
        # TODO Should be able to use a custom profile (e.g. with ublock origin)
        # TODO remove `--no-sandbox`. This is currently required by the
        # Dockerfile, which should be fixed first.
        cmdargs = [
            args.chrome_binary, "--headless", "--no-sandbox", "--print-to-pdf",
            link
        ]
        run(cmdargs,
            stdout=PIPE,
            stderr=PIPE,
            cwd=get_link_path(link),
            timeout=args.timeout)


class MetadataHandler(BaseHandler):
    """
    Handler for metadata : link -> hash
    """

    output = 'metadata.json'

    def run(self, link, args):
        with open(self.get_outfile(link), 'w') as metadatajson_fp:
            json.dump(
                {
                    "id": get_link_hash(link),
                    "link": link
                },
                metadatajson_fp,
                indent=True)


class HTMLHandler(BaseHandler):
    """
    Handler for html
    """

    output = 'index.html'

    def run(self, link, args):
        response = requests.get(link)
        doc = Document(response.text)

        # TODO might not be html, what about PDFs: check with content type as
        # described in
        # <https://stackoverflow.com/questions/23718424/requests-get-content-type-size-without-fetching-the-whole-page-content>
        with open(self.get_outfile(link), 'w') as htmlfile_fp:
            htmlfile_fp.write(doc.summary())
