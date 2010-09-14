#
# Copyright (c) 2010 rPath, Inc.
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
Module for implementing rObj classes.
"""

from threading import RLock

from robj.errors import ExternalUriError
from robj.errors import RemoteInstanceOverwriteError

def require_collection(func):
    def wrapper(self, *args, **kwargs):
        if not self._isCollection:
            raise TypeError, 'A list type is required for this method.'
        return func(self, *args, **kwargs)
    return wrapper


class rObjProxy(object):
    """
    REST object proxy class.
    @param uri: URI that identifies this instance.
    @type uri: str
    @param client: Instance of a glue client.
    @type client: robj.glue.HTTPClient
    @param root: XObj object tree.
    @type root: xobj.xobj.XObj
    @param parent: Parent rObj instance (optional).
    @type parent: robj.proxy.rObjProxy
    """

    __slots__ = ('_uri', '_client', '_root', '_parent', '_tag', '_isCollection',
        '_dirty_flag', '_dl', '_childTag', '_local_cache')

    def __init__(self, uri, client, root, parent=None):
        self._uri = uri
        self._client = client
        self._root = root

        if parent is not None:
            self._parent = parent
        else:
            self._parent = None

        self._dl = RLock()
        self._dirty_flag = False
        self._tag = self._root._xobj.tag

        self._local_cache = {}

        # Colleciton related attributes
        self._childTag = ''
        self._isCollection = False

        # Infer from tag names if this is intended to be a collection. Yes, this
        # is a hack, find a better way.
        if self._tag and self._tag.endswith('s'):
            elements = self._root._xobj.elements
            if (len(elements) == 1 and self._tag[:-1] in elements):
                element = getattr(self._root, self._tag[:-1])
                if not isinstance(element, list):
                    setattr(self._root, self._tag[:-1], [element, ])
                self._childTag = self._tag[:-1]
                self._isCollection = True
        elif isinstance(self._root, list):
            self._isCollection = True

    def _set_dirty(self, value):
        if self._isChild:
            self._parent._dirty_flag = value
        self._dirty_flag = value
    def _get_dirty(self):
        return self._dirty_flag
    _dirty = property(_get_dirty, _set_dirty)

    @property
    def _isChild(self):
        if self._parent and self._uri == self._parent._uri:
            return True
        return False

    @property
    def elements(self):
        return self._root._xobj.elements

    @property
    def attributes(self):
        return self._root._xobj.attributes.keys()

    def __dir__(self):
        elements = self._root._xobj.elements
        attributes = self._root._xobj.attributes.keys()
        return list(elements + attributes)

    def __repr__(self):
        return '<robj.rObj(%s)>' % self._tag

    __str__ = __repr__

    def __nonzero__(self):
        if self._root._xobj.elements:
            return True
        else:
            return bool(self._root)

    def _getObj(self, name, value):
        # Wrap this instance with an rObj.
        if hasattr(value, 'id'):
            return self._client.cache(value.id, self._client, value,
                parent=self)

        # Get the instance pointed to by the href.
        elif hasattr(value, 'href'):
            try:
                obj = self._client.do_GET(value.href, parent=self)
            except ExternalUriError:
                return value.href
            return obj

        # Wrap anything that has elements in an rObj.
        elif hasattr(value, '_xobj') and value._xobj.elements:
            if name not in self._local_cache:
                self._local_cache[name] = self.__class__(self._uri,
                    self._client, value, parent=self)
            return self._local_cache[name]

        return None

    def _setObj(self, obj, name, value):
        if hasattr(obj, 'href'):
            self._client.do_POST(obj.href, value)
        elif hasattr(obj, 'id'):
            raise RemoteInstanceOverwriteError(
                name=name, uri=self._uri, id=obj.id)
        else:
            return False
        return True

    def __getattr__(self, name):
        try:
            val = getattr(self._root, name)
        except AttributeError:
            raise AttributeError, "'%r' has no attribute '%s'" % (self, name)
        obj = self._getObj(name, val)
        if obj is not None:
            return obj
        else:
            return val

    def __setattr__(self, name, value):
        if not name.startswith('_'):
            self._dl.acquire()
            if hasattr(self._root, name):
                val = getattr(self._root, name)
                if not self._setObj(val, name, value):
                    self._dirty = True
                    setattr(self._root, name, value)
            else:
                self._dirty = True
                setattr(self._root, name, value)
            self._dl.release()
        else:
            object.__setattr__(self, name, value)

    @require_collection
    def __getitem__(self, idx):
        assert isinstance(idx, int), 'index is required to be an interger'

        val = self._root[idx]
        obj = self._getObj(self._childTag, val)
        if obj:
            return obj
        else:
            return val

    @require_collection
    def __setitem__(self, idx, value):
        assert isinstance(idx, int), 'index is required to be an interger'

        # Make sure the current value isn't an instance.
        self._dl.acquire()
        val = self._root.get(idx)
        if hasattr(val, 'id') or hasattr(val, 'href'):
            raise RemoteInstanceOverwriteError(name=idx, uri=self._uri,
                id=hasattr(val, 'id') and val.id or val.href)

        self._root[idx] = value
        self._dl.release()

    @require_collection
    def __delitem__(self, idx):
        assert isinstance(idx, int), 'index is required to be an interger'

        self._dl.acquire()
        val = self._root.get(idx)
        if isinstance(val, self.__class__):
            val.delete()
        elif hasattr(val, 'id'):
            self._client.do_DELETE(val.id)
        else:
            del self._root[idx]
        self._dl.release()

    @require_collection
    def __iter__(self):
        self._dl.acquire()
        for i in range(len(self._root)):
            yield self[i]
        self._dl.release()

    @require_collection
    def __len__(self):
        self._dl.acquire()
        l = len(self._root)
        self._dl.release()
        return l

    @require_collection
    def append(self, value):
        obj = self._client.do_POST(self._uri, value)
        self._root.append(obj._root)

    def persist(self):
        """
        Update the server with any modifications that have been made to this
        instance.
        """

        if self._dirty:
            self._dl.acquire()

            # Must mark instance as clean before PUTing contents, otherwise
            # instance cache will not inject the new model.
            self._dirty_flag = False

            if self._isChild:
                self._parent.persist()
            else:
                self._client.do_PUT(self._uri, self._root)
            self._dl.release()
        else:
            self.refresh()

    def delete(self):
        """
        Delete this instance from the server.
        """

        self._client.do_DELETE(self._uri)

    def refresh(self, force=False):
        """
        Refresh the instance from the server if it has not been modified.
        @param force: Optional parameter (defaults to False) to force the
                      refresh even if the instance has been modified locally.
        @type force: boolean
        """

        if not self._dirty or force:
            self._dl.acquire()
            self._dirty = False
            self._client.do_GET(self._uri, cache=False)
            self._dl.release()
