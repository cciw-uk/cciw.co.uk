# Migration script from old flatfiles
# to django
import devel
import os
from datetime import datetime
from datetime import date

from migrate_html import *

# import model *modules* from *packages*
from django.models.camps import *
from django.models.members import *
from django.models.polls import *
from django.models.posts import *
from django.models.photos import *
from django.models.forums import *
from django.models.sitecontent import *

# Config
PREFIX = '/home/httpd/www.cciw.co.uk/web/data/'

# Utility functions

# list that generates empty string items if you try to access out of bounds
# (matches our flatfiles and PHP arrays)
class LazyList(list):
	def __getitem__(self, index):
		if index >= len(self):
			return ""
		else:
			return list.__getitem__(self, index)

def getBool(stringData):
	"""Use instead of bool(int()) if empty data is allowed"""
	if len(stringData) == 0:
		return False
	else:
		return bool(int(stringData))

	
def getInt(stringData):
	"""Use instead of int() if empty data is allowed"""
	if len(stringData) == 0:
		return 0
	else:
		return int(stringData)

def getTable(filename, fieldSep="\t"):
	rows = []
	for line in file(filename):
		line = line.strip("\r\n")
		if len(line) == 0: continue
		lineData = LazyList(line.split(fieldSep))
		rows.append(lineData)
	return rows

def fix_bbcode(message):
	emoticonreplacements = (
		('[:anvil:]', ':anvil:'),
		('[:bandit:]', ':bandit'),
		('[:chop:]', ':chop:'),
		('[:biggun:]', ':biggun:'),
		('[:mouthful:]', ':mouthful:'),
		('[:gun:]', ':gun:'),
		('[:box:]', ':box:'),
		('[:gallows:]', ':gallows:'),
		('[:jedi:]', ':jedi:'),
		('[:bosh:]', ':bosh:'),
		('[:jonisanidiot:]', ':saw:'),
		('[:iwin:]', ':stupid:')
	)
	for icon in emoticonreplacements:
		message = message.replace(icon[0], icon[1])
	# TODO - misc transformations on messages, especially URLs
	return message

def remap_url(url):
	# TODO - probably easiest is a manual list, since
	# there are v few in current DB
	return url

