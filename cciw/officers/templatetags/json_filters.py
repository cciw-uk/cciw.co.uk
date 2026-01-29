# Thanks to skan for this snippet http://djangosnippets.org/users/skam/
import json

from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.template import Library

register = Library()


def jsonify(obj: object) -> str:
    if isinstance(obj, QuerySet):
        return serialize("json", obj)
    return json.dumps(obj)


register.filter("jsonify", jsonify)
