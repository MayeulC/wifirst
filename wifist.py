#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# The MIT License (MIT)
#
# Copyright (c) 2014 Jean Dupouy
# Copyright (c) 2018 Mayeul Cantan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
A simple script to reconnect to Wifirst.

Copyright (c) 2014 Jean Dupouy
Copyright (c) 2018 Mayeul Cantan
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse
import logging
import signal
import sys
import time
import http.client

__author__ = "Jean Dupouy"
__version__ = "0.2.0"

url_test = "http://example.com/"


signal.signal(signal.SIGINT, lambda s, f: sys.exit())

logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    logger.addHandler(logging.StreamHandler())

session = requests.Session()


def main(login, password, delay):
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    while 1:
        test_request = session.get(url_test)
        if test_request.url == url_test:
            logger.info("Wifirst is not blocking the connection.")
        else:
            logger.info(("Wifirst is blocking the connection! ",
                         "Trying to reconnect..."))
            reconnect(test_request, login, password)

        logger.debug("Trying again in %ss.", delay)
        time.sleep(delay)


def reconnect(test_request, login, password):
    # First, get the URL of the redirection. After querying our test page, we
    # get a 302, then a page with a meta-tag redirection
    soup = BeautifulSoup(test_request.text, "lxml")
    meta = soup.find("meta", attrs={'http-equiv': 'refresh'})['content']
    url_perform = meta[meta.find("URL=")+4:]

    # Once we get the URL, we load it, and store the cookies. The cookie
    # storage is handled by the session. We then need a CSRF (or whatever it is
    # used for) token from a pre-filled, invisible field in the login form.
    # We also extract the submit URL from the form
    perform_request = session.get(url_perform)
    soup = BeautifulSoup(perform_request.text, "lxml")
    token = soup.find(attrs={"name": "authenticity_token"})['value']

    data = {'utf8': '✓',
            'authenticity_token': token,
            'login': login,
            'password': password
            }
    urlpart = soup.find("form", attrs={"id": "signin-form"})['action']
    url_session = urljoin(perform_request.url, urlpart)
    session_request = session.post(url_session, data=data)

    # After "logging in", we are given a new username/password combo with which
    # to authenticate on the local gateway, prefilled in a form which is
    # normally automatically submitted. We just need to find the submission URL
    # and post the input fields there (except for the input button)
    soup = BeautifulSoup(session_request.text, "lxml")
    url_login = soup.find("form")['action']
    data = dict()  # will contain the form data/name combos
    for input_field in soup.find("form").find_all("input"):
        if (input_field["type"] == "hidden" and
                input_field.get('id') is not None):  # Filter the button
            data[input_field['id']] = input_field['value']
    # We should be logged in after the next step. If not, this function will be
    # called again next time the connection status is checked.
    session.post(url_login, data=data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="A simple script to reconnect to Wifirst.")
    parser.add_argument('login', help='your Wifirst login (e-mail address)')
    parser.add_argument('password', help='your Wifirst password')
    parser.add_argument(
            '-v', '--verbose', action='count', help='make me say stuff')
    parser.add_argument(
            '-d', '--delay', type=int, default=10,
            help='delay between attempts, in seconds (default: 10)')

    args = parser.parse_args()

    if args.verbose is None:
        logging.getLogger("requests").setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.DEBUG)
        if args.verbose > 1:
            http.client.HTTPConnection.debuglevel = 1

    main(args.login, args.password, args.delay)
