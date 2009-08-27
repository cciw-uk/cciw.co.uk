import datetime

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.conf import settings

from cciw.cciwmain.models import Camp, HtmlChunk, Forum, Gallery, Photo
from cciw.cciwmain.common import standard_extra_context, create_breadcrumb, get_thisyear, standard_subs
from cciw.cciwmain.decorators import member_required
from cciw.cciwmain.templatetags import bbcode
import cciw.cciwmain.utils as utils
import cciw.cciwmain.views.forums as forums_views


def index(request, year=None):
    """
    Displays a list of all camps, or all camps in a given year.

    Template - ``cciw/camps/index.html``

    Context:
        show_ancient
            True if the really old camps should be shown
        camps
            List of all Camp objects (or all Camp objects in the specified year).
    """
    c = standard_extra_context()
    c['title'] = u"Camp forums and photos"
    all_camps = Camp.objects.filter(end_date__lte=datetime.datetime.today())
    if (year == None):
        camps = all_camps.order_by('-year', 'number')
        c['show_ancient'] = True
    else:
        year = int(year)  # year is result of regex match
        camps = all_camps.filter(year=year)\
                                .order_by('-year', 'number')
        if len(camps) == 0:
            raise Http404
    c['camps'] = camps;

    return render_to_response('cciw/camps/index.html',
            context_instance=RequestContext(request, c))

def detail(request, year, number):
    """
    Shows details of a specific camp.

    Context:
        camp
            Camp objects
        camp_is_past
            True if this camp is now finished.
    """

    try:
        camp = Camp.objects.get(year=int(year), number=int(number))
    except Camp.DoesNotExist:
        raise Http404

    c = RequestContext(request, standard_extra_context())
    c['camp'] = camp
    c['title'] = camp.nice_name

    if camp.is_past():
        c['breadcrumb'] = create_breadcrumb(year_forum_breadcrumb(unicode(camp.year)) + [camp.nice_name])
    else:
        c['breadcrumb'] = create_breadcrumb([standard_subs(u'<a href="/thisyear/">Camps {{thisyear}}</a>'), "Camp " + number])
    return render_to_response('cciw/camps/detail.html', context_instance=c)

def thisyear(request):
    c = RequestContext(request,
                       standard_extra_context(title=u"Camps %d" % get_thisyear()))
    c['camps'] = Camp.objects.filter(year=get_thisyear()).order_by('site', 'number')
    return render_to_response('cciw/camps/thisyear.html', context_instance=c)

def get_forum_for_camp(camp):
    location = camp.get_absolute_url()[1:] + 'forum/'

    forum = None
    try:
        forum = Forum.objects.get(location=location)
    except Forum.DoesNotExist:
        # Self maintenance
        if not camp.end_date is None and camp.is_past():
            # If the forum doesn't exist, but should, we should create it
            forum = Forum(location=location, open=True)
            forum.save()
    return forum

def get_gallery_for_camp(camp):
    location = camp.get_absolute_url()[1:] + 'photos/'
    gallery = None
    try:
        gallery = Gallery.objects.get(location=location)
    except Gallery.DoesNotExist:
        # Self maintenance
        if camp.is_past():
            # if the gallery does not exist yet, but should, create it
            gallery = Gallery(location = location)
            gallery.save()
    return gallery

def _get_forum_for_path_and_year(location, year):
    """Gets the 'general' forum that lives at the specified location,
    for the given year."""
    try:
        forum = Forum.objects.get(location=location)
    except Forum.DoesNotExist:
        # Self maintenance
        # If any camps from that year are finished, create it
        if Camp.objects.filter(year=year,
                end_date__lte=datetime.date.today()).count() > 0:
            forum = Forum(location='camps/%s/all/forum/' % year)
        else:
            raise Http404
        # If it's an old forum, close it
        if Camp.objects.filter(year=year + 1,
                end_date__lte=datetime.date.today()).count() > 0:
            forum.open = False
        else:
            forum.open = True
        forum.save()
    return forum


def forum(request, year, number):
    """
    Displays a topic index for a camp or year.  If number == 'all', the
    general forum will be shown."""
    if number == 'all':
        camp = None
        forum = _get_forum_for_path_and_year(request.path[1:], int(year))
        title = u"General forum %s" % year
        breadcrumb_extra = year_forum_breadcrumb(year)

    else:
        try:
            camp = Camp.objects.get(year=int(year), number=int(number))
        except Camp.DoesNotExist:
            raise Http404

        forum = get_forum_for_camp(camp)
        if forum is None:
            raise Http404
        title = u"%s - Forum" % camp.nice_name
        breadcrumb_extra = camp_forum_breadcrumb(camp)

    c = standard_extra_context(title=title)
    return forums_views.topicindex(request, extra_context=c, forum=forum,
        template_name='cciw/forums/topicindex.html', breadcrumb_extra=breadcrumb_extra)

def _get_camp_and_breadcrumb(year, number):
    """Get camp and breadcrumb for the supplied year and number,
        throwing 404's if the camp is invalid."""
    if number == 'all':
        camp = None
        breadcrumb_extra = year_forum_breadcrumb(year)
    else:
        try:
            camp = Camp.objects.get(year=int(year), number=int(number))
        except Camp.DoesNotExist:
            raise Http404
        breadcrumb_extra = camp_forum_breadcrumb(camp)
    return camp, breadcrumb_extra

def topic(request, year, number, topicnumber):
    """Displays a topic for a camp."""
    camp, breadcrumb_extra = _get_camp_and_breadcrumb(year, number)

    return forums_views.topic(request, topicid=topicnumber, title_start=u'Topic',
        template_name='cciw/forums/topic.html', breadcrumb_extra=breadcrumb_extra)

def add_topic(request, year, number):
    camp, breadcrumb_extra = _get_camp_and_breadcrumb(year, number)
    return forums_views.add_topic(request, breadcrumb_extra)

def add_news(request, year, number):
    camp, breadcrumb_extra = _get_camp_and_breadcrumb(year, number)
    return forums_views.add_news(request, breadcrumb_extra)

def edit_poll(request, year, number, poll_id=None):
    camp, breadcrumb_extra = _get_camp_and_breadcrumb(year, number)
    return forums_views.edit_poll(request, poll_id, breadcrumb_extra)

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

    try:
        photo = Photo.objects.get(id=int(photonumber))
    except Photo.DoesNotExist:
        raise Http404

    ec = standard_extra_context(title=u"Photos: %s" % camp.nice_name)

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
        photo = Photo.all_objects.get(id=int(photonumber))
    except Photo.DoesNotExist:
        raise Http404

    ec = standard_extra_context(title=u"%s, %s - Photos" %
                                (utils.unslugify(year), utils.unslugify(galleryname)))
    return forums_views.photo(request, photo, ec, breadcrumb_extra)

def camp_forum_breadcrumb(camp):
    return [u'<a href="/camps/">Forums and photos</a>',
            u'<a href="/camps/#year%d">%d</a>' % (camp.year, camp.year),
            camp.get_link()]

def year_forum_breadcrumb(year):
    # NB: 'year' may be a string like 'Ancient'
    return [u'<a href="/camps/">Forums and photos</a>',
            u'<a href="/camps/#year%s">%s</a>' % (year, utils.unslugify(year)) ]
