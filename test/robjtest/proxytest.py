#!/usr/bin/python
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

import testsuite
testsuite.setup()

from xobj import xobj

from robj.glue import HTTPClient
from robj.proxy import rObjProxy

class rObjProxyTest(testsuite.TestCase):
    def setUp(self):
        testsuite.TestCase.setUp(self)
        self.client = HTTPClient(self.server.geturi('/api'))
        self.api = self.client.do_GET('/')

    def POST(self, archiveFileName, uri):
        xml = self.getArchiveContents(archiveFileName)
        doc = xobj.parse(xml)
        return self.client.do_POST(uri, doc)

    def testSimpleGetAttr(self):
        model = self.getModel('/api')
        self.failUnlessEqual(self.api.version, model.version)

        employees = self.api.employees
        self.failUnless(isinstance(employees, rObjProxy))

        # Nothing should be marked as a collection since all collections are
        # empty and we don't have a way of knowing something is a collection if
        # it is empty.
        self.failIf(self.api._isCollection)
        self.failIf(employees._isCollection)
        self.failIf(self.api.products._isCollection)

    def testGetAttributeError(self):
        try:
            self.api.foo
        except AttributeError, e:
            # Make sure an rObj attribute error is raised rather than the
            # attribute error from the internal xobj.
            self.failUnlessEqual(e.args[0],
                "'<robj.rObj(api)>' has no attribute 'foo'")

    def testSimpleSetAttr(self):
        # First need a resource that can be modified.
        employee = self.POST('employee1.xml', '/api/employees')

        # Set a simple attribute
        employee.name = 'Joe Trumbo'

        # Persist this resource on the server.
        employee.persist()

        # ensure that the name change made it to the server.
        self.failUnlessEqual('Joe Trumbo', self.getModel(employee.id).name)

    def testSubSetAttr(self):
        # First need a resource that can be modified.
        employee = self.POST('employee2.xml', '/api/employees')

        # Set a sub element of employee
        employee.address.zipcode = '90210'

        # Make sure the same instance is always returned.
        self.failUnless(employee.address is employee.address)

        # Make sure all objects in the tree were marked as dirty since an
        # address is not a resource itself, it requres modifications to the
        # employee resource.
        self.failUnless(employee._dirty_flag)
        self.failUnless(employee.address._dirty_flag)

        # Persist to the server
        address = employee.address
        address.persist()

        self.failUnlessEqual('90210',
            self.getModel(employee.id).address.zipcode)

        # Once an instance has been persisted to or refreshed from the server
        # any attributes of that instancee are invalidated. In this case
        # persisting address caused employee to be persisted, thus invalidating
        # the address instance.
        self.failIf(address is employee.address)

    def testDelete(self):
        # First need a resource that can be modified.
        employee = self.POST('employee2.xml', '/api/employees')

        # Make sure model is represented on the server.
        self.failUnlessEqual(employee.employeeid,
            str(self.getModel(employee.id).employeeid))

        # Delete instance.
        employee.delete()

        # Make sure model is no longer represented on the server.
        self.failIf(employee.id in self.server.data.employees)

        # What happens if an instance is deleted twice? The server returns a 404
        # and rObj ignores the response.
        employee.delete()

    def testSubDelete(self):
        # First need a resource that can be modified.
        employee = self.POST('employee2.xml', '/api/employees')

        # Try to delete from a sub-element. This should delete the parent since
        # they have have the same URI.
        employee.address.delete()

        # Check the server to make sure the instance is gone.
        self.failIf(employee.id in self.server.data.employees)

    def testRefresh(self):
        # First need a resource that can be modified.
        employee = self.POST('employee2.xml', '/api/employees')

        # A unmodified isntance should get a new instance when refreshed.
        root = employee._root
        employee.refresh()
        self.failIf(root is employee._root)

        # A modified instance should not get a new instance.
        root = employee._root
        employee.name = 'George'
        employee.refresh()
        self.failUnless(root is employee._root)

        # unless it is forced
        employee.refresh(force=True)
        self.failIf(root is employee._root)

        # Now check to make sure the local cache is cleared properly on refresh.
        address = employee.address
        employee.refresh()
        self.failIf(address is employee.address)

        # The cache should not be cleared if the xobj instance is not replaced.
        employee.name = 'Fred'
        address = employee.address
        employee.refresh()
        self.failUnless(address is employee.address)


