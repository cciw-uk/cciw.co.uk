from django.contrib.contenttypes.models import ContentType
from django.db import models
from cciw.tagging import utils

class CTRelatedObjectDescriptor(object):
    """Encapsulates descriptor behaviour for 'target' and 'by'
    properties on 'Tag' model i.e. a related object
    with associated content type.""" 
    def __init__(self, id_attr, ct_attr):
        # id_attr is the name of the 'id' attribute on the
        # object the descriptor is attached to.
        # ct_attr is the name of the 'ct' attribute
        self.id_attr = id_attr
        self.ct_attr = ct_attr
        self.cache_attr = '_ctrelcache_' + id_attr

    def __get__(self, obj, objtype):
        if obj is None:
            return self
        try:
            # try the cache first
            return getattr(obj, self.cache_attr)
        except AttributeError:
            # Get id and content type from the Tag
            id = getattr(obj, self.id_attr)
            ct = getattr(obj, self.ct_attr)
            # Use id and ct to get the actuall object
            retval = utils.get_model(ct)._default_manager.get(pk=utils.pk_from_str(id, ct))
            setattr(obj, self.cache_attr, retval)
            return retval

    def __set__(self, obj, value):
        if obj is None:
            return self
        # Caculate content type and id from the 
        # passed in object
        ct = utils.get_content_type_id(value.__class__)
        id = utils.pk_to_str(value._get_pk_val(), ct)
        # Set them on Tag object, and update cache
        setattr(obj, self.ct_attr, ct)
        setattr(obj, self.id_attr, id)
        setattr(obj, self.cache_attr, value)

class Tag(models.Model):
    text = models.CharField("Text", maxlength=32)
    target_id = models.CharField("'Target' ID", maxlength=64)
    target_ct = models.ForeignKey(ContentType, verbose_name="'Target' content type")
    by_id = models.CharField("'By' ID", maxlength=64)
    by_ct = models.ForeignKey(ContentType, verbose_name="'By' content type")
    added = models.DateTimeField("Date added", auto_now_add=True)
    
    target = CTRelatedObjectDescriptor('target_id', 'target_ct_id')
    by = CTRelatedObjectDescriptor('by_id', 'by_ct_id')
    
    class Meta:
        ordering = ('-added',)
    
    class Admin:
        list_display = (
            'text',
            'target',
            'by',
            'added',
        )
        list_filter = (
            'target_ct',
            'by_ct',
        )
        search_fields = ('text,')
