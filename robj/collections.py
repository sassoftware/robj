#
# Copyright (c) 2011 rPath, Inc.
#
# This program is distributed under the terms of the MIT License as found 
# in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/mit-license.php.
#
# This program is distributed in the hope that it will be useful, but
# without any waranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the MIT License for full details.
#

"""
Module for describing RESTful collections.
"""

from robj.proxy import rObjProxy

class Pages(dict):
    def insert(self, page):
        self.first = page
        self.last = page
        self[page.index] = page

    def iterkeys(self):
        num_pages = self.last.num_pages

        i = 0
        while i < num_pages:
            yield i
            i += 1

    def iteritems(self):
        for k in sorted(self.iterkeys()):
            yield k, self.get(k)

    def itervalues(self):
        for k, v in self.iteritems():
            yield v

    def get(self, idx):
        if idx in self:
            return self[idx]

        cur = None
        score = None
        direction = 0

        for i in self:
            newScore = i < idx and idx - i or i - idx
            if score is None or newScore < score:
                cur = i
                score = newScore
                direction = i < idx and 1 or -1

        page = self[cur]

        if direction:
            while page.index != idx:
                page = page.next_page
        else:
            while page.index != idx:
                page = page.previous_page

        return page


class Page(object):
    __slots__ = ('node', '_pages', '_prev', '_next', )

    def __init__(self, node, pages):
        self.node = node
        self._pages = pages

        self._prev = None
        self._next = None

    def __hash__(self):
        return hash(self.index)

    def __cmp__(self, other):
        return cmp(self.index, other.index)

    @property
    def index(self):
        return self.end_index / self.per_page

    @property
    def id(self):
        return self.node.id

    @property
    def start_index(self):
        return int(self.node.start_index)

    @property
    def end_index(self):
        return int(self.node.end_index)

    @property
    def per_page(self):
        return int(self.node.per_page)

    @property
    def limit(self):
        return int(self.node.limit)

    @property
    def count(self):
        return int(self.node.count)

    @property
    def num_pages(self):
        return int(self.node.num_pages)

    def _get_page(self, uri):
        if uri == '':
            return None

        cls = self.__class__
        node = self.node._client.do_GET(uri, parent=self.node)
        page = cls(node, self._pages)
        self._pages.insert(page)
        return page

    @property
    def next_page(self):
        if self._next:
            return self._next

        uri = self.node.next_page
        page = self._get_page(uri)

        self._next = page
        return page

    @property
    def previous_page(self):
        if self._prev:
            return self._prev

        uri = self.node.previous_page
        page = self._get_page(uri)

        self._prev = page
        return page


class PagedCollection(object):
    __slots__ = ('_pages', '_full_id', '_new_items', '_uri',
        '_write_node', )

    def __init__(self, node):
        self._pages = Pages()
        self._pages.insert(Page(node, self._pages))

        self._full_id = node._client._normalize_uri(node.full_collection)
        self._new_items = []

        self._uri = node._uri
        self._write_node = None

    @property
    def id(self):
        return self._full_id

    @property
    def _node(self):
        if not self._write_node:
            self._write_node = rObjProxy(self._uri,
                self._pages.first.node._client,
                self._pages.first.node._root)
        return self._write_node

    def __repr__(self):
        return '<robj.PagedCollection(%s)>' % self.id

    __str__ = __repr__

    def __len__(self):
        return self._pages.last.count

    def __nonzero__(self):
        return bool(len(self))

    def _get_page(self, idx):
        pageNum = idx / self._pages.last.limit
        pageIdx = idx % self._pages.last.limit
        page = self._pages.get(pageNum)

        return page, pageIdx

    def __getitem__(self, idx):
        page, idx = self._get_page(idx)
        return page.node[idx]

    def __setitem__(self, idx, value):
        page, idx = self._get_page(idx)
        page.node[idx] = value

    def __delitem__(self, idx):
        page, idx = self._get_page(idx)
        del page.node[idx]

    def __iter__(self):
        seen = set()
        for p in self._pages.itervalues():
            for i in p.node:
                if i.id in seen:
                    continue
                yield i
                seen.add(i.id)

    def append(self, item, post=True, tag=None):
        node = self._node.append(item, post=post, tag=tag)
        self._new_items.append(node)
        return node

    @staticmethod
    def isPaged(node):
        attrs = set(node.elements + node.attributes)
        required_attrs = set([
            'count',
            'limit',
            'per_page',
            'num_pages',
            'next_page',
            'previous_page',
            'start_index',
            'end_index',
        ])

        # Make sure all required attrs are available.
        if required_attrs.difference(attrs):
            return False

        if not getattr(node, 'full_collection', None):
            return False

        return True

    @classmethod
    def isSiblingNode(cls, a, b):
        if not a or not b:
            return False
        if not cls.isPaged(a):
            return False
        if not cls.isPaged(b):
            return False

        if a.full_collection == b.full_collection:
            return True
        return False
