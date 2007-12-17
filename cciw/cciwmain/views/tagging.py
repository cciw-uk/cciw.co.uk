from cciw.cciwmain.models import Member, Post, Topic, Photo
from cciw.cciwmain.common import standard_extra_context, create_breadcrumb
from django.http import Http404, HttpResponseRedirect
from django.core import exceptions
from cciw.cciwmain.decorators import member_required
from cciw.middleware.threadlocals import get_current_member
from cciw.cciwmain import feeds
from cciw.tagging import views as tagging_views
import cciw.tagging.utils as tagging_utils
from cciw.tagging.models import Tag

TAG_PAGINGATE_BY = 8
SEARCH_PAGINGATE_BY = 20

def index(request):
    extra_context=standard_extra_context(title='Tags')
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = True
    extra_context['tag_href_prefix'] = u"/tags/"
    extra_context['atom_feed_title'] = u"Atom feed for all tags."
    
    def feed_handler(request, queryset):
        return feeds.handle_feed_request(request, feeds.TagFeed, query_set=queryset)
        
    return tagging_views.recent_popular(request, creator_model=Member, template_name="cciw/tags/index.html",
                extra_context=extra_context, paginate_by=TAG_PAGINGATE_BY, 
                extra_handler=feed_handler, popular_tags_order='count')

def members_tags(request, user_name):
    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404()

    extra_context=standard_extra_context(title=u"Tags created by %s" % member.user_name)
    extra_context['member'] = member
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = False
    extra_context['showtagtarget'] = True
    extra_context['tag_href_prefix'] = u"/members/%s/tags/" % member.user_name
    extra_context['atom_feed_title'] = u"Atom feed for tags created by %s." % member.user_name
    extra_context['breadcrumb'] = create_breadcrumb([u'<a href="/tags/">All tags</a>', u'Tags created by %s' % member.get_link()])
    
    def feed_handler(request, queryset):
        return feeds.handle_feed_request(request, feeds.member_tag_feed(member), query_set=queryset)
    
    return tagging_views.recent_popular(request, creator=member, template_name="cciw/tags/index.html",
                extra_context=extra_context, paginate_by=TAG_PAGINGATE_BY,
                extra_handler=feed_handler, popular_tags_order='count')

def members_tags_single_text(request, user_name, text):
    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404()

    extra_context=standard_extra_context(title=u"'%s' tags created by %s" % (text, user_name))
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = False
    extra_context['showtagtarget'] = True
    extra_context['tag_href_prefix'] = u"/members/%s/tags/" % user_name
    extra_context['atom_feed_title'] = u"Atom feed for '%s' created by %s" % (text, user_name)
    extra_context['breadcrumb'] = create_breadcrumb([
            u'<a href="/tags/%s/">All \'%s\' tags</a>' % (text, text),
            u'<a href="/members/%s/tags/">All tags created by %s</a>' % (user_name, user_name),
            u'\'%s\' tags created by %s' % (text, user_name)])
        
    def feed_handler(request, queryset):
        return feeds.handle_feed_request(request, 
            feeds.member_tag_text_feed(member, text), query_set=queryset)
    
    return tagging_views.recent_popular(request, creator=member, text=text,
                template_name="cciw/tags/index.html",extra_context=extra_context, 
                paginate_by=TAG_PAGINGATE_BY, extra_handler=feed_handler)


taggable_models = { Member: 'member', Post: 'post', Topic: 'topic', Photo: 'photo' }
taggable_models_inv = {'member': Member, 'post': Post, 'topic': Topic, 'photo': Photo}


def _object_for_model_name_and_id(model_name, object_id):
    try:
        model = taggable_models_inv[model_name]
    except KeyError:
        raise Http404()

    ct = tagging_utils.get_content_type_id(model)
    pk = tagging_utils.pk_from_str(object_id, ct)
    try:
        return model._default_manager.get(pk=pk)
    except exceptions.ObjectDoesNotExist:
        raise Http404()

