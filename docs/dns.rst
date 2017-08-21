DNS setup
=========

Email config comes from:
https://app.mailgun.com/app/domains/cciw.co.uk

DNS was set up using 'add domain' to the Digital Ocean droplet. The resulting
records look like:


===== ================================== =================================
Type  Name/col1                          Value/col2
===== ================================== =================================
A     @                                  138.68.175.189
CNAME www.cciw.co.uk                     cciw.co.uk
CNAME email.cciw.co.uk                   mailgun.org.
MX    10                                 mxa.mailgun.org.
MX    10                                 mxb.mailgun.org.
TXT   cciw.co.uk                         v=spf1 include:mailgun.org ~all
TXT   mailo._domainkey.cciw.co.uk        ... (see mailgun)
NS                                       ns1.digitalocean.com.
NS                                       ns2.digitalocean.com.
NS                                       ns3.digitalocean.com.
===== ================================== =================================

Zone file below::

    $ORIGIN cciw.co.uk.
    $TTL 1800
    cciw.co.uk. IN SOA ns1.digitalocean.com. hostmaster.cciw.co.uk. 1503339922 10800 3600 604800 1800
    cciw.co.uk. 1800 IN NS ns1.digitalocean.com.
    cciw.co.uk. 1800 IN NS ns2.digitalocean.com.
    cciw.co.uk. 1800 IN NS ns3.digitalocean.com.
    www.cciw.co.uk. 43200 IN CNAME cciw.co.uk.
    cciw.co.uk. 14400 IN MX 10 mxa.mailgun.org.
    cciw.co.uk. 3600 IN A 138.68.175.189
    email.cciw.co.uk. 43200 IN CNAME mailgun.org.
    cciw.co.uk. 14400 IN MX 10 mxb.mailgun.org.
    cciw.co.uk. 3600 IN TXT v=spf1 include:mailgun.org ~all
    mailo._domainkey.cciw.co.uk. 3600 IN TXT k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDKYgDOFQkWOA7BvKGNyNuFQr0lMxBn12EKZj4uRqXEjiJbw5QI30rxBjNU36a+eKJgDXzV3n673rEW9sTuPb69Ll7MDPV0B/Ene8GhgurReE9WXDiv9SZNtKveWumDDzza564hFviTzfrxa6sLMNaYu5sRCkCPKUaRHU3ImN5k9wIDAQAB
