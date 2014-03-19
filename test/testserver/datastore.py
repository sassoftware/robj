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


from xobj import xobj

from testserver import models

class AttrDict(dict):
    def __getattr__(self, attr):
        if attr.startswith('_'):
            return dict.__getattr__(self, attr)
        else:
            return self.__getitem__(attr)

    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            return dict.__setattr__(self, attr, value)
        else:
            return self.__setitem__(attr, value)


class AbstractModelCollection(dict):
    def _nextId(self):
        if not self:
            return 0
        else:
            return max(self) + 1

    def parse(self, xml):
        raise NotImplementedError

    def create(self, xml, uri):
        raise NotImplementedError

    def update(self, idx, xml):
        raise NotImplementedError

    def delete(self, idx):
        raise NotImplementedError


class Employees(AbstractModelCollection):
    def __init__(self):
        AbstractModelCollection.__init__(self)
        self.files = AttrDict()
        self.productRefs = AttrDict()

    def parse(self, xml):
        class Doc(xobj.Document):
            employee = models.Employee
        doc = xobj.parse(xml, documentClass=Doc)
        return doc.employee

    def create(self, xml, uri):
        uri = uri.rstrip('/')
        model = self.parse(xml)

        if getattr(model, 'employeeid', None):
            return self[model.employeeid]

        model.employeeid = self._nextId()
        model.id = '%s/%s' % (uri, model.employeeid)
        model.products = models.ProductsRef()
        model.products.href = '%s/products' % model.id
        model.file = models.File()
        model.file.href = '%s/file' % model.id

        self[model.employeeid] = model
        self.productRefs[model.employeeid] = []
        return model

    def update(self, idx, xml):
        newModel = self.parse(xml)
        oldModel = self[idx]

        immutable = ('employid', 'id')
        for attr in models.Employee.__elements__:
            if attr in immutable:
                continue

            value = getattr(newModel, attr, None)
            if value is not None:
                setattr(oldModel, attr, value)

        return oldModel

    def delete(self, idx):
        self.pop(idx, None)
        self.productRefs.pop(idx, None)
        self.files.pop(idx, None)


class Products(AbstractModelCollection):
    def __init__(self):
        AbstractModelCollection.__init__(self)
        self.employeeRefs = AttrDict()

    def parse(self, xml):
        class Doc(xobj.Document):
            product = models.Product
        doc = xobj.parse(xml, documentClass=Doc)
        return doc.product

    def create(self, xml, uri):
        uri = uri.rstrip('/')
        model = self.parse(xml)

        if getattr(model, 'productid', None):
            return self[model.productid]

        model.productid = self._nextId()
        model.id = '%s/%s' % (uri, model.productid)
        model.employees = models.EmployeesRef()
        model.employees.href = '%s/employees' % model.id

        self[model.productid] = model
        self.employeeRefs[model.productid] = []
        return model

    def update(self, idx, xml):
        newModel = self.parse(xml)
        oldModel = self[idx]

        immutable = ('productid', 'id')
        for attr in models.Product.__elements__:
            if attr in immutable:
                continue

            value = getattr(newModel, attr, None)
            if value is not None:
                setattr(oldModel, attr, value)

        return oldModel

    def delete(self, idx):
        self.pop(idx)
        self.employeeRefs.pop(idx)


class DataStore(object):
    def __init__(self):
        self.employees = Employees()
        self.products = Products()
