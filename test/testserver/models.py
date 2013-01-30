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

class AbstractModel(object):
    __tag__ = None
    __elements__ = ()
    __attributes__ = ()

    def __init__(self):
        self._xobj = xobj.XObjMetadata()

        for cls in self.__class__.__mro__:
            for element in getattr(cls, '__elements__', ()):
                if element not in self._xobj.elements:
                    self._xobj.elements.append(element)
            for attribute in getattr(cls, '__attributes__', ()):
                if attribute not in self._xobj.attributes:
                    self._xobj.attributes[attribute] = None

        self._xobj.tag = self.__tag__


class AbstractCollection(AbstractModel):
    __tag__ = None
    __attributes__ = ('id', )


class Reference(AbstractModel):
    __attributes__ = ('href', )

    href = str


class ProductsRef(Reference):
    __tag__ = 'products'


class EmployeesRef(Reference):
    __tag__ = 'employees'


class File(Reference):
    __tag__ = 'file'


class Address(AbstractModel):
    __elements__ = ('street', 'city', 'state', 'zipcode', )
    __tag__ = 'address'

    street = str
    city = str
    state = str
    zipcode = str


class Product(AbstractModel):
    __attributes__ = ('id', )
    __elements__ = ('name', 'productcode', 'productsite', 'employees',
        'productid')
    __tag__ = 'product'

    name = str
    productcode = str
    productsite = str
    productid = int
    employees = EmployeesRef


class Employee(AbstractModel):
    __attributes__ = ('id', )
    __elements__ = ('name', 'address', 'phone', 'products', 'employeeid')
    __tag__ = 'employee'

    name = str
    address = Address
    phone = str
    products = ProductsRef
    employid = int
    file = File


class Api(AbstractModel):
    __attributes__ = ('id', )
    __elements__ = ('employees', 'products', 'version', )
    __tag__ = 'api'

    employees = EmployeesRef
    products = ProductsRef
    version = str


class Products(AbstractCollection):
    __tag__ = 'products'
    products = [ Product, ]


class Employees(AbstractCollection):
    __tag__ = 'employees'
    employees = [ Employee, ]
