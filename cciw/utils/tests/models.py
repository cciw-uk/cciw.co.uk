from django.test import TestCase
from cciw.utils.models import ConfirmToken
from datetime import datetime

class ConfirmTokenTests(TestCase):
    def test_data(self):
        """Tests that pickling/unpickling works"""
        c = ConfirmToken()
        c.expires = datetime.now()
        c.action_type = "test"
        c.token = ConfirmToken.make_token()
        c.data = {'key1': 'val1', 'key2': 'val2'}

        c.save()

        c2 = ConfirmToken.objects.filter(token=c.token)[0]
        assert id(c2) != id(c)
        self.assertEqual(c2.data, c.data)
