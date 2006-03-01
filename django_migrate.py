#!/usr/bin/python
# Migration script from old flatfiles to django
import devel
import os
import shutil
import re
import copy
from datetime import datetime, date

from migrate_html import *
from cciw.apps.cciw.models import *
from cciw.apps.cciw.utils import strip_control_chars

# Config
PREFIX = '/home/httpd/www.cciw.co.uk/web/data/'
ICONDIR = '/home/httpd/www.cciw.co.uk/web/images/members/'
NEW_ICONDIR = '/home/httpd/www.cciw.co.uk/django/media/images/members/'

# Utility functions

# list that generates empty string items if you try to access out of bounds
# (matches our flatfiles and PHP arrays)
class LazyList(list):
    def __getitem__(self, index):
        if index >= len(self):
            return ""
        else:
            return list.__getitem__(self, index)

def get_bool(string_data):
    """Use instead of bool(int()) if empty data is allowed"""
    if len(string_data) == 0:
        return False
    else:
        return bool(int(string_data))

    
def get_int(string_data):
    """Use instead of int() if empty data is allowed"""
    if len(string_data) == 0:
        return 0
    else:
        return int(string_data)

def get_table(filename, fieldSep="\t"):
    rows = []
    for line in file(filename):
        line = line.strip("\r\n")
        if len(line) == 0: continue
        lineData = LazyList(s.decode('windows-1252').encode('UTF-8') for s in line.split(fieldSep))
        rows.append(lineData)
    return rows

def fix_bbcode(message):
    """Fix up some old style bbcode to use new style"""
    replacements = (
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
        ('[:iwin:]', ':stupid:'),
        ('<br>', '[br]'),
        ('&lt;', '<'),
        ('&gt;', '>'),
        ('&quot;', '"'),
        ('&amp;', '&'),
    )
    
    for s in replacements:
        message = message.replace(s[0], s[1])
    
    message = strip_control_chars(message)
    
    return message

def fix_member_links(text):
    return re.sub(r'members.php\?sp=([^\'"]*)',r'/members/\1/', text)
    
def fix_news_items(html):
    html = fix_member_links(html)
    html = html.replace('src="news/', 'src="{{media}}news/').replace("src='news/", "src='{{media}}news/")
    return html
    

# start with some we will struggle to determine programatically
new_urls = {
    'news.php': '/news/',
    'pastcamps.php?sp=2005-all': '/camps/2005/all/forum/',
    'pastcamps.php?sp=2004-all': '/camps/2004/all/forum/',
    'pastcamps.php?sp=2003-all': '/camps/2003/all/forum/',
    'pastcamps.php?sp=2002-all': '/camps/2002/all/forum/',
    'pastcamps.php?sp=2001-all': '/camps/2001/all/forum/',
    'about_website.php?sp=codes': '/website/help/', # TODO ?
    'http://www.cciw.co.uk/': 'http://cciw.co.uk/',
} # these are added to by various functions as we go through




###########################################################################################
#                   SITES
# mainly manual
def migrate_sites():
    
    try:
        site1 = Site.objects.get(short_name="Brynglas Farm")
    except Site.DoesNotExist:
        site1 = Site(short_name="Brynglas Farm", long_name="Brynglas Farm, Tywyn")
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
        site2 = Site.objects.get(short_name="Llys Andreas")
    except Site.DoesNotExist:
        site2 = Site(short_name="Llys Andreas", long_name="Llys Andreas, Barmouth")
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
def migrate_leaders():
    Person.objects.all().delete()
    for pdata in get_table(PREFIX + 'leaders.data'):
        p = Person(name = pdata[0], info = pdata[1])
        p.save()

###########################################################################################
#                PAST CAMPS

