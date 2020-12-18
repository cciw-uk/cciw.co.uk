Email sending
=============

Email sending has been a severe headache!

Running your own mailserver comes with a lot of problems regarding maintaining
email reputation, to avoid being on a spam list.

We are currently using Amazon SES to send email, to outsource this problem, but
they also end up on blacklists sometimes.

We need to send email for certain purposes:

1. Our booking login process works via a confirmation email.

2. We send confirmation of bookings to people who have booked, and reminders to pay.

3. Our contact form needs to send out messages to a few CCiW staff.

4. We send various emails about references to CCiW staff and other people.
   We also handle bounces to some of these emails by notifying CCiW staff by email.

5. We send out group emails to CCiW officers.

6. We have various other @cciw.co.uk forwarding addresses.

To handle incoming mail, it is collected by AWS SES, and sent to our web app,
from where we send it out again via SMTP if it is a forwarding address or group
address. This means that we can appear to be the source of spam if we receive
and forward spam.

We have the following strategies to cope with spam and avoiding being on black lists.

1. Incoming email should be checked for spam by our provider and stopped at that
   point.

2. Any group lists should have some kind of security on them to stop spammers
   sending to them. For example, officer group lists require sender to be a part
   of the list. Sender fields are spoofable, but less so these days for
   spammers, and would require specific knowledge to get around this.

3. For the remaining cases where we need to send out data that could be from a
   spammer (e.g. contact form)

   * The recipients of these will be limited to a few CCiW staff
   * The email will not be sent. Instead, a link to a CCiW web page will be sent.
   * This page shows the email from the user, and has a ``mailto`` link set
     up that allows the staff to reply in their own email program.
