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

from StringIO import StringIO

from xobj import xobj

from robj.lib import util
from robj.lib import httputil
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

    def testFileInteractions(self):
        # Start with an employee that we can then attach a file to.
        employee = self.POST('employee2.xml', '/api/employees')

        # Create a file.
        blob = util.mktemp()
        blob.write('\x00\x01' * 100)
        blob.flush()
        blob.seek(0)
        employee.file = blob

        # Get a file
        content = employee.file

        # Must seek to the begining of the file since sending it seeks to
        # the end.
        blob.seek(0)

        # Make sure they match.
        self.failUnlessEqual(blob.read(), content.read())

        # Overwrite the file
        blob2 = '\x00\x02' * 100
        employee.file = blob2
        content2 = employee.file

        # Make sure it was overwritten.
        self.failUnlessEqual(blob2, content2.read())

    def testHTTPDataFiles(self):
        employee = self.POST('employee2.xml', '/api/employees')

        sio = StringIO('\x00\x01' * 100)
        content = httputil.HTTPData(sio, chunked=True, size=200)
        employee.file = content

        sio.seek(0)
        content = httputil.HTTPData(sio, chunked=False, size=200)
        employee.file = content

        stringData = '\x00\x01' * 100
        content = httputil.HTTPData(stringData, size=200)
        employee.file = content

    def testFileDeletion(self):
        raise testsuite.SkipTestException('implement file deletion')

        employee = self.POST('employee2.xml', '/api/employees')
        employee.file = '\x01\x02' * 100

        # Try to delete the file from the server.
        employee.file.delete()
        self.failUnless(employee.id in self.server.data.employees.files)

    def testSettingDictionaryAttributes(self):
        # Start with an employee that we can then attach a file to.
        employee = self.POST('employee3.xml', '/api/employees')

        address = dict(
            street='1234 Foo Ct.',
            city='Bar Town',
            state='Baz',
            zipcode='12345',
        )

        employee.address = address

        self.failUnlessEqual(employee.address.street, address['street'])
        self.failUnlessEqual(employee.address.city, address['city'])
        self.failUnlessEqual(employee.address.state, address['state'])
        self.failUnlessEqual(employee.address.zipcode, address['zipcode'])

        employee.persist()

        model = self.getModel(employee.id)

        self.failUnlessEqual(employee.address.street, model.address.street)
        self.failUnlessEqual(employee.address.city, model.address.city)
        self.failUnlessEqual(employee.address.state, model.address.state)
        self.failUnlessEqual(employee.address.zipcode, model.address.zipcode)


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

    def testDictionaryAppend(self):
        employees = self.api.employees
        employees.append(self.getArchiveModel('employee1.xml'))
        employees.refresh()

        employee = dict(
            name = 'Bob',
            address = dict(
                street = 'foobar',
                city = 'foobar',
                state = 'foobar',
                zipcode = '12345',
            ),
            phone = '(919) 555-1234',
        )

        employees.append(employee)

        model = employees[-1]

        self.failUnlessEqual(model.name,
            employee['name'])
        self.failUnlessEqual(model.address.street,
            employee['address']['street'])
        self.failUnlessEqual(model.address.city,
            employee['address']['city'])
        self.failUnlessEqual(model.address.state,
            employee['address']['state'])
        self.failUnlessEqual(model.address.zipcode,
            employee['address']['zipcode'])
        self.failUnlessEqual(model.phone,
            employee['phone'])

    def testCollectionCache(self):
        employees = self.api.employees

        preappend_xobj = employees._root
        employees.append(self.getArchiveModel('employee1.xml'))
        postappend_xobj = employees._root

        # Make sure that the colleciton is not refreshed from the server as a
        # side affect of an append operation.
        self.failUnless(preappend_xobj is postappend_xobj)

        # Return to a known good state
        employees.refresh()

        # Test the same thing, but this time access the collection from
        # self.api.employees each time.
        preappend_xobj = self.api.employees._root
        self.api.employees.append(self.getArchiveModel('employee2.xml'))
        postappend_xobj = self.api.employees._root

        # Make sure the collection was not refetched
        self.failUnless(preappend_xobj is postappend_xobj)

    def testComplexCollections(self):
        xml1 = """\
<?xml version='1.0' encoding='UTF-8'?>
<results>
  <resultFiles>
    <resultFile>
      <type>msi</type>
      <size>79360</size>
    </resultFile>
  </resultFiles>
  <productCode>FD38CC28-0E31-45C4-8107-D7694663A2DD</productCode>
  <upgradeCode>B32B567C-B2E1-4105-86E0-6C332F440E6F</upgradeCode>
  <package>
    <components>
      <component>
        <uuid>DA94B959-D786-4D58-8428-2991DE6A4FE5</uuid>
        <path>Program Files\WindowsAppTest</path>
      </component>
    </components>
  </package>
</results>
"""

        xml2 = """\
<?xml version='1.0' encoding='UTF-8'?>
<results>
  <resultFiles>
    <resultFile>
      <type>msi</type>
      <size>79360</size>
    </resultFile>
  </resultFiles>
  <productCode>FD38CC28-0E31-45C4-8107-D7694663A2DD</productCode>
  <upgradeCode>B32B567C-B2E1-4105-86E0-6C332F440E6F</upgradeCode>
  <package>
    <components>
      <component>
        <uuid>DA94B959-D786-4D58-8428-2991DE6A4FE5</uuid>
        <path>Program Files\WindowsAppTest</path>
      </component>
      <component>
        <uuid>DA94B959-D786-4D58-8428-2991DE6A4FE6</uuid>
        <path>Program Files\WindowsAppTest2</path>
      </component>
    </components>
  </package>
</results>
"""

        doc = xobj.parse(xml1)
        root = doc.results

        results = rObjProxy('/results', None, root, parent=None)

        self.failIf(results._isCollection)
        self.failUnless(results.package._isCollection)
        self.failUnless(hasattr(results.package, 'components'))
        self.failUnlessEqual(len(results.package), 1)
        self.failUnless(results.package.components._isCollection)
        self.failUnlessEqual(len(results.package.components), 1)

        doc2 = xobj.parse(xml2)
        root2 = doc2.results

        results2 = rObjProxy('/results', None, root2, parent=None)

        self.failIf(results2._isCollection)
        self.failUnless(results2.package._isCollection)
        self.failUnless(hasattr(results2.package, 'components'))
        self.failUnlessEqual(len(results2.package), 1)
        self.failUnless(results2.package.components._isCollection)
        self.failUnlessEqual(len(results2.package.components), 2)

    def testMultiElementCollection(self):
        """
        Multi element collections are collections that contain elements of more
        than one tag name.
        """

        def getrobj(rootName, xml):
            doc = xobj.parse(xml)
            root = getattr(doc, rootName)
            obj = rObjProxy('/%s' % rootName, None, root, parent=None)
            return obj

        xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<systems>
  <event_types>foo</event_types>
  <system>
    <name>foo.example.com</name>
    <type>server</type>
  </system>
  <system>
    <name>bar.example.com</name>
    <type>desktop</type>
  </system>
