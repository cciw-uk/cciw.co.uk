"""
Utilities for manipulating images
"""

# Using 'convert', because it's installed on my hosting and dev box,
# and it's easier than getting

from django.conf import settings
import os
from PIL import ImageFile
import tempfile


def parse_image(filename):
    fp = open(filename, "rb")
    p = ImageFile.Parser()

    while 1:
        s = fp.read(1024)
        if not s:
            break
        p.feed(s)

    im = p.close()
    return im


class ValidationError(Exception):
    pass


def safe_del(filename):
    try:
        os.unlink(filename)
    except OSError:
        pass  # don't care if we couldn't delete for some reason


def write_file(fp, filedata):
    for chunk in filedata.chunks():
        fp.write(chunk)
    fp.close()


def fix_member_icon(member, filedata):
    fd, filename = tempfile.mkstemp()
    write_file(os.fdopen(fd, "wb"), filedata)

    try:
        img = parse_image(filename)
    except IOError:
        safe_del(filename)
        raise ValidationError("The image format was not recognised.")

    if img.size is None:
        safe_del(filename)
        raise ValidationError("The image format was not recognised.")

    if img.size[0] > settings.MEMBER_ICON_MAX_SIZE or \
       img.size[1] > settings.MEMBER_ICON_MAX_SIZE:
        # For now, just complain
        safe_del(filename)
        raise ValidationError("The image was bigger than %s by %s." %
                              (settings.MEMBER_ICON_MAX_SIZE,
                               settings.MEMBER_ICON_MAX_SIZE))
        # Ideally would have scale to fit

    # Convert to destination format
    ext = settings.DEFAULT_MEMBER_ICON.split('.')[-1]
    newrelpath = "%s/%s" % (settings.MEMBER_ICON_PATH, member.user_name + "." + ext)
    newfullpath = "%s/%s" % (settings.MEDIA_ROOT, newrelpath)

    opts = {}
    try:
        opts['transparency'] = img.info['transparency']
    except KeyError:
        pass
    img.save(newfullpath, **opts)

    os.chmod(newfullpath, 0o0777)
    member.icon = newrelpath
    member.save()
