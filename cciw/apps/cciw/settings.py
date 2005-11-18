AWARD_UPLOAD_PATH = '/home/httpd/www.cciw.co.uk/django/media/images/awards'
MEMBERS_ICONS_UPLOAD_PATH = '/home/httpd/www.cciw.co.uk/django/media/images/members'
CCIW_MEDIA_ROOT = 'http://cciw_django_local/media/'

from django.models.camps import camps
import datetime


class ThisYear(object):
    """Class to get what year the website is currently on.  The website year is
    equal to the year of the last camp in the database, or the year 
    afterwards if that camp is in the past. It is implemented
    in this way to allow backwards compatibilty with code that
    expects THISYEAR to be a simplez integer.  And for fun."""
    def __init__(self):
        self.get_year()
    def get_year(self):
        lastcamp = camps.get_list(limit = 1, order_by = ('-year',))[0]
        if lastcamp.end_date <= datetime.date.today():
            self.year = lastcamp.year + 1
        else:
            self.year = lastcamp.year
        
        self.timestamp = datetime.datetime.now()
        
    def update(self):
        # update every hour
        if (datetime.datetime.now() - self.timestamp).seconds > 3600:
            self.get_year()
            
    # TODO - better way of doing this lot? some metaclass magic I imagine
    def __str__(self):
        self.update()
        return str(self.year)
        
    def __cmp__(self, other):
        self.update()
        return cmp(self.year, other)
        
    def __repr__(self):
        self.update()
        return str(self)
        
    def __add__(self, other):
        self.update()
        return self.year + other

    def __sub__(self, other):
        self.update()
        return self.year - other

THISYEAR = ThisYear()
