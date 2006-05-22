from cciw.tagging import views as tagging_views
import cciw.tagging.utils as tagging_utils
from cciw.tagging.models import Tag
from cciw.cciwmain.models import Member, Post, Topic, Photo
from cciw.cciwmain.common import standard_extra_context
from django.http import Http404
from django.core import exceptions

def index(request):
    extra_context=standard_extra_context(title='Tags')
    extra_context['showtagtext'] = True
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = True
    extra_context['tag_href_prefix'] = "/tags/"
    return tagging_views.recent_popular(request, by_model=Member, template_name="cciw/tags/index.html",
                extra_context=extra_context)

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
    return tagging_views.recent_popular(request, by=member, template_name="cciw/tags/index.html",
                extra_context=extra_context)

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
    return tagging_views.recent_popular(request, by_model=Member, target=obj,
        template_name="cciw/tags/index.html", extra_context=extra_context)

def tag_target_single_text(request, model_name, object_id, text):
    obj = _object_for_model_name_and_id(model_name, object_id)
    extra_context = standard_extra_context(title="'%s' tags for %s" % (text, obj))
    extra_context['tag_href_prefix'] = "/tags/"
    return tagging_views.recent_popular(request, by_model=Member, target=obj,
        text=text, template_name="cciw/tags/tagdetail.html", extra_context=extra_context)
        
def recent_and_popular_targets(request, text):
    extra_context = standard_extra_context(title="Items tagged as '%s'" % text)
    extra_context['showtagtext'] = False
    extra_context['showtaggedby'] = True
    extra_context['showtagtarget'] = True
    extra_context['showtagcounts'] = False
    
    # Get 'popular targets for this tag'
    extra_context['popular_targets'] = Tag.objects.get_targets(text, limit=10)
            
    return tagging_views.recent_popular(request, text=text, by_model=Member,
        extra_context=extra_context, template_name="cciw/tags/index.html")