###########################################################################################
#                   SITES
# mainly manual
def migrateSites():
	
	try:
		site1 = sites.get_object(shortName__exact="Brynglas Farm")
	except sites.SiteDoesNotExist:
		site1 = sites.Site(shortName="Brynglas Farm", longName="Brynglas Farm, Tywyn")
	site1.info = """
	 <address>Brynglas Farm,<br/>
Bryncug,<br/>
 Tywyn, <br/>
 Gwynedd, <br/>
 LL36 9PY, <br/>
 Phone 01654 710544 <br/>
 </address>
   
 <p>The Brynglas site is a large field on Brynglas farm, very close to the Tal-y-Llyn 
 railway - in fact you have to cross the railway (twice!) as you come through the 
 farm onto the campsite. The campers and officers are all in tents, with the exception 
 of some of the more pampered leaders and chaplains, and the kitchen and toilets are 
 also under canvas. The ample space means that the camps have a nominal capacity of 75, 
 but more can be accomodated.
</p>
 <div class='sitephoto'>
  <img src="{{media}}photos/2000-tywyn-site1b.jpeg" width="500" height="375" alt="Brynglas Farm photo 1" />
 </div>
 <br/>
 
 <p>The camp site provides plenty to do with a large football pitch, volleyball area,
 small hills to climb, a stream , as well as table tennis and other games in the main 
 marquee. The site, along with the surrounding fields, make it a great place for wide games.
 </p>
 
 <div class='sitephoto'>
  <img src="{{media}}photos/1999-bg-pyramids.jpeg" width="400" height="283" alt="Brynglas Farm photo 2" />
  <p><b>"It doesn't hurt, honest!"</b></p>
 </div>
 
 <p>The site is close to Tywyn (a small town with most amenities including a well served 
 railway station) - it only takes 10 minutes by car from camp to Tywyn. The shops there, 
 particularly the honey ice-cream factory, are popular with campers, and the leisure 
 centre with its swimming pool and showers are increasingly popular as the week progresses 
 (since the camp site does not have showers )! Just past Tywyn is Broadwater, which 
 is a great site for canoing and raft-building. The camp site is also 
 quite close to Cader Idris, which is usually climbed during the course of 
 the week, and also to the picturesque Dolgoch Falls.
</p>
 
<div class='sitephoto'>
  <img src="{{media}}photos/1999-dolgoch_falls.jpeg" width="387" height="262" alt="Brynglas Farm photo 3" />
  <p><b>Dolgoch Falls</b></p>
 </div>
 <br/>


 <h2><a name="aerialphoto">Aerial photo</a></h2>

 <p>Many thanks to W. Williams. Wynne for this fantastic aerial photograph of the Brynglas site</p>
 <div class='sitephoto'>
  <img src="{{media}}photos/2002-site1-aerial_400x300.jpeg" alt="aerial photo" />
  <p class="note" style="text-align: right">&copy;  W.Williams.Wynne (reproduced with permission).</p>
 </div>

 <p>Want this larger?  Try it in the following sizes, one of which should match your desktop.</p>
 <div class="sitephoto">
  <p><a href="{{media}}photos/2002-site1-aerial_640x480.jpeg">Small - 640 x 480, 55 kB</a></p>
  <p><a href="{{media}}photos/2002-site1-aerial_800x600.jpeg">Medium - 800 x 600, 80 kB</a></p>
  <p><a href="{{media}}photos/2002-site1-aerial_1024x768.jpeg">Large - 1024 x 768, 131 kB</a></p>
 </div>

"""
	site1.save()
	
	try:
		site2 = sites.get_object(shortName__exact="Llys Andreas")
	except sites.SiteDoesNotExist:
		site2 = sites.Site(shortName="Llys Andreas", longName="Llys Andreas, Barmouth")
	site2.info = """
	 <address>Llys Andreas Camp Site,<br/>
Ffordd Tyddyn Felin<br/>
 Tal-y-bont<br/>
 Barmouth<br/>
 LL43 2AU<br/>
 Pay phone: 01341 247526<br/>
 </address>
 <p>This site in Tal-y-bont is a smaller site than Tywyn, but still has plenty of room for the 50 campers it can accomodate. It has a main marquee for services and campsite activities, and a good sized playing space including a volleyball area. There is also a picturesque river just on the edge of the campsite.</p>

<p>There is a multi-purpose building which houses a kitchen and eating/games areas. The site also has a toilet and wash-block, (including showers) for both males and females.</p>

<p>Llys Andreas is very accessible, just two minutes off the main road between Barmouth & Harlech and just 10 mins from Tal-y-bont railway station. Barmouth also has a leisure centre, which has a five-a-side football pitch, as well a beach, a fair and plenty of shops. There is also a very pleasant beach much closer to Llys Andreas, which is a great spot for barbeques, bathing or bivouacking!
</p>

<div class='sitephoto'>
<img src="{{media}}photos/1999-la-volleyball.jpeg" width="352" height="288"  alt="photo 5" /><p><b>Volley Ball on site</b></p>
</div>

<div class='sitephoto'>
<img src="{{media}}photos/1999-la-river_bank.jpeg" width="352" height="288"  alt="photo 6" />
<p><b>River Bank near the site</b></p>
</div>
	"""
	site2.save()

###########################################################################################
#                 LEADERS + CHAPLAINS
def migrateLeaders():
	for p in persons.get_list():
		p.delete()
	for pdata in getTable(PREFIX+'leaders.data'):
		p = persons.Person(name = pdata[0], info = pdata[1])
		p.save()

###########################################################################################
#                PAST CAMPS

def migrateCamps():
	for c in reversed(getTable(PREFIX+'pastcamps.data')):
		try: year = int(c[0].split("-")[0])
		except: continue
		if year < 2000: continue # don't store
		
		try:
			number = int(c[0].split("-")[1])
		except:
			continue
		try:
			camp = camps.get_object(year__exact=year, number__exact=number)
		except camps.CampDoesNotExist:
			camp = camps.Camp(year = year, number = number)
			
		# ids of sites are the same as before:
		camp.site_id = sites.get_object(id__exact=int(c[1])).id
		camp.age = c[2]
		
	
		dates = c[3]
		# no date to 2000 and 2001 - make up some dates for now
		if year == 2000:
			dates = "July 1 - 8"
		else: 
			if year == 2001:
				dates = "July 7 - 14"
		
		dates = dates.replace("July", "Jul").replace("August", "Aug")
		start, end = dates.split("-")
		start = start.strip()
		end = end.strip()
		months = (("Jul", 7), ("Aug", 8))
		for monthtext, monthnum in months:
			if start.find(monthtext) != -1:
				start = start.replace(monthtext, "")
				startmonth = monthnum
		startday = int(start.strip())
		for monthtext, monthnum in months:
			if end.find(monthtext) != -1:
				end = end.replace(monthtext, "")
				endmonth = monthnum
			else:
				endmonth = startmonth
		endday = int(end.strip())
		
		camp.startDate = date(year, startmonth, startday)
		camp.endDate = date(year, endmonth, endday)
		
		camp.chaplain_id = persons.get_object(name__iexact=c[5]).id
		if len(c[6]) > 0:
			pcampyear, pcampnumber = map(int, c[6].split("-"))
			try:
				camp.previousCamp_id = camps.get_object(year__exact=pcampyear, number__exact=pcampnumber).id
			except:
				pass
			
		camp.save()
		
		leaders = c[4]
		if leaders.startswith('"'):
			leaders = [leader.strip() for leader in leaders.strip('"').split(",")]
		else:
			leaders = [leaders]
		camp.set_leaders([persons.get_object(name__iexact=name).id for name in leaders])
	