</systems>
"""

        xml2 = """\
<?xml version='1.0' encoding='UTF-8'?>
<systems>
  <event_types>foo</event_types>
  <system>
    <name>foo.example.com</name>
    <type>server</type>
  </system>
</systems>
"""

        xml3 = """\
<?xml version='1.0' encoding='UTF-8'?>
<systems>
  <event_types>foo</event_types>
</systems>
"""

        systems1 = getrobj('systems', xml)
        self.failUnless(systems1._isCollection)
        self.failUnlessEqual(len(systems1), 2)
        self.failUnless(hasattr(systems1, 'event_types'))

        systems2 = getrobj('systems', xml2)
        self.failUnless(systems2._isCollection)
        self.failUnlessEqual(len(systems2), 1)
        self.failUnless(hasattr(systems2, 'event_types'))

        systems3 = getrobj('systems', xml3)
        systems3.append(dict(name='mysystem', type='server'), post=False,
            tag='system')

        self.failUnless(systems3._isCollection)
        self.failUnlessEqual(systems3._childTag, 'system')
        self.failUnlessEqual(len(systems3), 1)

        self.failUnless(hasattr(systems3, 'event_types'))

    def testLocalCacheOfCollections(self):
        xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<results>
  <package>
    <components>
      <component>
        <uuid>DA94B959-D786-4D58-8428-2991DE6A4FE5</uuid>
        <path>Program Files\WindowsAppTest</path>
      </component>
      <component>
        <uuid>DA94B959-D786-4D58-8428-2991DE6A4FE6</uuid>
        <path>Program Files\WindowsAppTest2</path>
      </component>
    </components>
  </package>
</results>
"""

        doc = xobj.parse(xml)
        root = doc.results

        results = rObjProxy('/results', None, root, parent=None)

        self.failUnlessEqual(results.package.components[0].uuid,
            'DA94B959-D786-4D58-8428-2991DE6A4FE5')
        self.failUnlessEqual(results.package.components[1].uuid,
            'DA94B959-D786-4D58-8428-2991DE6A4FE6')

    def testEmptyList(self):
        xml = """\
<?xml version='1.0' encoding='UTF-8'?>
<job>
  <package>
    <version />
    <components />
  </package>
  <foo>bar</foo>
</job>
"""

        doc = xobj.parse(xml)
        root = doc.job

        job = rObjProxy('/job', None, root, parent=None)

        self.failUnless(isinstance(job.package.components, xobj.XObj))

        job.package.components = []

        self.failUnless(isinstance(job.package.components, rObjProxy))
