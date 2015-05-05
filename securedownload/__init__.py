"""
An app that makes it easy to create (relatively) secure download links to
restricted folders.  To avoid using the Django process to serve the file,
temporary symlinks are placed into designated directory, which must be served by
a separate webserver
"""