###########################################################################################
#             USERS
def migrateMembers():
	for u in members.get_list(): u.delete()
	def createMember(data, passwordsDict, lastSeenData):
		member = members.Member(userName=data[0])
		member.realName = data[1]
		member.email = data[3]
		member.password = passwordsDict.get(member.userName, members.encryptPassword('password1'))
		member.dateJoined = datetime.fromtimestamp(int(data[6]))
		member.lastSeen = lastSeenData.get(member.userName, member.dateJoined)
		member.showEmail = getBool(data[4])
		member.messageOption = getInt(data[5])
		member.comments = data[9]
		member.confirmSecret = data[13]
		member.moderated = getInt(data[15])
		member.hidden = getBool(data[17])
		member.banned = getBool(data[16])
		member.newEmail = data[22]
		member.bookmarksNotify = not getBool(data[18])
		return member
	
	# first get passwords from separate table
	passwords = {}
	for line in getTable(PREFIX+".htpasswd.online.2005-08-26",":"):
		passwords[line[0]] = line[1]
	
	lastSeenData = {}
	for line in getTable(PREFIX+"lastseen.data"):
		lastSeenData[line[0]] = datetime.fromtimestamp(int(line[1]))
		
	# Now parse members.data and pending_members.data
	for line in getTable(PREFIX+"members.data"):
		try:
			u = createMember(line,passwords, lastSeenData)
		except:
			print "Invalid data:"
			print line
			continue
		u.confirmed = True
		u.save()
	
	for line in getTable(PREFIX+"pending_members.data"):
		try:
			u = createMember(line,passwords, lastSeenData)
		except:
			print "Invalid data:"
			print line
			continue		
		u.confirmed = False
		u.save()

###########################################################################################
# Permissions (from old 'groups')
def migratePermissions():
	for p in permissions.get_list():
		p.delete()
	
	for id, description in ( 
		(permissions.SUPERUSER, "Administrator"),
		(permissions.USER_MODERATOR, "Member moderator"),
		(permissions.POST_MODERATOR, "Post moderator"),
		(permissions.PHOTO_APPROVER, "Photo approver"),
		(permissions.POLL_CREATOR, "Poll creator"),
		(permissions.NEWS_CREATOR, "News creator"),
		(permissions.AWARD_CREATOR, "Award creator") ):
		p = permissions.Permission(id = id, description = description)
		p.save()
	
	groups = getTable(PREFIX+'groups.data')
	
	for groupname, permsList in (
		("moderators", (permissions.USER_MODERATOR, permissions.POST_MODERATOR)),
		("admins", (permissions.SUPERUSER,)),
		("photomanagers", (permissions.PHOTO_APPROVER,)),
		("newsposters", (permissions.NEWS_CREATOR, permissions.POLL_CREATOR)) ):
		found = False
		for line in groups:
		
			if line[0] == groupname:
				for userName in line[2].split(","):
					u = members.get_object(userName__exact=userName.strip())
					perms = [p.id for p in u.get_permission_list()]
					perms += permsList
					u.set_permissions(perms)
					u.save()
				found = True
		if not found:
			raise Exception("Group " + groupname + " not found in groups.data")
	
	
	
###########################################################################################
#		Messages

def migrateMessages():
	for message in messages.get_list():
		message.delete()
		
	for member in members.get_list():
		for boxNumber, boxName in ( (0,'inbox'), (1,'saved') ):
			try:
				data = getTable(PREFIX+"../members/" + member.userName + "." + boxName)
			except IOError:
				data = []
			for line in data:
				message = messages.Message(toMember_id = member.id)
				message.fromMember_id = members.get_object(userName__exact=line[1]).id
				message.time = datetime.fromtimestamp(int(line[3]))
				message.text = line[2]
				message.box = boxNumber
				message.save()

