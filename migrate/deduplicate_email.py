#!/usr/bin/python
import devel
from django.db import connection, transaction
from cciw.cciwmain.models import Member

# Set permissions so that default managers show us everything.
from cciw.middleware import threadlocals
from django.contrib.auth.models import User
threadlocals.set_current_user(User.objects.filter(is_superuser=True)[0])


transaction.enter_transaction_management()
transaction.managed(True)


# fix MrKnowItAll's email address

# first delete various test users
try:
    Member.objects.filter(email__iexact='lukeplant@fastmail.fm').delete()
except Member.DoesNotExist:
    pass

mrknowitall = Member.objects.get(user_name__iexact='MrKnowItAll')
mrknowitall.email = "lukeplant@fastmail.fm"
mrknowitall.save()




cursor = connection.cursor()

sql = """select lower(email), count(user_name) as c from cciwmain_member group by lower(email) having count(user_name) != 1 order by lower(email);"""

cursor.execute(sql)
duplicates = list(cursor.fetchall())

changed = {}
for email, count in duplicates:
    
    if not email:
        continue
    # Heuristics:
    #  - how many posts
    #  - when they last signed in
    #  - when they joined up?
    print "Email: " + email
    members = Member.all_objects.filter(email__iexact=email).order_by('date_joined')
    max_posts = 0
    member_real = None
    earliest_joined = None
    for member in members:
        c = member.posts.all().count()
        print "  Member %s: posts %s; messages: %s" % (member.user_name, c, member.messages_received.count())
        if member_real is None or c > max_posts:
            max_posts = c
            member_real = member
        elif c == max_posts:
            # Choose the one that signed in most recently
            if member.last_seen > member_real.last_seen:
                member_real = member
        if earliest_joined is None or member.date_joined < earliest_joined:
            earliest_joined = member.date_joined

    # Update the date_joined of the member we are choosing.
    print "  Keeping member %s" % member_real.user_name
    member_real.date_joined = earliest_joined
    member_real.save()

    # Re-parent posts, topics,
    changed_list = []
    for member in set(m for m in members if m != member_real):
        changed_list.append(member.user_name)
        print "  Changing member %s" % member.user_name
        for relset, relfield in {'messages_sent': 'from_member',
                                 'messages_received': 'to_member',
                                 'personal_awards': 'member',
                                 'photos_with_last_post': 'last_post_by',
                                 'poll_votes': 'member',
                                 'polls_created': 'created_by',
                                 'posts': 'posted_by',
                                 'topics_started': 'started_by',
                                 'topics_with_last_post': 'last_post_by'
                                 }.items():
            related_objs = getattr(member, relset)
            ct = 0
            for item in related_objs.all():
                # Check for typos
                if not hasattr(item, relfield):
                    raise Exception("%s does not have field %s" % (item, relfied))
                # reparent
                setattr(item, relfield, member_real)
                item.save()
                ct += 1
            if ct > 0:
                print "    Changed: %s instances for %s" % (ct, relset)
        # Don't use Django's delete, as we want to know whether
        # there are still related objects
        cursor = connection.cursor()
        cursor.execute("delete from cciwmain_member where user_name = %s;", [member.user_name])
    changed[member_real.email] = (member_real.user_name, changed_list)

f = open("changed_users.py", "w")
f.write("changed = %r\n" % changed)
f.close()

transaction.commit()
