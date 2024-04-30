"""
Extracts the version date from the FTP site for pubtator3

Since the FTP site is raw HTML the structure is fairly simplistic:
<a href="relation2pubtator3.gz">relation2pubtator3.gz</a>    2024-01-23 06:49  245M

We look for the <a> </a> instance that matches the file pattern we care about and then
get the next sibling to extract the version date
"""

# pylint: disable=import-outside-toplevel, no-name-in-module


def get_release(self) -> str:
    """
    Extracts the version date from the FTP site for pubtator3

    Since the FTP site is raw HTML the structure is fairly simplistic:
    <a href="relation2pubtator3.gz">relation2pubtator3.gz</a>    2024-01-23 06:49  245M

    We look for the attribute instance that matches the file pattern we care about and then
    get the next sibling to extract the version date

    We then manipulate the string to strip out the time and data size so we only pull back
    string date
    """

    import re
    import urllib
    import urllib.request

    import bs4

    from biothings import config

    logger = config.logger

    pubtator_ftp_site = "https://ftp.ncbi.nlm.nih.gov/pub/lu/PubTator3/"
    request_timeout_sec = 15

    # [Bandit security warning note]
    # any usage of the urllib trigger the warning: {B310: Audit url open for permitted schemes}
    # urllib.request.urlopen supports file system access via ftp:// and file://
    #
    # if our usage accepted external input, then this would be a potential security concern, but
    # our use case leverages hard-coded URL's pointing directly at the FDA webpages
    try:
        page_request = urllib.request.Request(url=pubtator_ftp_site, data=None, headers={}, method="GET")
        with urllib.request.urlopen(url=page_request, timeout=request_timeout_sec) as http_response:  # nosec
            raw_html_structure = b"".join(http_response.readlines())
    except Exception as gen_exc:
        logger.exception(gen_exc)
        release_version = "Unknown"
        return release_version

    html_parser = bs4.BeautifulSoup(raw_html_structure, features="html.parser")

    attribute_tag = html_parser.find("a", href=re.compile("relation2pubtator3"))
    metadata_string = attribute_tag.next_sibling
    release_version = metadata_string.strip().split()[0]
    return release_version
