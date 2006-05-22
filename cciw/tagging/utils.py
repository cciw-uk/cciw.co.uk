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

# registry of functions used to render tags
# for different models
_renderers = {}

def get_object(str_pk_val, content_type_id):
    """Gets an object from the content type id and a primary key value as a string"""
    return get_model(content_type_id)._default_manager.get(pk=pk_from_str(str_pk_val, content_type_id))

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

def register_renderer(model, renderer):
    """Registers a function to be used to implement the __str__ method
    of Tag when it's target is the supplied model type.
    The function is passed the tag object, and must return
    the html to be displayed on a page."""
    _renderers[get_content_type_id(model)] = renderer
    
def get_renderer(model_ct):
    """Gets the renderer for a given content type id, 
    or None if none can be found."""
    return _renderers.get(model_ct, None)

def tagging_normaliser(tag_sum, collection=None):
    """Example 'normaliser' for calculating the 'weight'
    of a given TagSummary object.
    
    collection is the complete TagSummaryCollection.
    """
    # Rather simplistic normalising :-)
    return min(tag_sum.count, 5)
