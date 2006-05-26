from cciw.cciwmain.models import Member, Post, Topic, Photo
from cciw.cciwmain.common import standard_extra_context
from django.http import Http404
from django.core import exceptions
from cciw.cciwmain.decorators import member_required
from cciw.middleware.threadlocals import get_current_member
from cciw.cciwmain import feeds
from lukeplant_me_uk.django.tagging import views as tagging_views
import lukeplant_me_uk.django.tagging.utils as tagging_utils
from lukeplant_me_uk.django.tagging.models import Tag

TAG_PAGINGATE_BY = 10

def index(request):
    extra_context=standard_extra_context(title='Tags')
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = True
    extra_context['tag_href_prefix'] = "/tags/"
    extra_context['atom_feed_title'] = "Atom feed for all tags."
    return tagging_views.recent_popular(request, creator_model=Member, template_name="cciw/tags/index.html",
                extra_context=extra_context, paginate_by=TAG_PAGINGATE_BY, 
                extra_handler=lambda request, queryset: feeds.handle_feed_request(request, feeds.TagFeed, query_set=queryset))

def members_tags(request, user_name):
    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404()

    extra_context=standard_extra_context(title="Tags created by %s" % member.user_name)
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = False
    extra_context['showtagtarget'] = True
    extra_context['tag_href_prefix'] = "/%s/tags/" % member.user_name
    return tagging_views.recent_popular(request, creator=member, template_name="cciw/tags/index.html",
                extra_context=extra_context, paginate_by=TAG_PAGINGATE_BY)

taggable_models = {'member': Member, 'post': Post, 'topic': Topic}

def _object_for_model_name_and_id(model_name, object_id):
    try:
        model = taggable_models[model_name]
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
    extra_context = standard_extra_context(title='Tags for %s' % obj)
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = False
    extra_context['showtagcounts'] = True
    extra_context['tag_href_prefix'] = "/tags/"
    return tagging_views.recent_popular(request, creator_model=Member, target=obj,
        template_name="cciw/tags/index.html", extra_context=extra_context,
        paginate_by=TAG_PAGINGATE_BY)

def tag_target_single_text(request, model_name, object_id, text):
    obj = _object_for_model_name_and_id(model_name, object_id)
    extra_context = standard_extra_context(title="'%s' tags for %s" % (text, obj))
    extra_context['tag_href_prefix'] = "/tags/"
    return tagging_views.recent_popular(request, creator_model=Member, target=obj,
        text=text, template_name="cciw/tags/tagdetail.html", 
        extra_context=extra_context, paginate_by=TAG_PAGINGATE_BY)
        
# /tags/text
def recent_and_popular_targets(request, text):
    extra_context = standard_extra_context(title="Items tagged as '%s'" % text)
    extra_context['showtagtext'] = False
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = True
    extra_context['showtagcounts'] = False
    extra_context['atom_feed_title'] = "Atom feed for '%s' tags." % text
    # Get 'popular targets for this tag'
    extra_context['popular_targets'] = Tag.objects.get_targets(text, limit=10)
            
    return tagging_views.recent_popular(request, text=text, creator_model=Member,
        extra_context=extra_context, template_name="cciw/tags/index.html",
        paginate_by=TAG_PAGINGATE_BY, extra_handler= \
            lambda request, queryset: feeds.handle_feed_request(request, feeds.text_tag_feed(text), query_set=queryset))

@member_required
def edit_tag(request, model_name, object_id):
    obj = _object_for_model_name_and_id(model_name, object_id)
    current_member = get_current_member()
    extra_context = standard_extra_context(title="Add or edit tags")
    return tagging_views.create_update(request, creator=current_member, target=obj,
        redirect_url=request.GET.get('r', None), extra_context=extra_context)

def search(request):
    extra_context = standard_extra_context(title="Tag search")
    text = request.GET.get('search', '')
    text = ' '.join(list(set(text.split()))[0:4]) # maximum of 4 different tags, so we don't generate daft SQL queries
    return tagging_views.targets_for_text(request, text, paginate_by=TAG_PAGINGATE_BY,
        template_name='cciw/tags/search.html', extra_context=extra_context)