def migrate_camps():
    Camp.objects.all().delete()
    for c in reversed(get_table(PREFIX+'pastcamps.data')):
        try: year = int(c[0].split("-")[0])
        except: continue
        if year < 2000: continue # don't store
        
        try:
            number = int(c[0].split("-")[1])
        except:
            continue
        try:
            camp = Camp.objects.get(year=year, number=number)
        except Camp.DoesNotExist:
            camp = Camp(year=year, number=number)
            
        # ids of sites are the same as before:
        camp.site_id = Site.objects.get(id=int(c[1])).id
        camp.age = c[2]
        
        # Create proper dates from nearly free form dates we had before
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
        
        camp.start_date = date(year, startmonth, startday)
        camp.end_date = date(year, endmonth, endday)
        
        camp.chaplain_id = Person.objects.get(name__iexact=c[5]).id
        if len(c[6]) > 0:
            pcampyear, pcampnumber = map(int, c[6].split("-"))
            try:
                camp.previous_camp_id = Camp.objects.get(year=pcampyear, number=pcampnumber).id
            except:
                pass
            
        camp.save()
        
        leaders = c[4]
        if leaders.startswith('"'):
            leaders = [leader.strip() for leader in leaders.strip('"').split(",")]
        else:
            leaders = [leaders]
        for name in leaders:
            camp.leaders.add(Person.objects.get(name__iexact=name))
    
###########################################################################################
#             USERS
def migrate_members():
    Member.objects.all().delete()
    def create_member(data, passwords_dict, last_seen_data):
        member = Member(user_name=data[0])
        member.real_name = data[1]
        member.email = data[3]
        member.password = passwords_dict.get(member.user_name, Member.encrypt_password('password1'))
        member.date_joined = datetime.fromtimestamp(int(data[6]))
        member.last_seen = last_seen_data.get(member.user_name, member.date_joined)
        member.show_email = get_bool(data[4])
        member.message_option = get_int(data[5])
        member.comments = fix_bbcode(data[9])
        member.confirm_secret = data[13]
        member.moderated = get_int(data[15])
        member.hidden = get_bool(data[17])
        member.banned = get_bool(data[16])
        member.new_email = data[22]
        member.bookmarks_notify = not get_bool(data[18])
        for suffix in ('jpeg', 'png', 'gif'):
            imagefile = member.user_name + '.' + suffix
            if os.path.isfile(ICONDIR + imagefile):
                shutil.copyfile(ICONDIR + imagefile, NEW_ICONDIR + imagefile)
                member.icon = imagefile
                
        return member
    
    # first get passwords from separate table
    passwords = {}
    for line in get_table(PREFIX+".htpasswd.online.2005-08-26",":"):
        passwords[line[0]] = line[1]
    
    last_seen_data = {}
    for line in get_table(PREFIX+"lastseen.data"):
        last_seen_data[line[0]] = datetime.fromtimestamp(int(line[1]))
        
    # Now parse members.data and pending_members.data
    for line in get_table(PREFIX+"members.data"):
        try:
            u = create_member(line, passwords, last_seen_data)
        except:
            print "Invalid data:"
            print line
            continue
        u.confirmed = True
        u.save()
    
    for line in get_table(PREFIX+"pending_members.data"):
        try:
            u = create_member(line,passwords, last_seen_data)
        except:
            print "Invalid data:"
            print line
            continue
        u.confirmed = False
        u.save()

###########################################################################################
# Permissions (from old 'groups')
def migrate_permissions():
    for m in Member.objects.all():
        m.permissions.clear()
    Permission.objects.all().delete()
    
    for id, description in ( 
        (Permission.SUPERUSER, "Administrator"),
        (Permission.USER_MODERATOR, "Member moderator"),
        (Permission.POST_MODERATOR, "Post moderator"),
        (Permission.PHOTO_APPROVER, "Photo approver"),
        (Permission.POLL_CREATOR, "Poll creator"),
        (Permission.NEWS_CREATOR, "News creator"),
        (Permission.AWARD_CREATOR, "Award creator") 
        ):
        p = Permission(id=id, description=description)
        p.save()
    
    groups = get_table(PREFIX+'groups.data')
    
    # create permissions based on old 'groups' data for certain group names
    oldgroups = {
        "moderators": (Permission.USER_MODERATOR, Permission.POST_MODERATOR),
        "admins": (Permission.SUPERUSER,),
        "photomanagers": (Permission.PHOTO_APPROVER,),
        "newsposters": (Permission.NEWS_CREATOR, Permission.POLL_CREATOR),
    }

    for groupname, permsList in oldgroups.items():
        found = False
        for line in groups:
            if line[0] == groupname:
                for user_name in line[2].split(","):
                    u = Member.objects.get(user_name=user_name.strip())
                    u.permissions.add(*tuple(Permission(id=p) for p in permsList))
                    u.save()
                found = True
        if not found:
            raise Exception("Group " + groupname + " not found in groups.data")
    
