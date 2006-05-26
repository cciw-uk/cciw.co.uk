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
        
    def __repr__(self):
        return "<TagSummary: %s x %r>" % (self.count, self.text)


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
        
    # Possible TODO : add a 'creator_list' property that dynamically returns all
    # objects that have tagged the target
    
class GenericForeignKey(object):
    """Desciptor used to return an object that is defined
    in terms of a ContentType id and a string primary key."""
    def __init__(self, id_attr, ct_id_attr):
        # id_attr is the name of the '_id' attribute on the
        # object the descriptor is attached to.
        # ct_attr is the name of the '_ct_id' attribute on the
        # object the descriptor is attached to
        self.id_attr = id_attr
        self.ct_id_attr = ct_id_attr
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
            ct_id = getattr(obj, self.ct_id_attr)
            # Use id and ct to get the actual object
            retval = utils.get_object(id, ct_id)
            setattr(obj, self.cache_attr, retval)
            return retval

    def __set__(self, obj, value):
        if obj is None:
            return self
        # Caculate content type and id from the 
        # passed in object
        ct_id = utils.get_content_type_id(value.__class__)
        id = utils.pk_to_str(value._get_pk_val(), ct_id)
        # Set them on Tag object, and update cache
        setattr(obj, self.ct_id_attr, ct_id)
        setattr(obj, self.id_attr, id)
        setattr(obj, self.cache_attr, value)

