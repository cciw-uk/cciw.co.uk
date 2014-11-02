from collections import OrderedDict
from datetime import datetime
import random
import crypt

from django.contrib.auth.hashers import BasePasswordHasher


class CciwLegacyPasswordHasher(BasePasswordHasher):
    # written to maintain compatibility with previous system
    algorithm = "cciwlegacy"

    def encode(self, password, salt):
        # salt becomes first two letters of right hand side
        return "%s$%s" % (self.algorithm, crypt.crypt(password, salt))

    def verify(self, password, encoded):
        algo, the_rest = encoded.split('$', 2)
        salt = the_rest[0:2]
        assert algo == self.algorithm
        return self.encode(password, salt) == encoded

    def salt(self):
        rand64= "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        random.seed(datetime.now().microsecond)
        return rand64[int(random.random()*64)] + rand64[int(random.random()*64)]

    def safe_summary(self, encoded):
        algo, the_rest = encoded.split('$', 2)
        return OrderedDict([
            ('algorithm', algo),
            ('salt', the_rest[0:2]),
            ('hash', the_rest[2:4] + "..."),
        ])
