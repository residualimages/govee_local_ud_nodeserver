#!/usr/bin/env python3
"""
Polyglot v3 node server Example 2
Copyright (C) 2021 Robert Paauwe

MIT License
"""
import udi_interface
import sys
import time
import string
import re

from nodes import govee_local_controller

# Standard Library
from typing import Optional, Any, TYPE_CHECKING

import math,datetime,urllib.parse,http.client,base64

LOGGER = udi_interface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start()

        # Create the controller node
        govee_local_controller.Controller(polyglot, 'controller', 'controller', 'Counter')

        # Just sit and wait for events
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

