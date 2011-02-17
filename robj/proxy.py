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

from robj.lib import xutil
from robj.lib.httputil import HTTPData as _HTTPData
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

    HTTPData = _HTTPData

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
        self._tag = self._root._xobj.tag

        if self._tag is None:
            raise RuntimeError, ('No XML tag found for this object, please '
                'make sure you are using the latest verison of xobj.')

        # Colleciton related attributes
        self._childTag = None
        self._isCollection = False

        self._reset()

    def _reset(self):
        self._local_cache = {}
        self._dirty_flag = False

        # Infer from tag names if this is intended to be a collection. Yes, this
        # is a hack, find a better way.

        ##
        # How to guess if something is a collection:
        # 1. Top level tag name ends in 's' and number of elements is 0 or 1 and
        #    if 1 sub element is same as top level tag without the 's'.
        # 2. Number of elements is 1.
        # 3. Number of reoccuring elements is 1. In xobj this would mean that
        #    the attribute is a list.
        # 4. No reoccuring elements, but there is an element that matches the
        #    same pattern as #1.
        ##

        if self._tag.endswith('s') and len(self.elements) == 0:
            self._childTag = self._tag[:-1]
        elif len(self.elements) == 1:
            self._childTag = self.elements[0]
            self._isCollection = True
        else:
            lists = [ x for x in self.elements
                if isinstance(getattr(self._root, x, None), list) ]
            if len(lists) == 1:
                self._childTag = lists[0]
                self._isCollection = True
            elif self._tag[:-1] in self.elements:
                self._childTag = self._tag[:-1]


        # If child element is defined and is not a list already, make
        # it one.
        if self._childTag:
            collection = getattr(self._root, self._childTag, [])
            if not isinstance(collection, list):
                setattr(self._root, self._childTag, [collection, ])
                self._isCollection = True

    def _set_dirty(self, value):
        if self._isChild:
            self._parent._dirty_flag = value
        self._dirty_flag = value
    def _get_dirty(self):
        return self._dirty_flag
    _dirty = property(_get_dirty, _set_dirty)

    @property
    def _collection(self):
        if self._childTag is None:
            raise ValueError, 'child tag must be defined'
        if not hasattr(self, self._childTag):
            setattr(self._root, self._childTag, list())
            self._isCollection = True
        return getattr(self._root, self._childTag)

    @property
    def _isChild(self):
        if self._parent and self._uri == self._parent._uri:
            return True
        return False

    @property
    def elements(self):
        return sorted(self._root._xobj.elements)

    @property
    def attributes(self):
        return sorted(self._root._xobj.attributes.keys())

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
            return self._client.cache(self._client, value.id, value,
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
            valueId = id(value)
            if valueId not in self._local_cache:
                self._local_cache[valueId] = self.__class__(self._uri,
                    self._client, value, parent=self)
            return self._local_cache[valueId]

        # Return an already cached instance if it got there through some
        # other means.
        elif hasattr(value, '_xobj') and id(value) in self._local_cache:
            return self._local_cache[id(value)]

        # Unwrap the list that rObj created since it has not way to tell the
        # difference between a element with a single sub element and a
        # collection.
        elif isinstance(value, list) and len(value) == 1:
            return self._getObj(name, value[0])

        return None

    def _setObj(self, obj, name, value):
        if hasattr(obj, 'href'):
            self._client.do_PUT(obj.href, value)
        elif hasattr(obj, 'id'):
            raise RemoteInstanceOverwriteError(
                name=name, uri=self._uri, id=obj.id)
        elif value == [] and hasattr(obj, '_xobj'):
            valueId = id(obj)
            if valueId not in self._local_cache:
                self._local_cache[valueId] = self.__class__(self._uri,
                    self._client, obj, parent=self)
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
            # Convert dictionaries to XObj instances.
            if isinstance(value, dict):
                value = xutil.XObjify(value, name)

            self._dl.acquire()
            if hasattr(self._root, name):
                val = getattr(self._root, name)
                if not self._setObj(val, name, value):
                    self._dirty = True
                    setattr(self._root, name, value)
            else:
                self._dirty = True

                if isinstance(value, list) and len(value) == 0:
                    value = self.__class__(self._uri, self._client,
                        xutil.XObjify(dict(), name), parent=self)

                self._root._xobj.elements.append(name)
                setattr(self._root, name, value)
            self._dl.release()
        else:
            object.__setattr__(self, name, value)

    @require_collection
    def __getitem__(self, idx):
        if not isinstance(idx, int):
            raise TypeError, 'index is required to be an interger'

        val = self._collection[idx]
        obj = self._getObj(self._childTag, val)
        if obj:
            return obj
        else:
            return val

    @require_collection
    def __setitem__(self, idx, value):
        if not isinstance(idx, int):
            raise TypeError, 'index is required to be an interger'

        # Make sure the current value isn't an instance.
        self._dl.acquire()
        val = self._collection.get(idx)
        if hasattr(val, 'id') or hasattr(val, 'href'):
            raise RemoteInstanceOverwriteError(name=idx, uri=self._uri,
                id=hasattr(val, 'id') and val.id or val.href)

        # Convert dictionaries to XObj instances.
        if isinstance(value, dict):
            value = xutil.XObjify(value, self._childTag)

        self._collection[idx] = value
        self._dl.release()

    @require_collection
    def __delitem__(self, idx):
        if not isinstance(idx, int):
            raise TypeError, 'index is required to be an interger'

        self._dl.acquire()
        val = self[idx]
        if isinstance(val, self.__class__):
            val.delete()
        elif hasattr(val, 'id'):
            self._client.do_DELETE(val.id)
        del self._collection[idx]
        self._dl.release()

    @require_collection
    def __iter__(self):
        self._dl.acquire()
        for i in range(len(self._collection)):
            yield self[i]
        self._dl.release()

    @require_collection
    def __len__(self):
        self._dl.acquire()
        l = len(self._collection)
        self._dl.release()
        return l

    def append(self, value, post=True, tag=None):
        """
        Append a value to a collection.
        @param value: Object to append to the collection.
        @type value: xobj.XObj, str, unicode, or dict
        @param post: Optional argument to avoid POSTing the value at the time
                     that it is appended. If this is set to False the collection
                     must be later persisted. (default: True)
        @type post: boolean
        @param tag: Optional tag to use as the xml element tag for the object
                    being appended. This has the side effect of changing the
                    default childTag for the collection.
        @type tag: str
        """

        if tag:
            self._childTag = tag

        # Convert dictionaries to XObj instances.
        if isinstance(value, dict):
            value = xutil.XObjify(value, self._childTag)

        if post:
            obj = self._client.do_POST(self._uri, value)
            self._collection.append(obj._root)
        else:
            self._collection.append(value)
            self._dirty_flag = True

    def persist(self, force=False):
        """
        Update the server with any modifications that have been made to this
        instance.
        @param force: Optional parameter (defaults to False) to force the
                      refresh even if the instance has been modified locally.
        @type force: boolean
        """

        if self._dirty or force:
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

            # Must mark instance as clean before PUTing contents, otherwise
            # instance cache will not inject the new model.
            self._dirty_flag = False

            self._client.do_GET(self._uri, cache=False)
            self._dl.release()
