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

        self[model.employeeid] = model
        self.productRefs[model.employeeid] = []
        return model

    def update(self, idx, xml):
        newModel = self.parse(xml)
        oldModel = self.idx

        immutable = ('employid', 'id')
        for attr in models.Employee._xobj.elements:
            if attr in immutable:
                continue

            value = getattr(newModel, attr, None)
            if value is not None:
                setattr(oldModel, attr, value)

        return oldModel

    def delete(self, idx):
        self.pop(idx)
        self.productRefs.pop(idx)


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
        uri = uri.strip('/')
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
        oldModel = self.idx

        immutable = ('productid', 'id')
        for attr in models.Product._xobj.elements:
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
