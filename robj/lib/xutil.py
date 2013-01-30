#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""
XObj utilities.
"""

from xobj import xobj

def XObjify(d, tag):
    if not isinstance(d, dict):
        raise TypeError, 'dictionary required'

    class Model(object):
        _xobj = xobj.XObjMetadata(tag=tag)

    top = Model()
    for key, value in sorted(d.iteritems()):
        if isinstance(value, dict):
            value = XObjify(value, key)
        setattr(top, key, value)

    return top