class CollectionTest(testsuite.TestCase):
    def setUp(self):
        testsuite.TestCase.setUp(self)
        self.client = HTTPClient(self.server.geturi('/api'))
        self.api = self.client.do_GET('/')

    def POST(self, archiveFileName, uri):
        xml = self.getArchiveContents(archiveFileName)
        doc = xobj.parse(xml)
        return self.client.do_POST(uri, doc)

    def getArchiveModel(self, archiveFileName):
        xml = self.getArchiveContents(archiveFileName)
        doc = xobj.parse(xml)
        return getattr(doc, doc._xobj.elements[0])

    def testCreateCollection(self):
        employees = self.api.employees

        # Since there aren't any memerbers of the collection, rObj has no way of
        # knowing that this a colleciton.
        self.failIf(employees._isCollection)
        self.failUnlessEqual(employees._childTag, 'employee')

        # Another client, out of band, comes along and adds some employees to
        # the collection.
        self.POST('employee1.xml', '/api/employees')
        self.POST('employee2.xml', '/api/employees')

        employees.refresh()

        # After adding elements to the collection and refreshing, the instance
        # should now be marked as a collection.
        self.failUnless(employees._isCollection)
        self.failUnlessEqual(employees._childTag, 'employee')

    def testCreateCollection2(self):
        # Start with an empty collection.
        employees = self.api.employees

        self.failUnlessEqual(employees._childTag, 'employee')
        self.failIf(employees._isCollection)
        self.failUnlessEqual(len(employees._collection), 0)
        self.failUnless(employees._isCollection)

        employee1 = self.getArchiveModel('employee1.xml')
        employees.append(employee1)

        self.failUnlessEqual(len(employees), 1)

        # Appending POSTs the model to the server and adds the result to the
        # collection. The collection should not be marked as dirty, since there
        # are no pending changes. In fact, collections should never be dirty.
        self.failIf(employees._dirty)

    def testAccessCollection(self):
        employees = self.api.employees
        employees.append(self.getArchiveModel('employee1.xml'))
        employees.append(self.getArchiveModel('employee2.xml'))

        # Order is subject to change after a refresh. Indexes are not stable.
        employee1 = employees[0]
        employee2 = employees[1]

        # Make sure they are different
        self.failIf(employee1 is employee2)

    def testSetItem(self):
        # I don't really have a good case for __setitem__ needing to work. You
        # can't replace an item in a collection if it has an id or an href. To
        # remove something from a collection you would delete the individual
        # instance.

        raise testsuite.SkipTestException, ('Need to come up with a use case'
            ' for __setitem__')

    def testDeleteItem(self):
        employees = self.api.employees
        employees.append(self.getArchiveModel('employee1.xml'))
        employees.append(self.getArchiveModel('employee2.xml'))

        del employees[0]
        self.failUnlessEqual(len(employees), 1)

        del employees[0]
        self.failUnlessEqual(len(employees), 0)

    def testIter(self):
        employees = self.api.employees
        employees.append(self.getArchiveModel('employee1.xml'))
        employees.append(self.getArchiveModel('employee2.xml'))
        employees.append(self.getArchiveModel('employee3.xml'))

        empl = set()
        for e in employees:
            empl.add(e.employeeid)

        self.failUnlessEqual(len(empl), 3)

    def testSingleItemList(self):
        employees = self.api.employees
        employees.append(self.getArchiveModel('employee1.xml'))
        employees.refresh()

        self.failUnless(employees._isCollection)
        self.failUnlessEqual(employees._childTag, 'employee')

        employee1 = employees[0]
        model = self.getArchiveModel('employee1.xml')

        self.failUnlessEqual(employee1.name, model.name)

        employee1.address.zipcode = '90210'
        employee1.persist()

        employees.refresh()
        employee2 = employees[0]

        self.failUnlessEqual(employee2.address.zipcode, '90210')
