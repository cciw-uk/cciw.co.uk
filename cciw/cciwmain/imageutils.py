"""
Utilities for manipulating images
"""

# Using 'convert', because it's installed on my hosting and dev box,
# and it's easier than getting 

from django.conf import settings
import shutil
import os
import ImageFile
import glob

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
        pass # don't care if we couldn't delete for some reason


def fix_member_icon(member):
    filename = "%s/%s" % (settings.MEDIA_ROOT, member.icon)
    try:
        img = parse_image(filename)
    except IOError:
        safe_del(filename)
        raise ValidationError(u"The image format was not recognised.")
    
    if img.size is None:
        safe_del(filename)
        raise ValidationError(u"The image format was not recognised.")
    
    if img.size[0] > settings.MEMBER_ICON_MAX_SIZE or \
       img.size[1] > settings.MEMBER_ICON_MAX_SIZE:
        # For now, just complain
        safe_del(filename)
        raise ValidationError(u"The image was bigger than %s by %s." % \
            (settings.MEMBER_ICON_MAX_SIZE, settings.MEMBER_ICON_MAX_SIZE))
        
        # Scale to fit - TODO
        #factor = max(img.size[0], img.size[1])/float(settings.MEMBER_ICON_MAX_SIZE)
        #new_width, new_height = size[0]/factor, size[1]/factor
    
    # Give the icon a predictable name, with the same extension it had before.
    # We refer to it in views without its extension, and use content negotiation
    # to get the right one.
    # This means we can just we only need the primary key (the username) of 
    # the Member object to calculate this URL, saving on *lots* of db queries.
    
    ext = filename.split('.')[-1]
    # Remove existing variants
    for f in glob.glob("%s/%s/%s" % (settings.MEDIA_ROOT, settings.MEMBER_ICON_PATH, member.user_name + ".*")):
        os.unlink(f)

    newrelpath = "%s/%s" % (settings.MEMBER_ICON_PATH, member.user_name + "." + ext)
    newfullpath = "%s/%s" % (settings.MEDIA_ROOT, newrelpath)
    shutil.move(filename, newfullpath)
    os.chmod(newfullpath, 0777)
    member.icon = newrelpath
    member.save()