###########################################################################################
#        AWARDS
def migrateAwards():
	for a in awards.get_list():
		a.delete()
	for pa in personalawards.get_list():
		pa.delete()
		
	for line in getTable(PREFIX+"awards.data"):
		awardname = line[2]
		try:
			award = awards.get_object(name__exact=awardname)
		except awards.AwardDoesNotExist:
			award = awards.Award(name = awardname)
			award.image = "award_"+ line[1] + ".gif"
			award.save()
		pa = personalawards.PersonalAward(award_id=award.id)
		pa.reason = line[3]
		pa.member_id = members.get_object(userName__exact=line[0]).id
		pa.save()
	
###########################################################################################
#		POLLS
def migratePolls():
	# first delete all poll options and polls
	for pollOption in polloptions.get_list():
		pollOption.delete()
	
	for poll in polls.get_list():
		poll.delete()
	
	for line in getTable(PREFIX+"../polls/polls.data"):
		try:
			poll = polls.get_object(title__exact = line[1])
		except polls.PollDoesNotExist:
			poll = polls.Poll(title = line[1])
		options = []
		for pollline in line[2].split("[br]"):
			if len(pollline) == 0:
				continue
			if pollline.startswith("[option]"):
				options.append(pollline.replace("[option]", ""))
				# any previous additions to outroText were wrong
				if len(poll.outroText) > 0:
					print "Text '" + poll.outroText + "' in poll " + \
						line[0] + " was discarded"
					poll.outroText = ""
			else:
				if len(options) == 0:
					poll.introText += pollline
				else:
					# assume at end, complain later if we were wrong
					poll.outroText += pollline
		
		poll.open = False
		poll.votingStarts = datetime.fromtimestamp(int(line[6]))
		poll.votingEnds = datetime.fromtimestamp(int(line[7]))
		poll.rules = getInt(line[3])
		poll.ruleParameter = getInt(line[4])
		poll.haveVoteInfo = False
		poll.createdBy_id = members.get_object(userName__exact=line[5]).id
		poll.save()
		
		for i in range(0,len(options)):
			option = polloptions.PollOption(text=options[i])
			option.poll_id = poll.id
			option.total = int(line[9])
			option.listorder = i
			option.save()

############################################################################################
#  Forums

# Forums in different places - Camps, news, website

def getDummyOrRealMember(userName):
	userName = userName.strip()[0:20]
	if len(userName) == 0: userName = "''"
	# specifc hack for bad data:
	if userName == "Jen4Ste":
		userName = "'Jen4Ste'"
	if userName == '"ecky2702':
		userName = "'ecky2702'"
	try:
		u = members.get_object(userName__exact=userName)
		return u
	except members.MemberDoesNotExist:
		if userName.startswith("'"):
			u = members.Member(userName = userName)
			u.realName = ""
			u.email = ""
			u.password = ""
			u.dateJoined = None
			u.lastSeen = None
			u.dummyMember = True
			u.hidden = True
			u.save()
			return u
		return None

	

