import datetime

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, Http404

from cciw.cciwmain.models import Camp, HtmlChunk, Forum, Gallery, Photo
from cciw.cciwmain.common import *
from cciw.cciwmain.settings import THISYEAR
import cciw.cciwmain.utils as utils
import forums as forums_views


def index(request, year=None):
    if (year == None):
        all_camps = Camp.objects.order_by('-year', 'number')
    else:
        year = int(year)  # year is result of regex match
        all_camps = Camp.objects.filter(year=year)\
                                .order_by('-year', 'number')
        if len(all_camps) == 0:
            raise Http404
    
    ec = standard_extra_context()
    ec['camps'] = all_camps;
    ec['title'] ="Camp forums and photos"
    return render_to_response('cciw/camps/index', 
            context_instance=RequestContext(request, ec))

def detail(request, year, number):
    try:
        camp = Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist:
        raise Http404
    
    c = RequestContext(request, standard_extra_context())
    c['camp'] = camp
    c['title'] = camp.nice_name
    
    if camp.end_date < datetime.date.today():
        c['camp_is_past'] = True
        c['breadcrumb'] = create_breadcrumb(year_forum_breadcrumb(str(camp.year)) + [camp.nice_name])    
    else:
        c['breadcrumb'] = create_breadcrumb([standard_subs('<a href="/thisyear/">Camps {{thisyear}}</a>'), "Camp " + number])
    return render_to_response('cciw/camps/detail', context_instance=c)

def thisyear(request):
    c = RequestContext(request, standard_extra_context(title="Camps " + str(THISYEAR)))
    c['introtext'] = HtmlChunk(name='camp_dates_intro_text').render(request)
    c['outrotext'] = HtmlChunk(name='camp_dates_outro_text').render(request)

    return render_to_response('cciw/camps/thisyear', context_instance=c)

def get_forum_for_camp(camp):
    location = camp.get_absolute_url()[1:] + 'forum/'

    forum = None
    try:
        forum = Forum.objects.get(location=location)
    except Forum.DoesNotExist:
        if not camp.end_date is None and \
            camp.end_date <= datetime.date.today():
            # If the forum doesn't exist, but should, we should create it
            forum = Forum(location = location, open = True)
            forum.save()
    return forum

def get_gallery_for_camp(camp):
    location = camp.get_absolute_url()[1:] + 'photos/'
    gallery = None
    try:
        gallery = Gallery.objects.get(location=location)
    except Gallery.DoesNotExist:
        if not camp.end_date <= datetime.date.today():
            # if the gallery does not exist yet, but should, create it
            gallery = Gallery(location = location)
            gallery.save()
    return gallery

def forum(request, year, number):

    if number == 'all':
        camp = None
        location = request.path[1:]
        try:
            forum = Forum.objects.get(location=location)
        except Forum.DoesNotExist:
            # TODO: if any camps from that year are past, create it
            # TODO: but if it's an old forum, that would be closed immediately, don't bother
            raise Http404
        title="General forum " + str(year)
        breadcrumb_extra = year_forum_breadcrumb(year)
        
    else:
        try:
            camp = Camp.objects.get(year=int(year), number=int(number))
        except Camp.DoesNotExist:
            raise Http404

        forum = get_forum_for_camp(camp)
        if forum is None:
            raise Http404
        title=camp.nice_name + " - Forum"
        breadcrumb_extra = camp_forum_breadcrumb(camp)

    # TODO - some extra context vars, for text to show before the topic list
    
    ec = standard_extra_context(title = title)
    return forums_views.topicindex(request, extra_context=ec, forum=forum, 
        template_name = 'cciw/forums/topicindex', breadcrumb_extra=breadcrumb_extra)

def topic(request, year, number, topicnumber):

    if number == 'all':
        camp = None
        breadcrumb_extra = year_forum_breadcrumb(year)
    else:
        try:
            camp = Camp.objects.get(year=int(year), number=int(number))
        except Camp.DoesNotExist:
            raise Http404
        breadcrumb_extra = camp_forum_breadcrumb(camp)
            
    return forums_views.topic(request, topicid=topicnumber, title_start='Topic',
        template_name='cciw/forums/topic', breadcrumb_extra=breadcrumb_extra)        

def gallery(request, year, number):
    try:
        camp = Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist:
        raise Http404

    gallery = get_gallery_for_camp(camp)
    if gallery is None:
        raise Http404

    breadcrumb_extra = camp_forum_breadcrumb(camp)

    # TODO - some extra context vars, for text to show before the topic list
    
    ec = standard_extra_context(title=camp.nice_name + " - Photos")
    return forums_views.photoindex(request, gallery, ec, breadcrumb_extra)

def oldcampgallery(request, year, galleryname):
    try:
        gallery = Gallery.objects.get(location='camps/%s/%s/photos/' % (year, galleryname))
    except Gallery.DoesNotExist:
        raise Http404

    breadcrumb_extra = year_forum_breadcrumb(year) + [utils.unslugify(galleryname)]
    
    ec = standard_extra_context(title=utils.unslugify(year+", " + galleryname) + " - Photos")
    return forums_views.photoindex(request, gallery, ec, breadcrumb_extra)

def photo(request, year, number, photonumber):
    try:
        camp = Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist:
        raise Http404
    breadcrumb_extra = camp_forum_breadcrumb(camp)
    
    # TODO - permissions and hidden photos
    try:
        photo = Photo.objects.get(id=int(photonumber))
    except Photo.DoesNotExist:
        raise Http404
    
    ec = standard_extra_context(title="Photos: " + camp.nice_name)
    
    return forums_views.photo(request, photo, ec, breadcrumb_extra)

def oldcampphoto(request, year, galleryname, photonumber):
    # Do need to check the gallery exists, just for checking the URL
    try:
        gallery = Gallery.objects.get(location= 'camps/%s/%s/photos/' % (year, galleryname))
    except Gallery.DoesNotExist:
        raise Http404

    breadcrumb_extra = year_forum_breadcrumb(year) + [utils.unslugify(galleryname)]
    
    # TODO - permissions and hidden photos
    try:
        photo = Photo.objects.get(id=int(photonumber))
    except Photo.DoesNotExist:
        raise Http404
    
    ec = standard_extra_context(title=utils.unslugify(year+", " + galleryname) + " - Photos")    
    return forums_views.photo(request, photo, ec, breadcrumb_extra)

    
def camp_forum_breadcrumb(camp):
    return ['<a href="/camps/">Forums and photos</a>', '<a href="/camps/#year' + str(camp.year) + '">' + str(camp.year) + '</a>', camp.get_link()]
    
def year_forum_breadcrumb(year):
    return ['<a href="/camps/">Forums and photos</a>', '<a href="/camps/#year' + year + '">' + utils.unslugify(year) + '</a>']
