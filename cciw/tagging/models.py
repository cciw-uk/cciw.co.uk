"""Model and related functionality for the tagging app."""
from django.contrib.contenttypes.models import ContentType
from django.db import models
from cciw.tagging import utils
from django.db import backend, connection
from django.conf import settings
import django.contrib.contenttypes

try:
    _normaliser = settings.TAGGING_NORMALISER
except AttributeError:
    _normaliser = utils.tagging_normaliser

class TagSummaryCollection(list):
    """Collection of TagSummary objects.
  
    It exists to calculate and store its count_min and
    count_max properties, which are the minimum and maximum
    values of 'count' of all its children."""
    def __init__(self, iterable):
        list.__init__(self, iterable)
        count_max = 0
        count_min = -1
        for tagsum in self:
            tagsum.collection = self
            count = tagsum.count
            if count > count_max:
                count_max = count
            if count_min == -1 or count < count_min:
                count_min = count
        self.count_max, self.count_min = count_max, count_min

class TagSummary(object):
    """An object representing a summary of tags.
    
    - text is the tag text
    - count is the number of tags with that text.
    - collection is the collection of TagSummary
      objects this belongs to.
    """
    def __init__(self, text, count):
        self.text, self.count = text, count
        self.collection = None # this is set externally later
        
    def weight(self):
        """Weight is the count, but normalised using settings.TAGGING_NORMALISER."""
        return _normaliser(self, self.collection)

class TagTarget(object):
    """Simple container for targets of tags.  Includes
    some of the same attributes and methods as Tags, where appropriate"""
    def __init__(self, text, count, target_id, target_ct_id):
        self.target_id, self.target_ct_id = target_id, target_ct_id
        self.text, self.count = text, count

    @property
    def target(self):
        try:
            return self._target
        except AttributeError:
            target = utils.get_object(self.target_id, self.target_ct_id)
            self._target = target
            return target

    def render(self):
        """Renders the target using the registered renderer."""
        return utils.get_renderer(self.target_ct_id)(self.target)

    @property
    def target_ct(self):
        return django.contrib.contenttypes.models.ContentType.objects.get(pk=self.target_ct_id)
        
    # Possible TODO : add a 'by_list' property that dynamically returns all
    # objects that have tagged the target
    
class CTGenericObjectDescriptor(object):
    """Desciptor used to return an object that is defined
    in terms of a ContentType id and a string primary key."""
    def __init__(self, id_attr, ct_attr):
        # id_attr is the name of the '_id' attribute on the
        # object the descriptor is attached to.
        # ct_attr is the name of the '_ct_id' attribute on the
        # object the descriptor is attached to
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
            # Use id and ct to get the actual object
            retval = utils.get_object(id, ct)
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

