INTRODUCTION
============

**Archived projet: This project is no longer under active development and was archived on 2024-07-24.**

This is an initial offering of the rObj interface.  It should not be
considered a stable interface and may not be backwards compatible
with future releases.

The rObj project is a dynamic REST client library.

It is not required to provide an XML schema to use rObj.  Custom
objects may be used for parts or all of the document, whether or
not an XML schema is provided.  Schema validation is optional.
If new elements show up, they will be preserved across read/write;
schema additions will not normally require code changes.
