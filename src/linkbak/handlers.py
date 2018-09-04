"""
Handlers
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from readability import Document

from utils import get_link_hash, get_link_path, get_logger


class BaseHandler:
    """
    Baseclass providing minimal mandatory functions for handlers
    """

    output = ''
    requires = []

    def get_outfile(self, link):
        """ Returns the name of the expected output file for this particular handler
        """
        link_path = get_link_path(link)

        return f"{link_path}/{self.output}"

    def run_wrapper(self, link, meta, args):
        """
        Base class runner: check if the expected output file exists and if not,
        starts the runner. If the runner fails, a logfile is created with a
        specific name '.log'. The handler is also started if such a log file is
        found (reflecting a previous attempt that failed) if the -f/--force flag
        is found.
        """

        assert isinstance(meta, dict)
        logger = get_logger()

        # Skip if the target file already exists
        target_file = self.get_outfile(link)
        logfile = f"{target_file}.log"

        should_skip = False

        if Path(target_file).exists():
            logger.debug("Skipping %s", target_file)
            should_skip = True

        elif Path(logfile).exists():

            if not args.force:
                logger.debug("Skipping %s...", logfile)

                should_skip = True
            else:
                logger.debug("%s found, retrying...", logfile)
                Path(logfile).unlink()

        newfields = {}

        if not should_skip:
            # Run dependencies

            for required in self.requires:
                logger.debug("Running %s dependency %s for %s",
                             self.__class__.__name__, required.__name__, link)
                meta = required().run_wrapper(link, meta, args)
                assert isinstance(meta, dict)
            try:
                # Run it
                logger.debug("Running %s for %s", self.__class__.__name__,
                             link)
                newfields = self.run(link, meta, args)

                if not newfields:
                    newfields = {}
            except Exception as exception:
                # Dump log if it fails

                if logger.isEnabledFor(logging.DEBUG):
                    with open(f"{target_file}.log", 'w') as logfile_fp:
                        logfile_fp.write(str(exception))

        # If the expected output file has been generated, register id

        if Path(target_file).exists():
            http_path = "%s/%s" % (get_link_hash(link), self.output)
            newfields[self.__class__.__name__] = [
                http_path, datetime.now().isoformat()
            ]

        assert isinstance(meta, dict)
        assert isinstance(newfields, dict)

        return {**meta, **newfields}

    def run(self, link, meta, args):
        """
        Placeholder for the real run method
        """
        raise NotImplementedError()


class PDFHandler(BaseHandler):
    """
    Handler using Chrome/Chromium to create a PDF out of a link.
    """

    output = 'output.pdf'

    def run(self, link, meta, args):
        # TODO Should be able to use a custom profile (e.g. with ublock origin)
        # TODO remove `--no-sandbox`. This is currently required by the
        # Dockerfile, which should be fixed first.

        if meta["sensible-type"] == "pdf":
            return

        cmdargs = [
            args.chrome_binary, "--headless", "--no-sandbox", "--print-to-pdf",
            link
        ]
        subprocess.run(
            cmdargs,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=get_link_path(link),
            timeout=args.timeout)


class MetadataHandler(BaseHandler):
    """
    Handler for metadata : link -> hash
    """

    output = 'metadata.json'

    def _get_sensible_content_type(self, content_type):
        patterns = {"text/html": "html", "application/pdf": "pdf"}

        for pattern, sensible_type in patterns.items():
            if pattern in content_type:
                return sensible_type

        return content_type

    def run(self, link, meta, args):
        content_type = ""
        sensible_type = ""
        try:
            r = requests.head(link, timeout=args.timeout)

            if "Content-Type" in r.headers:
                content_type = r.headers["Content-Type"]
                sensible_type = self._get_sensible_content_type(content_type)
        except Exception as e:
            print(str(e))

        return {
            "id": get_link_hash(link),
            "link": link,
            "content-type": content_type,
            "sensible-type": sensible_type
        }

    def commit(self, link, meta, args):
        assert isinstance(meta, dict)
        with open(self.get_outfile(link), 'w') as metadatajson_fp:
            json.dump(meta, metadatajson_fp, indent=True)


class HTMLHandler(BaseHandler):
    """
    Handler for HTML using requests.
    """

    output = "index.html"

    def run(self, link, meta, args):
        response = requests.get(link, timeout=args.timeout)

        if meta["sensible-type"] == "html":
            doc = Document(response.text)
            with open(self.get_outfile(link), "w") as htmlfile_fp:
                htmlfile_fp.write(doc.summary())
        elif meta["sensible-type"] == "pdf":
            self.output = "index.pdf"
            with open(self.get_outfile(link), "wb") as htmlfile_fp:
                htmlfile_fp.write(response.content)


class DomHandler(BaseHandler):
    """
    Handler for DOM, with chrome/chromium, which is subsequently used by
    Mozilla's readability, epub, mobi and ReadablePDF.
    """

    output = 'index.dom'

    def run(self, link, meta, args):

        if meta["sensible-type"] != "html":
            return {}

        link_path = get_link_path(link)

        # Run chrome
        process = subprocess.run(
            ["chromium", "--headless", "--no-sandbox", "--dump-dom", link],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            timeout=args.timeout)

        if process.stderr and get_logger().isEnabledFor(logging.DEBUG):
            with open(f"{link_path}/index.dom.log", 'w') as fp:
                fp.write(process.stderr.decode())

        with open(f"{link_path}/index.dom", 'w') as fp:
            fp.write(process.stdout.decode())

        # Read title with BeautifulSoup
        title = ''
        try:
            soup = BeautifulSoup(process.stdout, 'lxml')
            title = soup.find('title').text.strip()
        except AttributeError as e:
            pass
        except Exception as e:
            get_logger().error(str(e))

        return {'title': title}


class ReadableHandler(BaseHandler):
    """
    Handler for readable content using Mozilla's readability.
    """

    output = 'index.readable.html'
    requires = [DomHandler]

    def run(self, link, meta, args):

        if meta["sensible-type"] != "html":
            return
        link_path = get_link_path(link)
        # Run readability
        readpath = __loader__.path[:__loader__.path.rfind('/')]
        process = subprocess.run(
            ["node", f"{readpath}/read.js"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=link_path,
            timeout=args.timeout)

        if process.stderr and get_logger().isEnabledFor(logging.DEBUG):
            with open(f"{link_path}/index.readable.html.log", 'w') as fp:
                fp.write(process.stderr.decode())

        with open(f"{link_path}/index.readable.html", 'w') as fp:
            fp.write(process.stdout.decode())


class PandocHandler(BaseHandler):
    """
    Generic handler for Pandoc
    """
    requires = [ReadableHandler]

    def run(self, link, meta, args):
        if meta["sensible-type"] != "html":
            return

        link_path = get_link_path(link)

        process = subprocess.run(
            ["pandoc", f"-o{self.output}", "index.readable.html"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=link_path,
            timeout=args.timeout)

        if process.stderr and get_logger().isEnabledFor(logging.DEBUG):
            with open(f"{link_path}/{self.output}.err", 'w') as fp:
                fp.write(process.stderr.decode())

        if process.stdout and get_logger().isEnabledFor(logging.DEBUG):
            with open(f"{link_path}/{self.output}.out", 'w') as fp:
                fp.write(process.stdout.decode())


class EpubHandler(PandocHandler):
    """
    Handler for EPUB file format
    """

    output = "pandoc.epub"


class MobiHandler(PandocHandler):
    """
    Handler for MOBI file format.
    """

    output = "pandoc.mobi"


class MarkdownHandler(PandocHandler):
    """
    Handler for Markdown file format.
    """

    output = "pandoc.md"


class ReadablePDFHandler(BaseHandler):
    """
    Handler for readable PDF files, i.e. PDF files generated by Pandoc from
    either the DOM dump, or if it fails, from the EPUB file.
    """

    output = "pandoc.pdf"
    requires = [EpubHandler, ReadableHandler]

    def run(self, link, meta, args):
        if meta["sensible-type"] != "html":
            return
        link_path = get_link_path(link)

        for source in ["index.readable.html", "pandoc.epub"]:

            if Path(f"{link_path}/{self.output}").exists():
                break

            process = subprocess.run(
                [
                    "pandoc",
                    "-opandoc.pdf",
                    # xelatex seems to work better?
                    # "--latex-engine=xelatex",  # On Stretch?
                    # "--pdf-engine=xelatex",  # On Arch?
                    source,
                ],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                cwd=link_path,
                timeout=args.timeout)

            if process.stderr and get_logger().isEnabledFor(logging.DEBUG):
                with open(f"{link_path}/{self.output}.{source}.err",
                          'w') as fp:
                    fp.write(process.stderr.decode())

            if process.stdout and get_logger().isEnabledFor(logging.DEBUG):
                with open(f"{link_path}/{self.output}.{source}.out",
                          'w') as fp:
                    fp.write(process.stdout.decode())