###########################################################################################
#        Messages

def migrate_messages():
    Message.objects.all().delete()
        
    for member in Member.objects.all():
        for boxNumber, boxName in ( (0,'inbox'), (1,'saved') ):
            try:
                data = get_table(PREFIX+"../members/" + member.user_name + "." + boxName)
            except IOError:
                data = []
            for line in data:
                message = Message(text=fix_bbcode(line[2]))
                message.to_member_id = member.user_name
                message.from_member_id = Member.objects.get(user_name=line[1]).user_name
                message.time = datetime.fromtimestamp(int(line[3]))
                message.box = boxNumber
                message.save()

###########################################################################################
#        AWARDS
def migrate_awards():
    Award.objects.all().delete()
    PersonalAward.objects.all().delete()
        
    for line in get_table(PREFIX+"awards.data"):
        awardname,year = line[2].split(" ")
        try:
            award = Award.objects.get(name=awardname, year=year)
        except Award.DoesNotExist:
            award = Award(name = awardname)
            award.year = year
            descriptions = {
                "Hero": (1, "'Bronze' award - sterling effort and achievement"),
                "Addict": (2, "'Silver' award - slightly worrying levels of website activity going on here."), 
                "Ubergeek": (3, "'Gold' award - definitely time to take a break from the computer."),
                "Numpton": (-2, "'Black' - we noticed you, at least you have that.")
            }
            award.value, award.description = descriptions[awardname]
            award.image = "award_"+ line[1] + ".gif"
            award.save()
        pa = PersonalAward(award_id=award.id)
        pa.reason = line[3]
        pa.member_id = Member.objects.get(user_name=line[0]).user_name
        pa.save()
    
###########################################################################################
#        POLLS
def migrate_polls():
    # first delete all poll options and polls
    PollOption.objects.all().delete()
    Poll.objects.all().delete()
    
    for line in get_table(PREFIX+"../polls/polls.data"):
        try:
            poll = Poll.objects.get(title=line[1])
        except Poll.DoesNotExist:
            poll = Poll(title=line[1])
        options = []
        for pollline in line[2].split("[br]"):
            if len(pollline) == 0:
                continue
            if pollline.startswith("[option]"):
                options.append(fix_bbcode(pollline.replace("[option]", "")))
                # any previous additions to outro_text were wrong
                if len(poll.outro_text) > 0:
                    print "Text '" + poll.outro_text + "' in poll " + \
                        line[0] + " was discarded"
                    poll.outro_text = ""
            else:
                if len(options) == 0:
                    poll.intro_text += pollline
                else:
                    # assume at end, complain later if we were wrong
                    poll.outro_text += pollline
        
        poll.open = False
        poll.voting_starts = datetime.fromtimestamp(int(line[6]))
        poll.voting_ends = datetime.fromtimestamp(int(line[7]))
        poll.rules = get_int(line[3])
        poll.rule_parameter = get_int(line[4])
        poll.have_vote_info = False
        poll.created_by_id = Member.objects.get(user_name=line[5]).user_name
        poll.save()
        
        # Get votes
        pollinfo = get_table(PREFIX + "../polls/" + str(line[0]) + ".data")
        # votes are on second row, second col
        votes = pollinfo[1][1].split(',')
        
        for i in range(0,len(options)):
            option = PollOption(text=options[i])
            option.poll_id = poll.id
            option.total = int(votes[i])
            option.listorder = i
            option.save()

############################################################################################
#  Forums

# Forums in different places - Camps, news, website

