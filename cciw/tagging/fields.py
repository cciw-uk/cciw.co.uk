import cciw.tagging.models
from cciw.tagging import utils


Any = object()


class RelatedTagsDescriptor(object):
    # This class provides the functionality that makes the Tags
    # available as attributes on the models that are 'targets'
    # or the 'source' ('by') of the tagging.
    def __init__(self, from_model=None, to_model=Any,
            from_attrname=None, to_attrname=None):
        self.from_model = from_model
        self.from_ct = utils.get_content_type_id(from_model)
        self.to_ct = (to_model == Any) and Any or utils.get_content_type_id(to_model)
        self.from_attrname = from_attrname # 'target' or 'by'
        self.to_attrname = to_attrname     # 'target' or 'by'

    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError, "Manager must be accessed via instance"

        # Dynamically create a class that subclasses Tag's manager
        desc = self # so we can access the descriptor inside the nested class
        model = cciw.tagging.models.Tag
        superclass = model._default_manager.__class__
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
        manager.model = model

        return manager
        
def add_tagging_fields(by_model=Any, by_attrname=None,
                        target_model=Any, target_attrname=None):
    """Adds fields to model classes to represent related 
    tags.  These fields can be used like reverse foreign
    keys to get a set of related Tag objects.
  
    All arguments are optional, with the constraint
    that one of by_model and target_model must be provided
    otherwise there is nothing to do.
    
    by_model is the class of object that the 'by' attribute
    of a Tag will return, or 'Any' (the default) for any.
    
    target_model is the class of object that the 'target' attribute
    of a Tag will return, or 'Any' (the default) for any.
    
    by_attrname is the name of the attribute that will be added
    to the 'by_model' class.  If None, the attribute won't be
    added to the class.

    target_attrname is the name of the attribute that will be added
    to the 'target_model' class.  If None, the attribute won't be
    added to the class.
    
    """
    if by_model is Any and target_model is Any:
        raise Exception("At least one of by_model and target_model must be set")
    if by_model is not Any and by_attrname is not None:
        setattr(by_model, by_attrname, 
            RelatedTagsDescriptor(
                from_model=by_model, from_attrname='by',
                to_model=target_model, to_attrname='target'))

    if target_model is not Any and target_attrname is not None:
        setattr(target_model, target_attrname, 
            RelatedTagsDescriptor(
                from_model=target_model, from_attrname='target',
                to_model=by_model, to_attrname='by'))


## Examples:

## # Member has a string primary key
## register_mappers(Member, pk_to_str=str, pk_from_str=str) 
## # Post and Topic have integer primary keys
## register_mappers(Post, pk_to_str=str, pk_from_str=int)
## register_mappers(Topic, pk_to_str=str, pk_from_str=int)

## add_tagging_fields(
##     by_model=Member, by_attrname='post_tags',
##     target_model=Post, target_attrname='tags',
## )

## Result:
## Every Member object gets 'post_tags' attribute which retrieves all
## the tags by that member on Post objects.
## Every Post object gets 'tags' attribute which evaluates to all tags on 
## that post by Member objects

##    add_tagging_fields(
##        by_model=Member, by_attrname='all_tags',
##    )

## Result: 
## Every Member object gets 'all_tags' attribute which retrieves all
## tags by that member on any type of object, so the
## following would be a heterogeneous list:
##   [tag.target for tag in mymember.all_tags.all()]

##    add_tagging_fields(
##        by_model=Member, by_attrname='topic_tags',
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
