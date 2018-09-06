"""
Misc helper functions
"""
import fcntl
import hashlib
import logging

import feedparser
from bs4 import BeautifulSoup


def get_output_dir():
    """

    Returns the output directory (currently `output`)
    """

    return "output"


def get_link_hash(link):
    """

    Returns the sha256 of the link
    """

    return hashlib.sha256(link.encode('utf-8')).hexdigest()


def get_link_path(link):
    """

    Returns the path of the link: `output_dir`/`link_hash`
    """
    hashid = get_link_hash(link)
    output_dir = get_output_dir()

    return f"{output_dir}/{hashid}"


def get_logger():
    """Get logger for linkbak
    :returns: TODO

    """

    return logging.getLogger('linkbak')


def get_links(filename):
    """ Return links from a filename (list, html, rss or atom)
    """

    def parse_feed():
        """

        Returns a set of links from an atom/rss feed
        """
        feed = feedparser.parse(filename)

        return {
            e.link.strip()

            for e in feed.entries if e.link.startswith('http')
        }

    def parse_html():
        """

        Returns a set of links from an HTML page
        """
        with open(filename) as html_file:
            soup = BeautifulSoup(''.join(html_file.readlines()), 'lxml')

        return {
            l['href'].strip()

            for l in soup.find_all('a') if l['href'].startswith('http')
        }

    def parse_list():
        """

        Returns a set of links from a list
        """
        with open(filename) as list_file:
            return {l.strip() for l in list_file if l.startswith('http')}

    # Parse from the most strict (feed) to the most undefined (list)

    # Try to parse as feed

    links = ()

    for parser in [parse_feed, parse_html, parse_list]:
        if not links:
            try:
                links = parser()

                if links:
                    get_logger().warning("Using parser %s", parser.__name__)
                    get_logger().warning("Found %s links", len(links))

                    return links
            except Exception:
                pass

    get_logger().error("Unknown file type")


class flocked(object):
    """ File locking """
    def __init__(self, file):
        self.file = file

    def __enter__(self):
        fcntl.lockf(self.file.fileno(), fcntl.LOCK_EX)

        return self.file

    def __exit__(self, *args):
        fcntl.lockf(self.file.fileno(), fcntl.LOCK_UN)