class TagManager(models.Manager):
    def _get_model_limited_query(self, target_model=None, by_model=None):
        q = self.get_query_set()
        if target_model is not None:
            q = q.filter(target_ct__id=utils.get_content_type_id(target_model))
        if by_model is not None:
            q = q.filter(by_ct__id=utils.get_content_type_id(by_model))
        return q

    def get_distinct_text(self, target_model=None, by_model=None, **kwargs):
        """Gets distinct 'text' values as a list of strings.
        
        Supply 'target_model' and/or 'by_model' to limit values to specified models.
        
        kwargs are extra keyword arguments supplied to QuerySet.filter(), which
        can be used to limit the query to a specific target object for example.
        """
        q = self._get_model_limited_query(target_model, by_model)
        return q.filter(**kwargs).distinct().values('text')
        
    def get_text_counts(self, target_model=None, by_model=None, 
            target=None, by=None, limit=None, order='count', text=None):
        """Returns a sequence (TagSummaryCollection) of TagSummary objects i.e.
        a tag 'text' value with its associated count.
        
        Use target_model, by_model, target and by to limit the query
        to the model types or specific objects.
        
        Use limit to specify that only the top 'n' should be returned.
        
        'order' can be 'count' (descending popularity) or 
        'text'.(alphabetical, ascending)
        
        'text' constrains the query to a single text value.
        
        This method does not work as expected in a 'related' context.
        """
        # We need to do GROUP BY etc, so it's easier to just construct
        # our own SQL
        cursor = connection.cursor()
        where = []
        params = []
        qn = backend.quote_name
        if target_model is None and target is not None:
            target_model = target.__class__
        if by_model is None and by is not None:
            by_model = by.__class__

        if target_model is not None:
            target_ct = utils.get_content_type_id(target_model)
            where.append('%s = %%s' % qn('target_ct_id'))
            params.append(target_ct)
            if target is not None:
                where.append('%s = %%s' % qn('target_id'))
                params.append(utils.pk_to_str(target._get_pk_val(), target_ct))

        if by_model is not None:
            by_ct = utils.get_content_type_id(by_model)
            where.append('%s = %%s' % qn('by_ct_id'))
            params.append(by_ct)
            if by is not None:
                where.append('%s = %%s' % qn('by_id'))
                params.append(utils.pk_to_str(by._get_pk_val(), by_ct))

        if text is not None:
            where.append('%s = %%s' %qn('text'))
            params.append(text)

        # SELECT
        sql = "SELECT %s, COUNT(%s) AS c FROM %s" % \
                (qn('text'), qn('text'), qn(Tag._meta.db_table))
        # WHERE
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        # GROUP BY
        sql +=  "GROUP BY %s "  % qn('text')
        # ORDER BY
        if order == 'count':
            sql += " ORDER BY c DESC"
        else:
            sql += " ORDER BY %s ASC" % qn('text')
        # LIMIT
        if limit is not None:
            sql += ' ' + backend.get_limit_offset_sql(limit, None)

        cursor.execute(sql, params)
        return TagSummaryCollection([TagSummary(r[0], r[1]) for r in cursor.fetchall()])

    def get_targets(self, text, limit=None, offset=None, target_model=None):
        """Returns target items that match the text value, as a sequence
        of two-tuples of (target, count)
        
        Items are ordered by popularity (count) descending.
        
        Use target_model to limit the targets to the specified model
        
        Use limit and offset to alter which/how many targets are found.
        """
        # SELECT COUNT(by_id) as c, target_id, target_ct_id 
        #  FROM tagging_tag
        #  WHERE text = foo GROUP BY target_id, target_ct_id
        #  ORDER BY c DESC LIMIT x
        
        # Really this should be something like COUNT(combination_of(by_id, by_ct_id)),
        # which you can't do, but actually, it makes no sense for one person ('by'
        # object) to tag the same thing more than once with the same text,
        # so as long as we don't do 'DISTINCT', we will get accurate results.
        qn = backend.quote_name
        # SELECT
        sql = "SELECT COUNT(%s) as c, %s, %s FROM %s WHERE %s = %%s" % \
                (qn('by_id'), qn('target_id'), qn('target_ct_id'), qn(Tag._meta.db_table), qn('text'))
        params = [text]
        # additional WHERE
        if target_model is not None:
            sql += " AND %s = %%s" % qn('target_ct_id')
            params.append(utils.get_content_type_id(target_model))
        # GROUP BY and ORDER BY
        sql += " GROUP BY %s, %s ORDER BY c DESC" % \
                (qn('target_id'), qn('target_ct_id'))
        # LIMIT
        if limit is not None:
            sql += ' ' + backend.get_limit_offset_sql(limit, offset)
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return [TagTarget(text, int(row[0]), row[1], int(row[2])) 
                    for row in cursor.fetchall()]

    def get_target_count(self, text, target_model=None):
        """Gets the total number of items that get_targets returns,
        (with no limits), but more efficiently than len(get_targets())"""
        qn = backend.quote_name
        inner_sql = "SELECT DISTINCT %s, %s FROM %s WHERE %s = %%s" % \
            (qn('target_ct_id'), qn('target_id'), qn(Tag._meta.db_table), qn('text'))
        params = [text]
        # additional WHERE
        if target_model is not None:
            inner_sql += " AND %s = %%s" % qn('target_ct_id')
            params.append(utils.get_content_type_id(target_model))
        sql = "SELECT COUNT(*) FROM (%s) as a" % inner_sql
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return int(cursor.fetchone()[0])

class Tag(models.Model):
    text = models.CharField("Text", maxlength=32)
    target_id = models.CharField("'Target' ID", maxlength=64)
    target_ct = models.ForeignKey(ContentType, verbose_name="'Target' content type")
    by_id = models.CharField("'By' ID", maxlength=64)
    by_ct = models.ForeignKey(ContentType, verbose_name="'By' content type")
    added = models.DateTimeField("Date added", auto_now_add=True)
    
    target = CTGenericObjectDescriptor('target_id', 'target_ct_id')
    by = CTGenericObjectDescriptor('by_id', 'by_ct_id')
    objects = TagManager()
    
    def __str__(self):
        return "%s tagged as %s by %s" % (self.target, self.text, self.by)
        
    def render(self):
        """Returns a rendered (e.g. HTML) representation of the
        tag target.  Requires a 'renderer' to be registered first."""
        return utils.get_renderer(self.target_ct_id)(self.target)

    def count_tagged_by_others(self):
        """Returns the number of other 'by' objects that have tagged
        the same object that this tag is for."""
        # only includes 'by' objects of the same content type,
        # as the SQL is harder otherwise.
        
        # try cache first
        try:
            return self._count_tagged_by_others
        except AttributeError:
            pass
        # SELECT COUNT(DISTINCT(by_id)) FROM "tagging_tag" 
        # WHERE target_ct_id = x AND target_id = y AND by_ct_id = z AND NOT (by_id = q)
        cursor = connection.cursor()
        qn = backend.quote_name
        sql = "SELECT COUNT(DISTINCT(%s)) FROM %s WHERE %s = %%s AND %s = %%s AND %s = %%s AND NOT (%s = %%s)" % \
                (qn('by_id'), qn(Tag._meta.db_table), qn('target_ct_id'), qn('target_id'), qn('by_ct_id'), qn('by_id'))
        params = [self.target_ct_id, self.target_id, self.by_ct_id, self.by_id]
        cursor.execute(sql, params)
        retval = int(cursor.fetchone()[0])
        
        # cache so we can use it more cheaply in templates
        self._count_tagged_by_others = retval
        return retval
        
    def count_tagged_with_text(self):
        """Returns the total number of times that this target 
        has been tagged with this text."""
        
        # we could do this more efficiently if we didn't use self.target
        return Tag.objects.get_text_counts(target=self.target, text=self.text)[0].count
        
    
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
        search_fields = ('text',)