def migrateForums():
	# delete eveything
	for p in posts.get_list(): p.delete()
	for n in newsitems.get_list(): n.delete()
	for t in topics.get_list(): t.delete()
	for p in photos.get_list(): p.delete()
	for f in forums.get_list(): f.delete()
	for g in gallerys.get_list(): g.delete()

	boardsdir = PREFIX+ "../boards/"
	boards = getTable(boardsdir + "boards.data")
	for line in boards:
		if line[0].startswith('2003'): continue # mistake
		
		if line[0].startswith('photos-'):
			# photo gallery
			location = "camps" + line[0].replace("photos-","/").replace("-", "/") + "/photos/"
			g = gallerys.Gallery(location = location)
			g.save()
			f = None
		else: 
			# message board
			if line[0].startswith("mb-"):
				location = "camps" + line[0].replace("mb-","/").replace("-", "/") + "/forum/"
			else:
				location = line[0] + "/"
			f = forums.Forum(location = location)
			f.open = bool(int(line[1]))
			f.save()
			g = None
		try:
			topiclist = getTable(boardsdir + line[0] + "/topiclist.data")
		except IOError:
			topiclist = []
			
		for topicline in topiclist:
			photo = None
			topic = None
			if f != None:
				topic = topics.Topic(open = bool(int(topicline[7])))
				topic.hidden = getBool(topicline[9])
				topic.createdAt = None
				try:
					timestamp = int(topicline[3])
					if timestamp > 0:
						topic.createdAt = datetime.fromtimestamp(timestamp)
				except:
					pass
				
				
				topic.subject = topicline[1]
				topic.startedBy_id = getDummyOrRealMember(topicline[2]).id
				# Create news item if necessary
				topictype = getInt(topicline[10])
				if topictype == 1 or topictype == 2:
					# news item
					ni = newsitems.NewsItem(summary="")
					ni.createdBy_d = topic.startedBy_id
					ni.createdAt = topic.createdAt
					ni.summary = topicline[11]
					
					if topictype == 2:
						# long news item
						try: 
							ni.fullItem = "".join(file(PREFIX+"../news/" + topicline[12]))
						except IOError:
							print "Migration of news items: '" + topicline[12] + "' data is missing"
							ni.fullItem = "ERROR - '" + topicline[12] + "' data was missing at migration time"
					else:
						ni.fullItem = ""
					
					ni.subject = topic.subject
					ni.save()
					topic.newsItem_id = ni.id
				elif topictype == 3:
					# poll names are unique up to now
					pollname = ""
					for pollline in getTable(PREFIX+"../polls/polls.data"):
						if pollline[0] == topicline[12]:
							pollname = pollline[1]
							break
					topic.poll_id = polls.get_object(title__exact=pollname).id
				topic.forum_id = f.id
				topic.save()
				
			if g != None:
				photo = photos.Photo(open = bool(int(topicline[7])))
				photo.hidden = getBool(topicline[9])
				photo.createdAt = None
				try:
					timestamp = int(topicline[3])
					if timestamp > 0:
						photo.createdAt = datetime.fromtimestamp(timestamp)
				except:
					pass
			
				for photoline in getTable(PREFIX+line[0]+".data"):
					if photoline[0] == topicline[0]:
						photo.filename = photoline[1]
						break
				photo.gallery_id = g.id
				photo.save()
			
			# Now get the posts
			try:
				postdata = getTable(boardsdir + line[0] + "/" + topicline[0] + ".data")
			except IOError:
				postdata = []
			for postline in postdata:
				p = posts.Post(subject="")
				p.postedBy_id = getDummyOrRealMember(postline[1].strip()).id
				p.subject = postline[2]
				
				p.message = fix_bbcode(postline[3])
				try:
					p.postedAt = datetime.fromtimestamp(int(postline[4]))
				except:
					p.postedAt = None
				if topic != None:
					p.topic_id = topic.id
				elif photo != None:
					p.photo_id = photo.id
				p.save()
		# end for topicline in topiclist
	# end for line in board			
	
def migrateMainMenu():
	for m in menulinks.get_list():
		m.delete()
	
	links = (
		('Home','/',0,''),
		('News','/news/',100, ''),
		('Camps {{thisyear}}', '/thisyear/',200, ''),
		('Booking', '/thisyear/booking/', 210, '/thisyear/'),
		('Coming on camp', '/thisyear/coming-on-camp/', 220, '/thisyear/'),
		('All camps', '/camps/',400, ''),
		('Camp sites', '/sites/', 500, ''),
		('Members', '/members/', 500, ''),
		('About CCIW', '/info/', 600, ''),
		('About camp', '/info/about-camp/', 602, '/info/'),
		('Directors', '/info/directors/', 610, '/info/'),
		('Doctrinal basis', '/info/doctrinal-basis/', 620, '/info/'),
		('Legal', '/info/legal/', 630, '/info/'),
		('About website', '/website/', 700, ''),
		('Terms','/website/terms/', 710, '/website/'),
		('Forum','/website/forum/', 720, '/website/'),
		('Help','/website/help/', 730, '/website/'),
		('Contact us','/contact/', 800, '')
	)
	
	for i in range(0, len(links)):
		title, url, order, parentUrl = links[i]
		m = menulinks.MenuLink(title = title, url = url, listorder=order)
		if parentUrl != '':
			m.parentItem_id = menulinks.get_object(url__exact=parentUrl).id
		m.save()
		

def migrateHtml():
	for h in htmlchunks.get_list():
		h.delete()
	for name, url, pageTitle, htmlChunk in html:
		h = htmlchunks.HtmlChunk(name = name)
		h.html = htmlChunk
		h.pageTitle = pageTitle
		if url != "":
			h.menuLink_id = menulinks.get_object(url__exact=url).id
		h.save()
	
##########################################################


migrateLeaders()
migrateSites()
migrateCamps()
migrateMembers()
migratePermissions()
migrateMessages()
migrateAwards()
migratePolls()
migrateForums()
migrateMainMenu()
migrateHtml()

