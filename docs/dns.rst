DNS setup
=========

DNS was set up using 'add domain' to the Digital Ocean droplet. The resulting
records look like:


===== ================================== =================================
Type  Name/col1                          Value/col2
===== ================================== =================================
A     @                                  178.62.115.97
CNAME www.cciw.co.uk                     cciw.co.uk
NS                                       ns1.digitalocean.com.
NS                                       ns2.digitalocean.com.
NS                                       ns3.digitalocean.com.
===== ================================== =================================

Further records added as per instructions for various services in :doc:`services.rst`

Most recent Zone file:

Zone file below::

    $ORIGIN cciw.co.uk.
    $TTL 1800
    cciw.co.uk. IN SOA ns1.digitalocean.com. hostmaster.cciw.co.uk. 1608211709 10800 3600 604800 1800
    cciw.co.uk. 86400 IN NS ns1.digitalocean.com.
    cciw.co.uk. 86400 IN NS ns2.digitalocean.com.
    cciw.co.uk. 86400 IN NS ns3.digitalocean.com.
    www.cciw.co.uk. 86400 IN CNAME cciw.co.uk.
    cciw.co.uk. 86400 IN A 178.62.115.97
    cciw.co.uk. 86400 IN MX 10 inbound-smtp.eu-west-1.amazonaws.com.
    mailtest.cciw.co.uk. 86400 IN MX 10 inbound-smtp.eu-west-1.amazonaws.com.
    cciw.co.uk. 86400 IN TXT v=spf1 include:amazonses.com ~all
    mailo._domainkey.cciw.co.uk. 86400 IN TXT k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDKYgDOFQkWOA7BvKGNyNuFQr0lMxBn12EKZj4uRqXEjiJbw5QI30rxBjNU36a+eKJgDXzV3n673rEW9sTuPb69Ll7MDPV0B/Ene8GhgurReE9WXDiv9SZNtKveWumDDzza564hFviTzfrxa6sLMNaYu5sRCkCPKUaRHU3ImN5k9wIDAQAB
    z3eelawfukebv7mvxtoinsdi22z2ev6u._domainkey.cciw.co.uk. 86400 IN CNAME z3eelawfukebv7mvxtoinsdi22z2ev6u.dkim.amazonses.com.
    bxdnaroig3dplojupqwwq5by3m7otcl2._domainkey.cciw.co.uk. 86400 IN CNAME bxdnaroig3dplojupqwwq5by3m7otcl2.dkim.amazonses.com.
    ikckimwtqraue5g2ugdrqn7svhj3p2uy._domainkey.cciw.co.uk. 86400 IN CNAME ikckimwtqraue5g2ugdrqn7svhj3p2uy.dkim.amazonses.com.
    _amazonses.cciw.co.uk. 86400 IN TXT RSOthFcgHSsLOE0u2IYtAaDXyqCFcwPWQs5y2vnH1mY=
    a4d4zn6yp3mvtmcocwvrd5ouccuhgt56._domainkey.cciw.co.uk. 43200 IN CNAME a4d4zn6yp3mvtmcocwvrd5ouccuhgt56.dkim.amazonses.com.
    o3epkevhrv3wjrx4o37hlpnkcxossc35._domainkey.cciw.co.uk. 43200 IN CNAME o3epkevhrv3wjrx4o37hlpnkcxossc35.dkim.amazonses.com.
    s4tyw7rv2umo6ulqa3n7zo4xb6jr44h3._domainkey.cciw.co.uk. 43200 IN CNAME s4tyw7rv2umo6ulqa3n7zo4xb6jr44h3.dkim.amazonses.com.
    h2jr7xlix2nhpslxgsoj2blhmc5mmniw._domainkey.cciw.co.uk. 43200 IN CNAME h2jr7xlix2nhpslxgsoj2blhmc5mmniw.dkim.amazonses.com.
    ancc6qp74tv2pg4mohwm6bxhvopfie4a._domainkey.cciw.co.uk. 43200 IN CNAME ancc6qp74tv2pg4mohwm6bxhvopfie4a.dkim.amazonses.com.
    opnnhv7waiu4mww5winm2jy3nq4fbntr._domainkey.cciw.co.uk. 43200 IN CNAME opnnhv7waiu4mww5winm2jy3nq4fbntr.dkim.amazonses.com.
