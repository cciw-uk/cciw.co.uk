import cciw.tagging.models
from cciw.tagging import utils

Any = object()

class RelatedGenericManyToManyDescriptor(object):
    # This class provides the functionality that makes a generic
    # many-to-many object (e.g. a Tag) available as attributes
    # on the models that are the targets of the relationship
    def __init__(self, m2m_model=None, from_model=None, to_model=Any,
            from_attrname=None, to_attrname=None):
        self.from_model = from_model
        self.from_attrname = from_attrname
        self.to_attrname = to_attrname
        self.to_model = to_model
        self.m2m_model = m2m_model
        # Delay getting from_ct and to_ct, because that involves a DB lookup
        # and can cause import errors due to cyclic imports


    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError, "Manager must be accessed via instance"

        if not hasattr(self, 'from_ct'):
            self.from_ct = utils.get_content_type_id(self.from_model)
            self.to_ct = (self.to_model is Any) and Any or utils.get_content_type_id(self.to_model)

        # Dynamically create a class that subclasses m2m_model's manager
        desc = self # so we can access the descriptor inside the nested class
        superclass = self.m2m_model._default_manager.__class__
        class RelatedManager(superclass):
            def get_query_set(self):
                return superclass.get_query_set(self).filter(**(self.core_filters))

            def add(self, *objs):
                """Adds a newly created tag to this set."""
                for obj in objs:
                    # Check whether the object matches
                    # our 'to' relation
                    if desc.to_ct is not Any:
                        obj_ct = getattr(obj, '%s_ct_id' % desc.to_attrname)
                        if obj_ct != desc.to_ct:
                            raise Exception("Can't add tag with content type %s to this set." % obj_ct)
                    # Set the 'from' relation
                    setattr(obj, desc.from_attrname, instance)
                    obj.save()
            add.alters_data = True

            def create(self, **kwargs):
                """Creates a new tag, and adds to this set."""
                new_obj = self.model(**kwargs)
                self.add(new_obj)
                return new_obj
            create.alters_data = True

        manager = RelatedManager()
        manager.core_filters = {
            '%s_ct__id__exact' % self.from_attrname: self.from_ct,
            '%s_id__exact' % self.from_attrname: utils.pk_to_str(instance._get_pk_val(), self.from_ct)
        }
        # Limit to Tags of the desired content type
        if self.to_ct is not Any:
            manager.core_filters['%s_ct__id__exact' % self.to_attrname] = self.to_ct
        manager.model = self.m2m_model

        return manager

def add_tagging_fields(creator_model=Any, creator_attrname=None,
                        target_model=Any, target_attrname=None):
    """Adds fields to model classes to represent related
    tags.  These fields can be used like reverse foreign
    keys to get a set of related Tag objects.

    All arguments are optional, with the constraint
    that one of creator_model and target_model must be provided
    otherwise there is nothing to do.

    creator_model is the class of object that the 'creator' attribute
    of a Tag will return, or 'Any' (the default) for any.

    target_model is the class of object that the 'target' attribute
    of a Tag will return, or 'Any' (the default) for any.

    creator_attrname is the name of the attribute that will be added
    to the 'creator_model' class.  If None, the attribute won't be
    added to the class.

    target_attrname is the name of the attribute that will be added
    to the 'target_model' class.  If None, the attribute won't be
    added to the class.

    See examples below.

    WARNING: this function can add some cyclic import dependencies
    that can make it difficult to drop your database tables using
    'django-admin.py reset'
    """
    if creator_model is Any and target_model is Any:
        raise Exception("At least one of creator_model and target_model must be set")
    if creator_model is not Any and creator_attrname is not None:
        setattr(creator_model, creator_attrname,
            RelatedGenericManyToManyDescriptor(m2m_model=cciw.tagging.models.Tag,
                from_model=creator_model, from_attrname='creator',
                to_model=target_model, to_attrname='target'))

    if target_model is not Any and target_attrname is not None:
        setattr(target_model, target_attrname,
            RelatedGenericManyToManyDescriptor(m2m_model=cciw.tagging.models.Tag,
                from_model=target_model, from_attrname='target',
                to_model=creator_model, to_attrname='creator'))


## Examples:

## # Member has a string primary key
## register_mappers(Member, pk_to_str=str, pk_from_str=str)
## # Post and Topic have integer primary keys
## register_mappers(Post, pk_to_str=str, pk_from_str=int)
## register_mappers(Topic, pk_to_str=str, pk_from_str=int)

## add_tagging_fields(
##     creator_model=Member, creator_attrname='post_tags',
##     target_model=Post, target_attrname='tags',
## )

## Result:
## Every Member object gets 'post_tags' attribute which retrieves all
## the tags by that member on Post objects.
## Every Post object gets 'tags' attribute which evaluates to all tags on
## that post by Member objects

##    add_tagging_fields(
##        creator_model=Member, creator_attrname='all_tags',
##    )

## Result:
## Every Member object gets 'all_tags' attribute which retrieves all
## tags by that member on any type of object, so the
## following would be a heterogeneous list:
##   [tag.target for tag in mymember.all_tags.all()]

##    add_tagging_fields(
##        creator_model=Member, creator_attrname='topic_tags',
##        target_model=Topic
##    )

## Result:
## Every Member objects gets 'topics_tags' which retrieves all
## tags by that member on Topic objects.
## But Topic objects don't get any attributes.

## In each case, the attribute added returns a RelatedManager object,
## like reverse foreign keys and m2m relationships.  The RelatedManager
## supports add() and create(), but not remove() -- use delete instead,
## since you are actually deleting Tag objects
