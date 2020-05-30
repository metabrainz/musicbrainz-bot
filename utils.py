# -*- coding: utf-8 -*-
from __future__ import print_function

import locale
import sys
import os


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    NONE = ""


def colored_out(color, *args):
    args = [unicode(a).encode(locale.getpreferredencoding()) for a in args]
    sys.stdout.write(color + " ".join(args) + bcolors.ENDC + "\n")
    sys.stdout.flush()


def get_page_content_from_cache(title, wp_lang):
    key = title.encode("utf-8", "xmlcharrefreplace").replace("/", "_")
    file = os.path.join("wiki-cache", wp_lang, key[0], key)
    if os.path.exists(file):
        return open(file).read().decode("utf8")
