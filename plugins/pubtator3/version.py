"""
Extracts the version date from the FTP site for pubtator3

Since the FTP site is raw HTML the structure is fairly simplistic:
<a href="relation2pubtator3.gz">relation2pubtator3.gz</a>    2024-01-23 06:49  245M

We look for the <a> </a> instance that matches the file pattern we care about and then
get the next sibling to extract the version date
"""

# pylint: disable=import-outside-toplevel, no-name-in-module


