import os
import sys
PY3 = sys.version_info.major >= 3

try:
    string_types = (str, unicode)
except NameError:
    string_types = str

try:
    from subprocess import DEVNULL 
except ImportError:
    DEVNULL = open(os.devnull, "wb")
