import sys
import os
sys.path = sys.path + ['/home/httpd/www.cciw.co.uk/django/','/home/httpd/www.cciw.co.uk/django_src/']
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings.main'

from django.models.camps import camps, sites, persons

def getTable(filename):
	data = []
	for line in file(filename):
		data.append(line.strip("\r\n").split("\t"))
	return data

PREFIX = '/home/httpd/www.cciw.co.uk/web/data/'

# migrate sites
# manual
try:
	site1 = sites.get_object(short_name__exact="Brynglas Farm")
except sites.SiteDoesNotExist:
	site1 = sites.Site(short_name="Brynglas Farm", long_name="Brynglas Farm, Tywyn")
site1.info = """
<address>Brynglas Farm,<br/>
Bryncug,<br/>
Tywyn, <br/>
Gwynedd, <br/>
LL36 9PY, <br/>
Phone 01654 710544 <br/>
</address>
	 
<p>The Brynglas site is a large field on Brynglas farm, very close to the Tal-y-Llyn railway - in fact you have to cross the railway (twice!) as you come through the farm onto the campsite. The campers and officers are all in tents, with the exception of some of the more pampered leaders and chaplains, and the kitchen and toilets are also under canvas. The ample space means that the camps have a nominal capacity of 75, but more can be accomodated.
photo 1 The camp site provides plenty to do with a large football pitch, volleyball area, small hills to climb, a stream , as well as table tennis and other games in the main marquee. The site, along with the surrounding fields, make it a great place for wide games.
</p>
<p>The site is close to Tywyn (a small town with most amenities including a well served railway station) - It only takes 10 minutes by car from camp to Tywyn. The shops there, particularly the honey ice-cream factory, are popular with campers, and the leisure centre with its swimming pool and showers are increasingly popular as the week progresses (since the campsite does not have showers )! Just past Tywyn is Broadwater, which is a great site for canoing and raft-building. The camp site is also quite close to Cader Idris, which is usually climbed during the course of the week, and also to the picturesque Dolgoch Falls.
</p>"""
site1.save()

try:
	site2 = sites.get_object(short_name__exact="Llys Andreas")
except sites.SiteDoesNotExist:
	site2 = sites.Site(short_name="Llys Andreas", long_name="Llys Andreas, Barmouth")
site2.info = """
<address>Llys Andreas Camp Site,<br/>
Ffordd Tyddyn Felin<br/>
Tal-y-bont<br/>
Barmouth<br/>
LL43 2AU<br/>
Pay phone: 01341 247526<br/>
</address>
<p>This site in Tal-y-bont is a smaller site than Tywyn, but still has plenty of room for the 50 campers it can accomodate. It has a main marquee for services and campsite activities, and a good sized playing space including a volleyball area. There is also a picturesque river just on the edge of the campsite.
There is a multi-purpose building which houses a kitchen and eating/games areas. The site also has a toilet and wash-block, (including showers) for both males and females.
Llys Andreas is very accessible, just two minutes off the main road between Barmouth & Harlech and just 10 mins from Tal-y-bont railway station. Barmouth also has a leisure centre, which has a five-a-side football pitch, as well a beach, a fair and plenty of shops. There is also a very pleasant beach much closer to Llys Andreas, which is a great spot for barbeques, bathing or bivouacking!
</p>
"""
site2.save()

# migrate leaders/chaplains
for pdata in getTable(PREFIX+'leaders.data'):
	name = pdata[0]
	info = pdata[1]
	try:
		p = persons.get_object(name__iexact = name)
	except persons.PersonDoesNotExist:
		p = persons.Person(name = name, info = info)
		p.save()
	
# migrate past camps
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
		
	# ids of sites are the same:
	camp.site_id = sites.get_object(id__exact=int(c[1])).id
	camp.age = c[2]
	
	# TODO - change schema of camps to have start date and 
	# end date and intelligently work out what they should be here
	camp.dates = c[3]
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
	
		
		
	