def tag_target(request, model_name, object_id):
    obj = _object_for_model_name_and_id(model_name, object_id)
    extra_context = standard_extra_context(title=u'Tags for %s' % obj)
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = False
    extra_context['showtagcounts'] = True    
    extra_context['tag_href_prefix'] = u"/tags/"
    extra_context['atom_feed_title'] = u"Atom feed for %s" % obj
    extra_context['breadcrumb'] = create_breadcrumb([
            u'<a href="/tags/">All tags</a>',
            u'Tags for "%s"' % obj
            ])
    
    def feed_handler(request, queryset):
        return feeds.handle_feed_request(request, feeds.target_tag_feed(obj), 
                    query_set=queryset)
    
    return tagging_views.recent_popular(request, creator_model=Member, target=obj,
        template_name="cciw/tags/index.html", extra_context=extra_context,
        paginate_by=TAG_PAGINGATE_BY, extra_handler=feed_handler)

def tag_target_single_text(request, model_name, object_id, text):
    text = tagging_utils.strip_unsafe_chars(text)
    obj = _object_for_model_name_and_id(model_name, object_id)
    extra_context = standard_extra_context(title=u"'%s' tags for %s" % (text, obj))
    extra_context['tag_href_prefix'] = u"/tags/"
    extra_context['breadcrumb'] = create_breadcrumb([
            u'<a href="/tags/">All tags</a>', 
            u'<a href="../">All tags for this item</a> :: %s' % text
            ])
    return tagging_views.recent_popular(request, creator_model=Member, target=obj,
        text=text, template_name="cciw/tags/tagdetail.html", 
        extra_context=extra_context, paginate_by=TAG_PAGINGATE_BY)

def single_tag(request, model_name, object_id, text, tag_id):
    """View that exists merely to give individual Tag objects unique URLs"""
    # Not useful to show anything here, so redirect.
    return HttpResponseRedirect("../")

# /tags/text
def recent_and_popular_targets(request, text):
    text = tagging_utils.strip_unsafe_chars(text)
    extra_context = standard_extra_context(title=u"Items tagged as '%s'" % text)
    extra_context['showtagtext'] = False
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = True
    extra_context['showtagcounts'] = False
    extra_context['breadcrumb'] = create_breadcrumb([
            u'<a href="/tags/">All tags</a> :: %s' % text])
    extra_context['atom_feed_title'] = u"Atom feed for '%s' tags." % text
    # Get 'popular targets for this tag'
    extra_context['popular_targets'] = Tag.objects.get_targets(text, limit=10)
    
    def feed_handler(request, queryset):
        return feeds.handle_feed_request(request, feeds.text_tag_feed(text), query_set=queryset)
        
    return tagging_views.recent_popular(request, text=text, creator_model=Member,
        extra_context=extra_context, template_name="cciw/tags/index.html",
        paginate_by=TAG_PAGINGATE_BY, extra_handler=feed_handler)

@member_required
def edit_tag(request, model_name, object_id):
    obj = _object_for_model_name_and_id(model_name, object_id)
    current_member = get_current_member()
    extra_context = standard_extra_context(title=u"Add or edit tags")
    return tagging_views.create_update(request, creator=current_member, target=obj,
        redirect_url=request.GET.get('r', None), extra_context=extra_context)

def search(request):
    extra_context = standard_extra_context(title="Tag search")
    extra_context['breadcrumb'] = create_breadcrumb([
            u'<a href="/tags/">Browse tags</a> :: Search tags'
            ])
    text = tagging_utils.strip_unsafe_chars(request.GET.get('search', ''))
    text = ' '.join(list(set(text.split()))[0:4]) # maximum of 4 different tags, so we don't generate daft SQL queries
    return tagging_views.targets_for_text(request, text, paginate_by=SEARCH_PAGINGATE_BY,
        template_name='cciw/tags/search.html', extra_context=extra_context)
