#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os
from simpleconverter import convert

if __name__ == "__main__":
    params = [os.path.realpath(p) for p in sys.argv[1:]]
    convert(*params)