def get_dummy_or_real_member(user_name):
    user_name = user_name.strip()[0:20]
    if len(user_name) == 0: user_name = "''"
    # specifc hack for bad data:
    if user_name == "Jen4Ste":
        user_name = "'Jen4Ste'"
    if user_name == '"ecky2702':
        user_name = "'ecky2702'"
    try:
        u = Member.objects.get(user_name=user_name)
        return u
    except Member.DoesNotExist:
        if user_name.startswith("'"):
            u = Member(user_name = user_name)
            u.real_name = ""
            u.email = ""
            u.password = ""
            u.date_joined = None
            u.last_seen = None
            u.dummy_member = True
            u.hidden = True
            u.save()
            return u
        return None

def migrate_forums():
    # delete eveything
    Post.objects.all().delete()
    NewsItem.objects.all().delete()
    Topic.objects.all().delete()
    Photo.objects.all().delete()
    Forum.objects.all().delete()
    Gallery.objects.all().delete()

    boardsdir = PREFIX+ "../boards/"
    boards = get_table(boardsdir + "boards.data")
    for line in boards:
        if line[0].startswith('2003'): continue # this was a random mistake
        
        if line[0].startswith('photos-'):
            # photo gallery
            location = ("camps" + line[0].replace("photos-","/").replace("-", "/") + "/photos/").lower()
            # Old URL:
            old_location = 'pastcamps.php?sp=' + line[0].replace("photos-","")
            if line[0].startswith('photos-20') or line[0].startswith('photos-19'):
                old_location = old_location + '&ssp=photos'
            
            g = Gallery(location = location)
            g.save()
            new_urls[old_location] = g.get_absolute_url()
            f = None
        else: 
            # message board
            if line[0].startswith("mb-"):
                old_location = 'pastcamps.php?sp=' + line[0].replace("mb-","") + '&ssp=mb'
                location = "camps" + line[0].replace("mb-","/").replace("-", "/") + "/forum/"
            else:
                location = line[0] + "/"
            if location == "website/":
                old_location = 'about_website.php?sp=mb'
                location = "website/forum/"
            if location == 'news/':
                old_location = 'news.php?sp=mb'
            
            f = Forum(location = location)
            f.open = bool(int(line[1]))
            f.save()
            
            new_urls[old_location] = f.get_absolute_url()
            g = None
        try:
            topiclist = get_table(boardsdir + line[0] + "/topiclist.data")
        except IOError:
            topiclist = []
        
        # old_location is used below
        for topicline in topiclist:
            photo = None
            topic = None
            if f != None:
                topic = Topic(open = bool(int(topicline[7])))
                topic.hidden = get_bool(topicline[9])
                topic.created_at = None
                try:
                    timestamp = int(topicline[3])
                    if timestamp > 0:
                        topic.created_at = datetime.fromtimestamp(timestamp)
                except:
                    pass

                topic.subject = topicline[1]
                topic.started_by_id = get_dummy_or_real_member(topicline[2]).user_name
                # Create news item if necessary
                topictype = get_int(topicline[10])
                if topictype == 1 or topictype == 2:
                    # news item
                    ni = NewsItem(summary="")
                    ni.created_by_id = topic.started_by_id
                    ni.created_at = topic.created_at
                    ni.summary = topicline[11]
                    
                    if topictype == 2:
                        # long news item
                        try: 
                            ni.full_item = fix_news_items("".join(file(PREFIX+"../news/" + topicline[12])))
                        except IOError:
                            print "Migration of news items: '" + topicline[12] + "' data is missing"
                            ni.full_item = "ERROR - '" + topicline[12] + "' data was missing at migration time"
                    else:
                        ni.full_item = ""
                    
                    ni.subject = topic.subject
                    ni.save()
                    topic.news_item_id = ni.id
                elif topictype == 3:
                    # poll names are unique up to now, so this will work
                    pollname = ""
                    for pollline in get_table(PREFIX+"../polls/polls.data"):
                        if pollline[0] == topicline[12]:
                            pollname = pollline[1]
                            break
                    topic.poll_id = Poll.objects.get(title=pollname).id
                topic.forum_id = f.id
                topic.save()
                
                old_topic_location = old_location + '&n=' + topicline[0]
                new_urls[old_topic_location] = topic.get_absolute_url()
                
            if g != None:
                photo = Photo(open = bool(int(topicline[7])))
                photo.hidden = get_bool(topicline[9])
                photo.created_at = None
                try:
                    timestamp = int(topicline[3])
                    if timestamp > 0:
                        photo.created_at = datetime.fromtimestamp(timestamp)
                except:
                    pass
            
                for photoline in get_table(PREFIX+line[0]+".data"):
                    if photoline[0] == topicline[0]:
                        photo.filename = photoline[1]
                        photo.description = photoline[2]
                        break
                photo.gallery_id = g.id
                photo.save()
                
                old_photo_location = old_location + '&n=' + topicline[0]
                new_urls[old_photo_location] = photo.get_absolute_url()

                
            # Now get the posts
            try:
                postdata = get_table(boardsdir + line[0] + "/" + topicline[0] + ".data")
            except IOError:
                postdata = []
            for postline in postdata:
                p = Post(subject="")
                p.posted_by_id = get_dummy_or_real_member(postline[1].strip()).user_name
                p.subject = postline[2]
                
                if p.subject.strip() == '&nbsp;' or p.subject.strip() == '':
                    p.subject = ''
                p.message = fix_bbcode(postline[3])
                try:
                    p.posted_at = datetime.fromtimestamp(int(postline[4]))
                except:
                    p.posted_at = None
                if topic != None:
                    p.topic_id = topic.id
                if photo != None:
                    p.photo_id = photo.id
                p.save()
        # end for topicline in topiclist
    # end for line in boards
    
