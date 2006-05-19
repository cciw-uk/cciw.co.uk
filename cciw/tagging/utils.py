import django.contrib.contenttypes.models
from django.contrib import contenttypes

# Caches of content types/models
_model_cache = {}
_content_type_cache = {}

# registry of functions that map primary
# key values to strings for each content type
_pk_to_str_mappers = {}

# registry of functions that map strings
# to primary key values for each content type
_pk_from_str_mappers = {}


def get_model(content_type_id):
    """Gets a model class for a given content_type_id"""
    try:
        return _model_cache[content_type_id]
    except KeyError:
        ct = contenttypes.models.ContentType.objects.get(pk=content_type_id)
        model = ct.model_class()
        _model_cache[content_type_id] = model
        _content_type_cache[model] = content_type_id
        return model

def get_content_type_id(model):
    """Gets a content type id for a given model"""
    try:
        return _content_type_cache[model]
    except:
        ct_id = contenttypes.models.ContentType.objects.get_for_model(model).id
        _model_cache[ct_id] = model
        _content_type_cache[model] = ct_id
        return ct_id

def pk_from_str(pk_str, content_type_id):
    """Get a primary key value of the correct type."""
    try:
        mapper = _pk_from_str_mappers[content_type_id]
    except:
        raise Exception("No string-to-primary key mapper has been configured for content type %s" % content_type_id)
    return mapper(pk_str)

def pk_to_str(pk, content_type_id):
    """Get a string representation of a primary key value."""
    try:
        mapper = _pk_to_str_mappers[content_type_id]
    except:
        raise Exception("No primay key-to-string mapper has been configured for content type %s" % content_type_id)
    return mapper(pk)

def register_mappers(model, pk_to_str=None, pk_from_str=None):
    """Register mapper functions for converting primary key values to and
    from strings, for a given model."""
    content_type_id = get_content_type_id(model)

    if pk_to_str is not None:
        _pk_to_str_mappers[content_type_id] = pk_to_str
    if pk_from_str is not None:
        _pk_from_str_mappers[content_type_id] = pk_from_str
