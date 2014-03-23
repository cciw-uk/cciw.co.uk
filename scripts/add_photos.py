#!/usr/bin/env python2.5
from cciw.cciwmain.models import Photo, Gallery, Camp
from cciw.cciwmain.views.camps import get_gallery_for_camp
import sys
import re

def usage():
    return """
Usage: add_photos.py photo1.jpeg [photo2.jpeg...]
"""


camp_re = re.compile('^(?P<year>\d{4})-(?P<number>\d+)')

def main():
    if len(sys.argv) == 1:
        print(usage())
        sys.exit(1)

    for photoname in sys.argv[1:]:
        # Parse the photoname
        m = camp_re.match(photoname)
        if m is None:
            raise Exception("Photo %s is not in the form yyyy-n-*" % photoname)

        try:
            camp = Camp.objects.get(year=int(m.groupdict()['year']),
                                    number=int(m.groupdict()['number']))
        except Camp.DoesNotExist:
            raise Exception("Camp %s could not be found" % m.group())

        gallery = get_gallery_for_camp(camp)

        if gallery is None:
            raise Exception(("A gallery for camp %s, %s does not exist.  " +
                            "It is not created until the day the camp ends.") % (camp.number, camp.year))

        try:
            p = Photo.objects.get(gallery=gallery, filename=photoname)
        except Photo.DoesNotExist:
            p = None
        if p is None:
            p = Photo.create_default_photo(photoname, gallery)
            print("Created photo %s." % photoname)
        else:
            print("Warning: Photo %s already exists." % photoname)

if __name__ == '__main__':
    main()
