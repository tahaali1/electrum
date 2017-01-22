# Electrum - Lightweight Bitcoin Client
# Copyright (c) 2015 Thomas Voegtlin
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import six

import sys
import re
import dns
import os
import json

from . import bitcoin
from . import dnssec
from .util import print_error
from .i18n import _


class Contacts(dict):

    def __init__(self, storage):
        self.storage = storage
        d = self.storage.get('contacts', {})
        try:
            self.update(d)
        except:
            return
        # backward compatibility
        for k, v in self.items():
            _type, n = v
            if _type == 'address' and bitcoin.is_address(n):
                self.pop(k)
                self[n] = ('address', k)

    def save(self):
        self.storage.put('contacts', dict(self))

    def import_file(self, path):
        try:
            with open(path, 'r') as f:
                d = self._validate(json.loads(f.read()))
        except:
            return
        self.update(d)
        self.save()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.save()

    def pop(self, key):
        if key in self.keys():
            dict.pop(self, key)
            self.save()

    def resolve(self, k):
        if bitcoin.is_address(k):
            return {
                'address': k,
                'type': 'address'
            }
        if k in self.keys():
            _type, addr = self[k]
            if _type == 'address':
                return {
                    'address': addr,
                    'type': 'contact'
                }
        out = self.resolve_openalias(k)
        if out:
            address, name, validated = out
            return {
                'address': address,
                'name': name,
                'type': 'openalias',
                'validated': validated
            }
        raise Exception("Invalid Bitcoin address or alias", k)

    def resolve_openalias(self, url):
        # support email-style addresses, per the OA standard
        url = url.replace('@', '.')
        records, validated = dnssec.query(url, dns.rdatatype.TXT)
        prefix = 'btc'
        for record in records:
            string = record.strings[0]
            if string.startswith('oa1:' + prefix):
                address = self.find_regex(string, r'recipient_address=([A-Za-z0-9]+)')
                name = self.find_regex(string, r'recipient_name=([^;]+)')
                if not name:
                    name = address
                if not address:
                    continue
                return address, name, validated

    def find_regex(self, haystack, needle):
        regex = re.compile(needle)
        try:
            return regex.search(haystack).groups()[0]
        except AttributeError:
            return None
            
    def _validate(self, data):
        for k,v in data.items():
            if k == 'contacts':
                return self._validate(v)
            if not bitcoin.is_address(k):
                data.pop(k)
            else:
                _type,_ = v
                if _type != 'address':
                    data.pop(k)
        return data