class TagManager(models.Manager):
    # Lots of methods require custom SQL, which means:
    #  - we can't use normal .filter() stuff, so we need to have keyword 
    #    arguments for everything that you might want to query on.
    #  - query_set.core_filters won't work automatically, so we have to manually
    #    merge in data from core_filters for methods to work correctly in a 
    #    related context.
    def _get_model_limited_query(self, target_model=None, creator_model=None):
        q = self.get_query_set()
        if target_model is not None:
            q = q.filter(target_ct__id=utils.get_content_type_id(target_model))
        if creator_model is not None:
            q = q.filter(creator_ct__id=utils.get_content_type_id(creator_model))
        return q

    def get_distinct_text(self, target_model=None, creator_model=None, **kwargs):
        """Gets distinct 'text' values as a list of strings.
        
        Supply 'target_model' and/or 'creator_model' to limit values to specified models.
        
        kwargs are extra keyword arguments supplied to QuerySet.filter(), which
        can be used to limit the query to a specific target object for example.
        """
        q = self._get_model_limited_query(target_model, creator_model)
        return [row['text'] for row in  q.filter(**kwargs).distinct().order_by().values('text')]

    def _normalise_target_info(self, target, target_model):
        """Gets any additional target info from core_filters, and
        returns target, target_model, target_id, target_ct_id.
        
        ID will be retrieved for objects, but objects will not
        be retrieved from the ID.
        """
        core_filters = getattr(self, 'core_filters', {})
        target_ct_id = core_filters.get('target_ct__id__exact')
        target_id = core_filters.get('target_id__exact')
        if target_model is None and target is not None:
            target_model = target.__class__
        if target_ct_id is None and target_model is not None:
            target_ct_id = utils.get_content_type_id(target_model)
        if target_id is None and target is not None:
            target_id = utils.pk_to_str(target._get_pk_val(), target_ct_id)
        return (target, target_model, target_id, target_ct_id)

    def _normalise_creator_info(self, creator, creator_model):
        """Gets any additional creator info from core_filters, and
        returns creator, creator_model, creator_id, creator_ct_id.
        
        ID will be retrieved for objects, but objects will not
        be retrieved from the ID.
        """
        # Duplicate of above, but merging them will just obfuscate
        core_filters = getattr(self, 'core_filters', {})
        creator_ct_id = core_filters.get('creator_ct__id__exact', None)
        creator_id = core_filters.get('creator_id__exact', None)
        if creator_model is None and creator is not None:
            creator_model = creator.__class__
        if creator_ct_id is None and creator_model is not None:
            creator_ct_id = utils.get_content_type_id(creator_model)
        if creator_id is None and creator is not None:
            creator_id = utils.pk_to_str(creator._get_pk_val(), creator_ct_id)
        return (creator, creator_model, creator_id, creator_ct_id)

    def get_tag_summaries(self, target_model=None, creator_model=None, 
            target=None, creator=None, limit=None, order='count', text=None):
        """Returns a sequence (TagSummaryCollection) of TagSummary objects i.e.
        a tag 'text' value with its associated count.
        
        Use target_model, creator_model, target and creator to limit the query
        to the model types or specific objects.
        
        Use limit to specify that only the top 'n' should be returned.
        
        'order' can be 'count' (descending popularity) or 
        'text'.(alphabetical, ascending)
        
        'text' constrains the query to a single text value.

        """
        # We need to do GROUP BY etc, so it's easier to just construct
        # our own SQL
        cursor = connection.cursor()
        where = []
        params = []
        qn = backend.quote_name

        target, target_model, target_id, target_ct_id = self._normalise_target_info(target, target_model)
        creator, creator_model, creator_id, creator_ct_id = self._normalise_creator_info(creator, creator_model)
        
        if target_ct_id is not None:
            where.append('%s = %%s' % qn('target_ct_id'))
            params.append(target_ct_id)
            if target_id is not None:
                where.append('%s = %%s' % qn('target_id'))
                params.append(target_id)

        if creator_ct_id is not None:
            where.append('%s = %%s' % qn('creator_ct_id'))
            params.append(creator_ct_id)
            if creator_id is not None:
                where.append('%s = %%s' % qn('creator_id'))
                params.append(creator_id)

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
        sql +=  " GROUP BY %s "  % qn('text')
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

    @staticmethod
    def _normalise_text_textlist(text):
        # Normalise 'text'
        if isinstance(text, basestring):
            if ' ' in text:
                textlist = text.split()
            else:
                textlist = [text]
        else:
            # assume text is sequence
            textlist = text
        
        textlist = list(set(textlist)) # eliminate dupes
        text = ' '.join(textlist)
        return text, textlist

    def get_targets(self, text, limit=None, offset=None, target_model=None):
        """Returns target items that match the text value, as a sequence
        of two-tuples of (target, count)
        
        'text' can be a single string value, a space separated list
        or a list of strings.
        
        Items are ordered by popularity (count) descending.  If a single
        text value is provided, the count is the number of 'creator' objects
        that have tagged the object with that text. If a list of text values 
        is provided, the count becomes the product of those values.
        
        Use target_model to limit the targets to the specified model
        
        Use limit and offset to alter which/how many targets are found.
        
        
        """
        text, textlist = TagManager._normalise_text_textlist(text)
        
        # Normalise other vals.
        target, target_model, target_id, target_ct_id = self._normalise_target_info(None, target_model)
        
        # SQL:
        # SELECT COUNT(creator_id) as c, target_id, target_ct_id 
        #  FROM tagging_tag
        #   [ optional INNER JOINS for more than one text value]
        #  WHERE text = foo GROUP BY target_id, target_ct_id
        #   [ optional WHERE CLAUSES for more than one text value]
        #  ORDER BY c DESC LIMIT x
        
        # Really this should be something like COUNT(combination_of(creator_id, creator_ct_id)),
        # which you can't do, but actually, it makes no sense for one person ('creator'
        # object) to tag the same thing more than once with the same text, so multiple
        # rows with the same creator_id and 'text' *must* have different creator_ct_id,
        # (since we are grouping on the other fields),
        # so as long as we don't do 'DISTINCT', we will get accurate results.
        qn = backend.quote_name
        # SELECT
        tablename = qn(Tag._meta.db_table)

        tablealias = 0
        selectsql = "SELECT COUNT(tagtable0.creator_id) as c, tagtable0.target_id, tagtable0.target_ct_id "
        fromsql = " FROM %s as tagtable0" % tablename
        wheresql = " WHERE tagtable0.text = %s"
        params = [textlist.pop()]
        
        tablealias += 1

        # additional WHERE
        if target_ct_id is not None:
            wheresql += " AND tagtable0.target_ct_id = %s"
            params.append(target_ct_id)

        # Searching for more than one text value
        while len(textlist) > 0:
            fromsql += \
                (" INNER JOIN %s as tagtable%d "
                 "   ON tagtable0.target_id = tagtable%d.target_id " +
                 "  AND tagtable0.target_ct_id = tagtable%d.target_ct_id") \
                 % (tablename, tablealias, tablealias, tablealias)
            wheresql += \
                " AND tagtable%d.text = %%s" % tablealias
            params.append(textlist.pop())
            tablealias += 1
        
        # combine and continue
        sql = selectsql + ' ' + fromsql + ' ' + wheresql
        
        # GROUP BY and ORDER BY
        sql += " GROUP BY tagtable0.target_id, tagtable0.target_ct_id ORDER BY c DESC"
        
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
        tablename = qn(Tag._meta.db_table)        
        text, textlist = TagManager._normalise_text_textlist(text)
        target, target_model, target_id, target_ct_id = self._normalise_target_info(None, target_model)
        
        tablealias = 0
        selectsql = "SELECT DISTINCT tagtable0.target_ct_id, tagtable0.target_id"
        fromsql = " FROM %s as tagtable0" % tablename
        wheresql = " WHERE tagtable0.text = %s"
        params = [textlist.pop()]
        
        tablealias += 1

        # additional WHERE
        if target_ct_id is not None:
            wheresql += " AND tagtable0.target_ct_id = %s"
            params.append(target_ct_id)

        # TODO - reduce duplication with above
        # Searching for more than one text value
        while len(textlist) > 0:
            fromsql += \
                (" INNER JOIN %s as tagtable%d "
                 "   ON tagtable0.target_id = tagtable%d.target_id " +
                 "  AND tagtable0.target_ct_id = tagtable%d.target_ct_id") \
                 % (tablename, tablealias, tablealias, tablealias)
            wheresql += \
                " AND tagtable%d.text = %%s" % tablealias
            params.append(textlist.pop())
            tablealias += 1
        sql = selectsql + ' ' + fromsql + ' ' + wheresql
        sql = "SELECT COUNT(*) FROM (%s) as x" % sql
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return int(cursor.fetchone()[0])

