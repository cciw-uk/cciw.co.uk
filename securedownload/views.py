import datetime
import hmac
import os
import posixpath
import urllib
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponseForbidden
from django.utils.hashcompat import sha_hmac

def serve_secure_file(filename):
    """
    Returns an HTTP redirect to serve the specified file.
    It will be a redirect to a location under SECURE_FILES_SERVE_URL,
    which should map to SECURE_FILES_SERVE_ROOT

    filename is relative to SECURE_FILES_SOURCE.
    """
    src = os.path.join(settings.SECURE_FILES_SOURCE, filename)
    if not os.path.isfile(src):
        raise Http404()
    # Make a link
    ts = datetime.datetime.now().strftime("%s")
    # Make a directory that cannot be guessed, and that contains the timestamp
    # so that we can remove it easily by timestamp later.
    key = "cciw.officers.secure_file" + settings.SECRET_KEY
    nonce = hmac.new(key, "%s-%s" % (ts, filename), sha_hmac).hexdigest()
    dirname = "%s-%s" % (ts, nonce)
    abs_destdir = os.path.join(settings.SECURE_FILES_SERVE_ROOT, dirname)
    if not os.path.isdir(abs_destdir):
        os.mkdir(abs_destdir)
    dest = os.path.join(dirname, os.path.basename(filename))
    os.symlink(src, os.path.join(settings.SECURE_FILES_SERVE_ROOT, dest))
    return HttpResponseRedirect(os.path.join(settings.SECURE_FILES_SERVE_URL, dest))

def sanitise_path(path):
    newpath = ''
    for part in path.split('/'):
        if not part:
            # Strip empty path components.
            continue
        drive, part = os.path.splitdrive(part)
        head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # Strip '.' and '..' in path.
            continue
        newpath = os.path.join(newpath, part).replace('\\', '/')
    return newpath

def access_folder_securely(folder, check_permission):
    """
    Creates a view function for accessing files in a folder.
    check_permission is a callable that takes a request and
    returns True if the file should be served.

    folder is relative to SECURE_FILES_SOURCE.
    """
    def view(request, filename):
        if check_permission(request):
            filename = posixpath.normpath(urllib.unquote(filename))
            fname = sanitise_path(filename)
            if fname != filename:
                raise Http404()
            return serve_secure_file(os.path.join(folder, fname))
        else:
            return HttpResponseForbidden("<h1>Access denied</h1>")
    return view
