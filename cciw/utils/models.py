import random
import base64
import cPickle

from django.db import models


class ConfirmToken(models.Model):
    action_type = models.CharField("Action type", max_length="50")
    token = models.CharField(max_length=10)
    expires = models.DateTimeField()
    objdata = models.TextField()
    
    def _get_data(self):
        try:
            return cPickle.loads(base64.decodestring(self.objdata))
        except UnpicklingError:
            return None

    def _set_data(self, obj):
        self.objdata = base64.encodestring(cPickle.dumps(obj))

    data = property(_get_data, _set_data)

    @staticmethod
    def make_token():
        chars = [chr(c) for p1, p2 in [("A", "Z"),("a", "z"), ("0","9")] 
                          for c in range(ord(p1), ord(p2) + 1)]
        random.seed()
        random.shuffle(chars)
        return u''.join(chars[0:10])