class Tag(models.Model):
    text = models.CharField("Text", maxlength=32)
    target_id = models.CharField("'Target' ID", maxlength=64)
    target_ct = models.ForeignKey(ContentType, verbose_name="'Target' content type")
    creator_id = models.CharField("'creator' ID", maxlength=64)
    creator_ct = models.ForeignKey(ContentType, verbose_name="'creator' content type")
    added = models.DateTimeField("Date added", auto_now_add=True)
    
    target = GenericForeignKey('target_id', 'target_ct_id')
    creator = GenericForeignKey('creator_id', 'creator_ct_id')
    objects = TagManager()
    
    def __str__(self):
        return "%s tagged as %s by %s" % (self.target, self.text, self.creator)
        
    def render(self):
        """Returns a rendered (e.g. HTML) representation of the
        tag target.  Requires a 'renderer' to be registered first."""
        return utils.get_renderer(self.target_ct_id)(self.target)

    def count_tagged_by_others(self):
        """Returns the number of other 'creator' objects that have tagged
        the same object that this tag is for."""
        # only includes 'creator' objects of the same content type,
        # as the SQL is harder otherwise.
        
        # try cache first
        try:
            return self._count_tagged_by_others
        except AttributeError:
            pass
        # SELECT COUNT(DISTINCT(creator_id)) FROM "tagging_tag" 
        # WHERE target_ct_id = x AND target_id = y AND creator_ct_id = z AND NOT (creator_id = q)
        cursor = connection.cursor()
        qn = backend.quote_name
        sql = "SELECT COUNT(DISTINCT(%s)) FROM %s WHERE %s = %%s AND %s = %%s AND %s = %%s AND NOT (%s = %%s)" % \
                (qn('creator_id'), qn(Tag._meta.db_table), qn('target_ct_id'), qn('target_id'), qn('creator_ct_id'), qn('creator_id'))
        params = [self.target_ct_id, self.target_id, self.creator_ct_id, self.creator_id]
        cursor.execute(sql, params)
        retval = int(cursor.fetchone()[0])
        
        # cache so we can use it more cheaply in templates
        self._count_tagged_by_others = retval
        return retval
        
    def count_tagged_with_text(self):
        """Returns the total number of times that this target 
        has been tagged with this text."""

        # we could do this more efficiently if we didn't use self.target
        return Tag.objects.get_tag_summaries(target=self.target, text=self.text)[0].count

    class Meta:
        ordering = ('-added',)
    
    class Admin:
        list_display = (
            'text',
            'target',
            'creator',
            'added',
        )
        list_filter = (
            'target_ct',
            'creator_ct',
        )
        search_fields = ('text',)