def migrate_main_menu():
    MenuLink.objects.all().delete()
    
    links = (
        ('Home','/',0,''),
        ('News','/news/',100, ''),
        ('Camps {{thisyear}}', '/thisyear/',200, ''),
        ('Booking', '/thisyear/booking/', 210, '/thisyear/'),
        ('Coming on camp', '/thisyear/coming-on-camp/', 220, '/thisyear/'),
        ('Camp sites', '/sites/', 300, ''),
        ('Forums and photos', '/camps/',400, ''),
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
        m = MenuLink(title = title, url = url, listorder=order)
        if parentUrl != '':
            m.parent_item_id = MenuLink.objects.get(url=parentUrl).id
        m.save()
        

def migrate_html():
    HtmlChunk.objects.all().delete()
    for name, url, page_title, htmlChunk in html:
        h = HtmlChunk(name=name, html=htmlChunk, 
                                 page_title=page_title)
        if url != "":
            h.menu_link_id = MenuLink.objects.get(url=url).id
        h.save()
    
##########################################################


def fixup_urls():
    # first sort new_urls by the length of the key
    # descending, to ensure that longer more specific urls get
    # replaced first    
    urlpairs = copy.copy(new_urls.items())
    urlpairs.sort(lambda x, y: len(y[0]) - len(x[0]))
    
    # debug
    out = open("/home/luke/cciw_url_pairs.txt", "w")
    for k, v in urlpairs:
        out.write(k + ' ' + v + "\n")
    out.close()

    # Remap all references to old URLs
    for objectlist, attrlist in (
            (Post.objects.all(), ['message']),
            (NewsItem.objects.all(), ['full_item', 'summary']),
            (Member.objects.all(), ['comments']),
            (Message.objects.all(), ['text']),
            (PollOption.objects.all(), ['text']),
        ):
        for obj in objectlist:
            for attrname in attrlist:
                sorig = getattr(obj, attrname)
                snew = sorig
                for old, new in urlpairs:
                    snew = snew.replace(old, new)
                    snew = snew.replace(old.replace('&', '&amp;'), new.replace('&', '&amp;'))
                snew = fix_member_links(snew)
                snew = snew.replace("http://cciw.co.uk//", "http://cciw.co.uk/")
                if snew != sorig:
                    setattr(obj, attrname, snew)
                    obj.save()


##########################################################

# Order matters!
migrate_leaders()
migrate_sites()
migrate_camps()
migrate_members()
migrate_permissions()
migrate_messages()
migrate_awards()
migrate_polls()
migrate_forums()

migrate_main_menu()
migrate_html()

fixup_urls() # must come after everything else, and needs (at least) migrate_forums to work

