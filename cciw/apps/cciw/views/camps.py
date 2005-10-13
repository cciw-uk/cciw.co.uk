import datetime

from django.core.extensions import render_to_response
from django.utils.httpwrappers import HttpResponse
from django.core.exceptions import Http404

from django.models.camps import camps
from django.models.sitecontent import htmlchunks
from django.models.forums import forums, topics, gallerys, photos

from cciw.apps.cciw.common import *
from cciw.apps.cciw.settings import *
import cciw.apps.cciw.utils as utils
import forums as forums_views


def index(request, year = None):
	if (year == None):
		all_camps = camps.get_list(order_by=['-year','number'])
	else:
		year = int(year)  # year is result of regex match
		all_camps = camps.get_list(year__exact=year, order_by=['number'])
		if len(all_camps) == 0:
			raise Http404
	
	return render_to_response('camps/index', 
			StandardContext(request, {'camps': all_camps},
					title="Camp forums and photos"))

def detail(request, year, number):
	try:
		camp = camps.get_object(year__exact=int(year), number__exact=int(number))
	except camps.CampDoesNotExist:
		raise Http404
		
	c = StandardContext(request, {'camp': camp }, 
							title = camp.niceName())
	
	
	if camp.endDate < datetime.date.today():
		c['camp_is_past'] = True
		c['breadcrumb'] = create_breadcrumb(year_forum_breadcrumb(str(camp.year)) + [camp.niceName()])	
	else:
		c['breadcrumb'] = create_breadcrumb([standard_subs('<a href="/thisyear/">Camps {{thisyear}}</a>'), "Camp " + number])
	return render_to_response('camps/detail', c)

	
def thisyear(request):
	c = StandardContext(request, title="Camps " + str(THISYEAR))
	htmlchunks.renderIntoContext(c, {
		'introtext': 'camp_dates_intro_text',
		'outrotext': 'camp_dates_outro_text'})
	c['camps'] = camps.get_list(year__exact=THISYEAR, order_by=['site_id', 'number'])	
	
	return render_to_response('camps/thisyear',c)

def get_forum_for_camp(camp):
	location = camp.get_absolute_url()[1:] + 'forum/'

	forum = None
	try:
		forum = forums.get_object(location__exact=location)
	except forums.ForumDoesNotExist:
		if not camp.endDate is None and \
			camp.endDate <= datetime.date.today():
			# If the forum doesn't exist, but should, we should create it
			forum = forums.Forum(location = location, open = True)
			forum.save()
	return forum

def get_gallery_for_camp(camp):
	location = camp.get_absolute_url()[1:] + 'photos/'
	gallery = None
	try:
		gallery = gallerys.get_object(location__exact=location)
	except gallerys.GalleryDoesNotExist:
		if not camp.endDate <= datetime.date.today():
			# if the gallery does not exist yet, but should, create it
			gallery = gallerys.Gallery(location = location)
			gallery.save()
	return gallery

def forum(request, year, number):

	if number == 'all':
		camp = None
		location = request.path[1:]
		try:
			forum = forums.get_object(location__exact=location)
		except forums.ForumDoesNotExist:
			# TODO: if any camps from that year are past, create it
			# TODO: but if it's an old forum, that would be closed immediately, don't bother
			raise Http404
		title="General forum " + str(year)
		breadcrumb_extra = year_forum_breadcrumb(year)
		
	else:
		try:
			camp = camps.get_object(year__exact=int(year), number__exact=int(number))
		except camps.CampDoesNotExist:
			raise Http404

		forum = get_forum_for_camp(camp)
		if forum is None:
			raise Http404
		title=camp.niceName() + " - Forum"
		breadcrumb_extra = camp_forum_breadcrumb(camp)

	# TODO - some extra context vars, for text to show before the topic list
	
	ec = standard_extra_context(request, title = title)
	return forums_views.topicindex(request, extra_context = ec, forum = forum, 
		template_name = 'forums/topicindex', breadcrumb_extra = breadcrumb_extra)

def topic(request, year, number, topicnumber):

	if number == 'all':
		camp = None
		breadcrumb_extra = year_forum_breadcrumb(year)
	else:
		try:
			camp = camps.get_object(year__exact=int(year), number__exact=int(number))
		except camps.CampDoesNotExist:
			raise Http404
		breadcrumb_extra = camp_forum_breadcrumb(camp)
			
	return forums_views.topic(request, topicid = topicnumber, title_start = 'Topic',
		template_name = 'forums/topic', breadcrumb_extra = breadcrumb_extra)		

def gallery(request, year, number):
	try:
		camp = camps.get_object(year__exact=int(year), number__exact=int(number))
	except camps.CampDoesNotExist:
		raise Http404

	gallery = get_gallery_for_camp(camp)
	if gallery is None:
		raise Http404

	breadcrumb_extra = camp_forum_breadcrumb(camp)

	# TODO - some extra context vars, for text to show before the topic list
	
	ec = standard_extra_context(request, title = camp.niceName() + " - Photos")
	return forums_views.photoindex(request, gallery, ec, breadcrumb_extra)

def oldcampgallery(request, year, galleryname):
	try:
		gallery = gallerys.get_object(location__exact = 'camps/' + year + '/' + galleryname + '/photos/')
	except gallerys.GalleryDoesNotExist:
		raise Http404

	breadcrumb_extra = year_forum_breadcrumb(year) + [utils.unslugify(galleryname)]
	
	ec = standard_extra_context(request, title = utils.unslugify(year+", " + galleryname) + " - Photos")
	return forums_views.photoindex(request, gallery, ec, breadcrumb_extra)

	
def photo(request, year, number, photonumber):
	try:
		camp = camps.get_object(year__exact=int(year), number__exact=int(number))
	except camps.CampDoesNotExist:
		raise Http404
	breadcrumb_extra = camp_forum_breadcrumb(camp)
	
	# TODO - permissions and hidden photos
	try:
		photo = photos.get_object(id__exact = int(photonumber))
	except photos.PhotoDoesNotExist:
		raise Http404
	
	ec = standard_extra_context(request, title = "Photos: " + camp.niceName())
	
	return forums_views.photo(request, photo, ec, breadcrumb_extra)

def oldcampphoto(request, year, galleryname, photonumber):
	# Do need to check the gallery exists, just for checking the URL
	try:
		gallery = gallerys.get_object(location__exact = 'camps/' + year + '/' + galleryname + '/photos/')
	except gallerys.GalleryDoesNotExist:
		raise Http404

	breadcrumb_extra = year_forum_breadcrumb(year) + [utils.unslugify(galleryname)]
	
	# TODO - permissions and hidden photos
	try:
		photo = photos.get_object(id__exact = int(photonumber))
	except photos.PhotoDoesNotExist:
		raise Http404
	
	ec = standard_extra_context(request, title = utils.unslugify(year+", " + galleryname) + " - Photos")	
	return forums_views.photo(request, photo, ec, breadcrumb_extra)

	
def camp_forum_breadcrumb(camp):
	return ['<a href="/camps/">Forums and photos</a>', '<a href="/camps/#year' + str(camp.year) + '">' + str(camp.year) + '</a>', camp.get_link()]
	
def year_forum_breadcrumb(year):
	return ['<a href="/camps/">Forums and photos</a>', '<a href="/camps/#year' + year + '">' + utils.unslugify(year) + '</a>']
