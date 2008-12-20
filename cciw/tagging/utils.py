import string
from django.contrib.contenttypes import models
from django.db.models.base import ModelBase

# Caches of content types/models
_model_cache = {}
_content_type_cache = {}

# registry of functions that map primary
# key values to strings for each content type
_pk_to_str_mappers = {}

# registry of functions that map strings
# to primary key values for each content type
_pk_from_str_mappers = {}

# registry of functions used to render tags
# for different models
_renderers = {}

class NoMapperError(Exception): pass

def get_object(str_pk_val, content_type_id):
    """Gets an object from the content type id and a primary key value as a string"""
    return get_model(content_type_id)._default_manager.get(pk=pk_from_str(str_pk_val, content_type_id))

def get_model(content_type_id):
    """Gets a model class for a given content_type_id"""
    try:
        return _model_cache[content_type_id]
    except KeyError:
        ct = models.ContentType.objects.get_for_id(content_type_id)
        model = ct.model_class()
        _model_cache[content_type_id] = model
        _content_type_cache[model] = content_type_id
        return model

def get_content_type_id(model):
    """Gets a content type id for a given model"""
    if not isinstance(model, ModelBase):
        if not isinstance(type(model), ModelBase):
            raise Exception("%s is not a model" % model)
        model = type(model)
    try:
        return _content_type_cache[model]
    except KeyError:
        ct_id = models.ContentType.objects.get_for_model(model).id
        _model_cache[ct_id] = model
        _content_type_cache[model] = ct_id
        return ct_id

def strip_unsafe_chars(text):
    "Returns a text value with undesirable chars stripped"
    return u''.join(c for c in text if c not in u"<>&\"'?/")

def pk_from_str(pk_str, content_type_id):
    """Get a primary key value of the correct type."""
    try:
        mapper = _pk_from_str_mappers[get_model(content_type_id)]
    except KeyError:
        raise NoMapperError("No string-to-primary key mapper has been configured for content type %s" % content_type_id)
    return mapper(pk_str)

def pk_to_str(pk, content_type_id):
    """Get a string representation of a primary key value."""
    try:
        mapper = _pk_to_str_mappers[get_model(content_type_id)]
    except KeyError:
        raise NoMapperError("No primay key-to-string mapper has been configured for content type %s" % content_type_id)
    return mapper(pk)

def get_pk_as_str(django_object):
    ct_id = get_content_type_id(django_object.__class__)
    return pk_to_str(django_object._get_pk_val(), ct_id)

def register_mappers(model, pk_to_str=None, pk_from_str=None):
    """Register mapper functions for converting primary key values to and
    from strings, for a given model."""
    # register_mappers is called from a model module file
    # typically, so looking up ContentType ids immediately
    #  can cause have havoc when trying to *uninstall* models.
    # So we key on 'model', not content type id
    if pk_to_str is not None:
        _pk_to_str_mappers[model] = pk_to_str
    if pk_from_str is not None:
        _pk_from_str_mappers[model] = pk_from_str

def register_renderer(model, renderer):
    """Registers a function to be used to implement the render method
    of Tag when it's target is the supplied model type.
    The function is passed the tag object, and must return
    the html to be displayed on a page."""
    _renderers[model] = renderer

def get_renderer(model_ct):
    """Gets the renderer for a given content type id,
    or None if none can be found."""
    return _renderers.get(get_model(model_ct), None)

def tagging_normaliser(tag_sum, collection):
    """Example 'normaliser' for calculating the 'weight'
    of a given TagSummary object.

    collection is the complete TagSummaryCollection.
    """
    # Fit to scale 0 to 5
    rng = collection.count_max - collection.count_min
    if rng == 0:
        return 2 # put somewhere in the middle
    else:
        return int(5 * (tag_sum.count - collection.count_min)/rng)

