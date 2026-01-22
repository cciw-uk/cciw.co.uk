AWS_MESSAGE_ID = b"2c9c57fhmj03rtht1mcq6gvpg9hijo77ju218ag1"
# Data from a notification from a real email to webmaster@mailtest.cciw.co.uk, modified slightly
AWS_SNS_NOTIFICATION = {
    "headers": {
        "Content-Type": "text/plain; charset=UTF-8",
        "X-Amz-Sns-Message-Type": "Notification",
        "X-Amz-Sns-Message-Id": "5f6d663c-0841-5e96-876a-3e7690a32e53",
        "X-Amz-Sns-Topic-Arn": "arn:aws:sns:eu-west-1:319777369186:ses-incoming-notification",
        "X-Amz-Sns-Subscription-Arn": "arn:aws:sns:eu-west-1:319777369186:ses-incoming-notification:3fa386c5-0a86-42f4-8d2f-25efbf305c97",
        "Host": "5ddb11646c2b.ngrok.io",
        "User-Agent": "Amazon Simple Notification Service Agent",
        "Accept-Encoding": "gzip,deflate",
        "X-Forwarded-Proto": "https",
        "X-Forwarded-For": "54.240.197.56",
    },
    "body": b'{"Type": "Notification", "MessageId": "5f6d663c-0841-5e96-876a-3e7690a32e53", "TopicArn": "arn:aws:sns:eu-west-1:319777369186:ses-incoming-notification", "Subject": "Amazon SES Email Receipt Notification", "Message": "{\\"notificationType\\":\\"Received\\",\\"mail\\":{\\"timestamp\\":\\"2020-12-09T09:19:29.886Z\\",\\"source\\":\\"joe.bloggs@example.com\\",\\"messageId\\":\\"'
    + AWS_MESSAGE_ID
    + b'\\",\\"destination\\":[\\"webmaster@mailtest.cciw.co.uk\\"],\\"headersTruncated\\":false,\\"headers\\":[{\\"name\\":\\"Return-Path\\",\\"value\\":\\"<joe.bloggs@example.com>\\"},{\\"name\\":\\"Received\\",\\"value\\":\\"from forward2-smtp.messagingengine.com (forward2-smtp.messagingengine.com [66.111.4.226]) by inbound-smtp.eu-west-1.amazonaws.com with SMTP id '
    + AWS_MESSAGE_ID
    + b' for webmaster@mailtest.cciw.co.uk; Wed, 09 Dec 2020 09:19:29 +0000 (UTC)\\"},{\\"name\\":\\"X-SES-Spam-Verdict\\",\\"value\\":\\"PASS\\"},{\\"name\\":\\"X-SES-Virus-Verdict\\",\\"value\\":\\"PASS\\"},{\\"name\\":\\"Received-SPF\\",\\"value\\":\\"neutral (spfCheck: 66.111.4.226 is neither permitted nor denied by domain of cantab.net) client-ip=66.111.4.226; envelope-from=joe.bloggs@example.com; helo=forward2-smtp.messagingengine.com;\\"},{\\"name\\":\\"Authentication-Results\\",\\"value\\":\\"amazonses.com; spf=neutral (spfCheck: 66.111.4.226 is neither permitted nor denied by domain of cantab.net) client-ip=66.111.4.226; envelope-from=joe.bloggs@example.com; helo=forward2-smtp.messagingengine.com; dkim=pass header.i=@messagingengine.com; dmarc=fail header.from=cantab.net;\\"},{\\"name\\":\\"X-SES-RECEIPT\\",\\"value\\":\\"AEFBQUFBQUFBQUFGV2dpZFJudnNEU2FpdmY0Q3VRVUkyRWo0a1c4aFR0WlNxY0N6ZEhubFM5TXBiVW9uVHRjV2VLNXZMZ2xCWThFZzV6a3F4K1d4TzBwNjVJbWVMVFVKM1p3WlVCbGJMT3RSNDBkZ0lybkF4bVVOTndwNXBRZ21mYlNjaGZTdnpJWnhESTZwZG9aR0JqT0NzY21VNnlwUFp6WTU3ZDVJekYxQWVGVFFjMHkwaXNmRlE1b04rK290SEl6ejdKdlViaFdrMnBPRFl4VlpDSllwUmdPL3pCUDFIVUppUyttOVpZb3RHQTNMQU9ZYXV1UVQ5bzB2T1BVV2U5b1ZlUG91QjBKVzBmYUVPYWxaNzFnS0Y5MzZoZkdCdzFxc1JrUkVkb1ErdWpWd3U2Yld5VlE9PQ==\\"},{\\"name\\":\\"X-SES-DKIM-SIGNATURE\\",\\"value\\":\\"a=rsa-sha256; q=dns/txt; b=J9lTwMWZVMHQCbVtri6O084C8xlCQwp4dhCSOkViOSLHR9v1Ky2SZ5Wh0wzGeTpUQkg7JFjiZJ8iKJaPUjBSn5xfNZN70R5EvKzimOygegvQZRLNr4OL3BDPEpC+1oxGu6mbTvqaIPXi8OV6vbNSixkGsR1+o5UPSWJeMpx7mWI=; c=relaxed/simple; s=shh3fegwg5fppqsuzphvschd53n6ihuv; d=amazonses.com; t=1607505570; v=1; bh=9Q/dTI6SSbAIdswuE5JJeFrqik0lbDe3vdHuV1lNQmc=; h=From:To:Cc:Bcc:Subject:Date:Message-ID:MIME-Version:Content-Type:X-SES-RECEIPT;\\"},{\\"name\\":\\"Received\\",\\"value\\":\\"from compute1.internal (compute1.nyi.internal [10.202.2.41]) by mailforward.nyi.internal (Postfix) with ESMTP id 524511943AE5 for <webmaster@mailtest.cciw.co.uk>; Wed,  9 Dec 2020 04:19:28 -0500 (EST)\\"},{\\"name\\":\\"Received\\",\\"value\\":\\"from mailfrontend1 ([10.202.2.162]) by compute1.internal (MEProxy); Wed, 09 Dec 2020 04:19:28 -0500\\"},{\\"name\\":\\"DKIM-Signature\\",\\"value\\":\\"v=1; a=rsa-sha256; c=relaxed/relaxed; d=messagingengine.com; h=content-type:date:from:message-id:mime-version:subject:to:x-me-proxy:x-me-proxy:x-me-sender:x-me-sender:x-sasl-enc; s=fm1; bh=51FlYbVgTyEd4aR9onJCyk6+svuysaMIsqvUzIeDGKo=; b=IzEi0p5HRpLjKrfBDd8nxWYOw1lOZCG7FVZgyHVM6K+6tK7+QxpUFlx1XsyS9sQMPc+PCOftV/RpF57g4sxwbMWCrio/rIuM/H1zk3BR20uifLysjRz21tx+1rVWuOwRuDX3IoO1k5tJExXMfNlyYG7SQq1GnKCWge6nG6vNh9kt/Ijftrpd/ULPR4yHStZhdopYcxGD/anjQdrLhGdAXkqBiHLB/kVQP7X1TtRHeDrANmgtlV9a9k0UwcHdvXyvhnXJB78Q2bdbaljdlyrl/s2vWbJxuZw07C2B2VqwI0njOynxluVr1r1EQMG/gtpJN/vJH3N8tDf30QRvOei6SQ==\\"},{\\"name\\":\\"X-ME-Sender\\",\\"value\\":\\"<xms:n5bQX45k7WpvFMoDIyHq394WL7tFuq2GBUgegSbNC7dmqG26JZWcXw> <xme:n5bQX56ASe6eNiDeckrAySyVogKL5edxwHk5hP4eSL7A2VrnuSW8vjxNlTX4DgEtu Aq-zSOGE2_3Wg>\\"},{\\"name\\":\\"X-ME-Proxy-Cause\\",\\"value\\":\\"gggruggvucftvghtrhhoucdtuddrgedujedrudejkedgtdegucetufdoteggodetrfdotf fvucfrrhhofhhilhgvmecuhfgrshhtofgrihhlpdfqfgfvpdfurfetoffkrfgpnffqhgen uceurghilhhouhhtmecufedttdenucenucfjughrpefhuffvkffffgggtgesrgdtreertd efjeenucfhrhhomhepnfhukhgvucfrlhgrnhhtuceonfdrrfhlrghnthdrleeksegtrghn thgrsgdrnhgvtheqnecuggftrfgrthhtvghrnhepudfgleelvdfgtdffudfhteeuvdejte dtueeukeevieegveduvdeiveelfeeutddunecukfhppeekhedrudehfedrvdefiedrvddv keenucevlhhushhtvghrufhiiigvpedtnecurfgrrhgrmhepmhgrihhlfhhrohhmpefnrd frlhgrnhhtrdelkeestggrnhhtrggsrdhnvght\\"},{\\"name\\":\\"X-ME-Proxy\\",\\"value\\":\\"<xmx:n5bQX3cP4gs7wvIlWAEToMtSq4tCzZ4uLzAFso0KZASQrM-8FFXfHg> <xmx:n5bQX9LrvOEPnMbskBK0zNZdkeFMFM5vN8Buz8KDdWC6Cqd3_GnT-A> <xmx:n5bQX8LYKpdrOWNLqsWE0NDlZjZaEnmCmlQJZ4pPdOgWoCNKHgTplw> <xmx:oJbQX7ZBU0ojVRXWefU5RqD4Z-tJfILxvvcOaPQgoSZfUd4jErSmeA>\\"},{\\"name\\":\\"Received\\",\\"value\\":\\"from [192.168.1.25] (unknown [85.153.236.228]) by mail.messagingengine.com (Postfix) with ESMTPA id 91805240062 for <webmaster@mailtest.cciw.co.uk>; Wed,  9 Dec 2020 04:19:27 -0500 (EST)\\"},{\\"name\\":\\"From\\",\\"value\\":\\"Joe Bloggs <joe.bloggs@example.com>\\"},{\\"name\\":\\"Subject\\",\\"value\\":\\"SNS test 1\\"},{\\"name\\":\\"To\\",\\"value\\":\\"webmaster@mailtest.cciw.co.uk\\"},{\\"name\\":\\"Message-ID\\",\\"value\\":\\"<01898236-7e5f-5d03-2e75-644ef41a27b2@cantab.net>\\"},{\\"name\\":\\"Date\\",\\"value\\":\\"Wed, 9 Dec 2020 12:19:26 +0300\\"},{\\"name\\":\\"User-Agent\\",\\"value\\":\\"Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Thunderbird/68.10.0\\"},{\\"name\\":\\"MIME-Version\\",\\"value\\":\\"1.0\\"},{\\"name\\":\\"Content-Type\\",\\"value\\":\\"multipart/alternative; boundary=\\\\\\"------------8C23122ED39EFD655BC8D501\\\\\\"\\"},{\\"name\\":\\"Content-Language\\",\\"value\\":\\"en-GB\\"}],\\"commonHeaders\\":{\\"returnPath\\":\\"joe.bloggs@example.com\\",\\"from\\":[\\"Joe Bloggs <joe.bloggs@example.com>\\"],\\"date\\":\\"Wed, 9 Dec 2020 12:19:26 +0300\\",\\"to\\":[\\"webmaster@mailtest.cciw.co.uk\\"],\\"messageId\\":\\"<01898236-7e5f-5d03-2e75-644ef41a27b2@cantab.net>\\",\\"subject\\":\\"SNS test 1\\"}},\\"receipt\\":{\\"timestamp\\":\\"2020-12-09T09:19:29.886Z\\",\\"processingTimeMillis\\":970,\\"recipients\\":[\\"webmaster@mailtest.cciw.co.uk\\"],\\"spamVerdict\\":{\\"status\\":\\"PASS\\"},\\"virusVerdict\\":{\\"status\\":\\"PASS\\"},\\"spfVerdict\\":{\\"status\\":\\"GRAY\\"},\\"dkimVerdict\\":{\\"status\\":\\"GRAY\\"},\\"dmarcVerdict\\":{\\"status\\":\\"FAIL\\"},\\"action\\":{\\"type\\":\\"S3\\",\\"topicArn\\":\\"arn:aws:sns:eu-west-1:319777369186:ses-incoming-notification\\",\\"bucketName\\":\\"cciw-incoming-mail\\",\\"objectKeyPrefix\\":\\"\\",\\"objectKey\\":\\"'
    + AWS_MESSAGE_ID
    + b'\\"},\\"dmarcPolicy\\":\\"none\\"}}", "Timestamp": "2020-12-09T09:19:30.864Z", "SignatureVersion": "1", "Signature": "hVx4gcXzQRTBlo6ZPKQEEDwh3JdeA9UQihB3lFbUYy/kcs5ulaVVp1Zq20jHqKRWvqvmFsae/NrcYqLkSYoTchL76kPySibOzuYU/uhEsZVOh1xKU7DhKCYdYsxnwduoF80bmVp/ISNDLfU0nP/cGqDp27ZSu9wTvHD8INgqNiszsTz2YFEVbT2fUfqSOqUoNTEm286jV27C2HbLd2J+ddpgHeFtC1zXIbPxxnAnlBhw09ch2KIg2Nv4qtb1glK4Cm6G1bAEQOLyQwcjDREADB5AEcW/RsCmzzRiRA0ip/4GIffSzz10nVb7Qcf2qIpK59wX79Zh31CtwJ2qCTwZ0Q==", "SigningCertURL": "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-010a507c1833636cd94bdb98bd93083a.pem", "UnsubscribeURL": "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:319777369186:ses-incoming-notification:3fa386c5-0a86-42f4-8d2f-25efbf305c97"}',
}

AWS_BOUNCE_NOTIFICATION = {
    "headers": {
        "Content-Length": "3052",
        "Content-Type": "text/plain; charset=UTF-8",
        "X-Amz-Sns-Message-Type": "Notification",
        "X-Amz-Sns-Message-Id": "bf5991d9-9f94-5bbf-af30-c99758486554",
        "X-Amz-Sns-Topic-Arn": "arn:aws:sns:eu-west-1:319777369186:ses-bounces",
        "X-Amz-Sns-Subscription-Arn": "arn:aws:sns:eu-west-1:319777369186:ses-bounces:a4995c81-f8b5-4879-8747-3897967e333e",
        "Host": "5ddb11646c2b.ngrok.io",
        "User-Agent": "Amazon Simple Notification Service Agent",
        "Accept-Encoding": "gzip,deflate",
        "X-Forwarded-Proto": "https",
        "X-Forwarded-For": "54.240.197.106",
    },
    "body": b'{\n  "Type" : "Notification",\n  "MessageId" : "bf5991d9-9f94-5bbf-af30-c99758486554",\n  "TopicArn" : "arn:aws:sns:eu-west-1:319777369186:ses-bounces",\n  "Message" : "{\\"notificationType\\":\\"Bounce\\",\\"bounce\\":{\\"feedbackId\\":\\"010201765723ea4a-97e6a38a-da36-47c9-b447-bc76b838c0c2-000000\\",\\"bounceType\\":\\"Permanent\\",\\"bounceSubType\\":\\"General\\",\\"bouncedRecipients\\":[{\\"emailAddress\\":\\"a.referrer@example.com\\",\\"action\\":\\"failed\\",\\"status\\":\\"5.1.1\\",\\"diagnosticCode\\":\\"smtp; 550 5.1.1 user unknown\\"}],\\"timestamp\\":\\"2020-12-12T13:29:00.000Z\\",\\"remoteMtaIp\\":\\"3.218.174.122\\",\\"reportingMTA\\":\\"dsn; a7-17.smtp-out.eu-west-1.amazonses.com\\"},\\"mail\\":{\\"timestamp\\":\\"2020-12-12T13:28:58.951Z\\",\\"source\\":\\"webmaster@cciw.co.uk\\",\\"sourceArn\\":\\"arn:aws:ses:eu-west-1:319777369186:identity/cciw.co.uk\\",\\"sourceIp\\":\\"85.153.236.111\\",\\"sendingAccountId\\":\\"319777369186\\",\\"messageId\\":\\"010201765723e547-6322af43-456a-45cb-aa18-05ab53ff52ee-000000\\",\\"destination\\":[\\"a.referrer@example.com\\"],\\"headersTruncated\\":false,\\"headers\\":[{\\"name\\":\\"Received\\",\\"value\\":\\"from bunyan ([85.153.236.111]) by email-smtp.amazonaws.com with SMTP (SimpleEmailService-d-TK1K3UJR7) id eA7YseB1P5MKA1YsAa16 for a.referrer@example.com; Sat, 12 Dec 2020 13:28:58 +0000 (UTC)\\"},{\\"name\\":\\"Content-Type\\",\\"value\\":\\"text/plain; charset=\\\\\\"utf-8\\\\\\"\\"},{\\"name\\":\\"MIME-Version\\",\\"value\\":\\"1.0\\"},{\\"name\\":\\"Content-Transfer-Encoding\\",\\"value\\":\\"7bit\\"},{\\"name\\":\\"Subject\\",\\"value\\":\\"[CCIW] Reference for Roy Armstrong\\"},{\\"name\\":\\"From\\",\\"value\\":\\"webmaster@cciw.co.uk\\"},{\\"name\\":\\"To\\",\\"value\\":\\"a.referrer@example.com\\"},{\\"name\\":\\"Date\\",\\"value\\":\\"Sat, 12 Dec 2020 13:28:58 -0000\\"},{\\"name\\":\\"Message-ID\\",\\"value\\":\\"<160777973839.803843.6703080364289671170@bunyan>\\"},{\\"name\\":\\"Reply-To\\",\\"value\\":\\"a.camp.leader@example.com\\"},{\\"name\\":\\"X-CCIW-Camp\\",\\"value\\":\\"2000-blue\\"},{\\"name\\":\\"X-CCIW-Action\\",\\"value\\":\\"ReferenceRequest\\"},{\\"name\\":\\"X-CCIW-Referee\\",\\"value\\":\\"1234\\"}],\\"commonHeaders\\":{\\"from\\":[\\"webmaster@cciw.co.uk\\"],\\"replyTo\\":[\\"a.camp.leader@example.com\\"],\\"date\\":\\"Sat, 12 Dec 2020 13:28:58 -0000\\",\\"to\\":[\\"a.referrer@example.com\\"],\\"messageId\\":\\"<160777973839.803843.6703080364289671170@bunyan>\\",\\"subject\\":\\"[CCIW] Reference for Roy Armstrong\\"}}}",\n  "Timestamp" : "2020-12-12T13:29:00.409Z",\n  "SignatureVersion" : "1",\n  "Signature" : "fp/ladNgk9bI4s8zK7uCV4r8xpBDX1EBc1A/OjbiS/4AuDDqc6EmBsj/P/tYXU1Py2Qe3ih1HVxP2IEZtjl6qnoUixUh8KjGQfTD2Als0m/VgIIFfikwgn6UEpPbVIF4E9QmrgBmeUHnC5i8m7YSmw4zQLll9fccmkZjmMEjRAFa7SWaClFTcvWPK1KlK/sjiwi/ger+ZFz5M73V9HLfzT/pEbuCpr3++hXlh5QK2mLk8ANy7Nu+chl/4c7hl5DBZITZn4c1w09qsgIbUsZh/QUhrkFzxc5aQaRbODSiqfGWvvLHmzLGtJSV+7afWgi22zsMHDBMJml4u31rwiSdvg==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-010a507c1833636cd94bdb98bd93083a.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:319777369186:ses-bounces:a4995c81-f8b5-4879-8747-3897967e333e"\n}',
}

BAD_MESSAGE_1 = """
Return-Path: <no-reply@mvlar.top>
Received: from ns.mvlar.top (ns.mvlar.top [45.156.24.67])
 by inbound-smtp.eu-west-1.amazonaws.com with SMTP id 2f5o7drgukqhmg1aff9de61r6b9mtpe4lkuqr4o1
 for cpo@mailtest.cciw.co.uk;
 Fri, 27 May 2022 09:48:04 +0000 (UTC)
X-SES-Spam-Verdict: PASS
X-SES-Virus-Verdict: PASS
Received-SPF: pass (spfCheck: domain of mvlar.top designates 45.156.24.67 as permitted sender) client-ip=45.156.24.67; envelope-from=no-reply@mvlar.top; helo=ns.mvlar.top;
Authentication-Results: amazonses.com;
 spf=pass (spfCheck: domain of mvlar.top designates 45.156.24.67 as permitted sender) client-ip=45.156.24.67; envelope-from=no-reply@mvlar.top; helo=ns.mvlar.top;
 dmarc=pass header.from=mvlar.top;
X-SES-RECEIPT: AEFBQUFBQUFBQUFFL1duUTUrVXFTU2tPNCtmWi9sMVBZaEdSdjJzZnRoSjNlalFXL2t1Zkx6WW96N2RPVklXTkdaa0ZodVkrMHBxVUlRU1lDdHpPMFVVYm4xMlhQN3VuRDExQmFoQm9mbnVOSkFLRlpNbkJNekdBL1dGR0RqQUJDczkxQVBWWC95MVExU1puWGptdGV1bmVwdXpidFVTaU9tNjNNRW1Pb0dVUy94dXhPd0docHRvRkNDbFlSSGx1NUNta0tKY1J1Tkd0MlJJZzJVNDNhOFIydGw4UXFHTmh5aklsWDBhUGZ3NGdBK2JBSGJTb3UvM0Z0MUsyaFI2WmY2cUNzU0lWSmNlL3E0eXNEaE1KV0hIc1RIdHEyREZmWjhJa3pFbE94WHVzZE5IV1JxMnpXM0E9PQ==
X-SES-DKIM-SIGNATURE: a=rsa-sha256; q=dns/txt; b=e5KfJ/TahP5Yxni/34a9KRjIVhw9OQW6/h6+OUIXe/IuWnYvSj1giCvThtSYMsnCqYjyvAvy21fRwtPEUjZ6yD2/2cI8eFfXYUnEDbPXO7oD7SFpOeNdJzxit+ttEqh1PZlUz+iZ2LAHFDB85VSRb9gRcFmsTjKFkRsdhZzec4I=; c=relaxed/simple; s=ihchhvubuqgjsxyuhssfvqohv7z3u4hn; d=amazonses.com; t=1653644885; v=1; bh=Trju8PuifJ5awuxRLq5pO915rIw1dJU1CAWX5A91760=; h=From:To:Cc:Bcc:Subject:Date:Message-ID:MIME-Version:Content-Type:X-SES-RECEIPT;
Received: by ns.mvlar.top for <cpo@mailtest.cciw.co.uk>; Fri, 27 May 2022 09:48:00 +0000 (envelope-from <no-reply@mvlar.top>)
Date: Fri, 27 May 2022 09:48:00 GMT
To: <cpo@mailtest.cciw.co.uk>
Subject: Your Sunday Saving Is Waiting Inside...
From: "RB-USA® Sunglasses"<no-reply@mvlar.top>
Message-Id: <4b5f7d5e-87db-43b4-9b5c-64fc5217a5b7@mvlar.top>
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8
X-Priority: 2
X-Spam-Score: 1
ReturnReceipt: 1
DKIM-Signature: v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDJqILd3seO5ZwfYWfg8RbSJYbxFAbI5llEe+ASpw4l0mhoJlESL/SPs+2f+f8+Hgjlr7CvxdU1f+Baj0jAPbdOK9CprwgwM9csdeLXGjKvTjW2hsL6qtgMf1APhtvKWEf7h4IvXIiEyyb+70PtFr5Wb4I3+EiIr3AOAvhv4zBqcQIDAQAB
List-Unsubscribe: <https://www.sexydoll4u.com/list.cgi?cmd=unsub&lst=list>, <mailto:allen@sexydoll4u.com?subject=unsubscribe>

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>RayBan@Sunglasses</title>
</head>
<body>
<table width="620" border="0" cellspacing="5" cellpadding="0" align="center"  style="border:1px solid #898989;font-family:'Palatino Linotype', 'Book Antiqua', Palatino, serif;">
  <tr>
    <td colspan="2">
        <table width="620" border="0" cellspacing="0" cellpadding="0" align="center">
          <tr>
            <td height="5" bgcolor="#F0BB2D"></td>
            <td height="5" bgcolor="#E2DFD0"> </td>
            <td height="5" bgcolor="#000"> </td>
            <td height="5" bgcolor="#F0BB2D"></td>
            <td height="5" bgcolor="#E2DFD0"> </td>
            <td height="5" bgcolor="#000"> </td>
            <td height="5" bgcolor="#F0BB2D"></td>
            <td height="5" bgcolor="#E2DFD0"> </td>
            <td height="5" bgcolor="#000"> </td>
          </tr>
        </table>
    </td>
  </tr>
  <tr><td colspan="2">
      <span style="display:block; font-size:14px; text-align:center; margin:10px; font-weight:lighter; color:#555; letter-spacing:1px; line-height:20px;">Having trouble reading this email?<a style="color:#555;" href="https://subscriber.ijgdmf.com/SubscribeClick?6vz6=jw&5jg5=cpo@mailtest.cciw.co.uk&i2ex0wlfdx5053=&grabbed =Gregory grabbed a ribbed sandwich that had been strewn nearby he massaged it with his fi" target="_blank">View it in your browser</a>. <br>Not interested anymore? <a style="color:#555;" href="https://subscriber.ijgdmf.com/Uns?6vz6=jw&5jg5=cpo@mailtest.cciw.co.uk&i2ex0wlfdx5053=&grabbed =Gregory grabbed a ribbed sandwich that had been strewn nearby he massaged it with his fi" target="_blank">Unsubscribe instantly</a>. <a style="color:#000;" href="https://subscriber.ijgdmf.com/Spam?name=jw&5jg5=cpo@mailtest.cciw.co.uk&i2ex0wlfdx5053=&grabbed =Gregory grabbed a ribbed sandwich that had been strewn nearby he massaged it with his fi" target="_blank"><font color="red">SPAM</font></a></span>
  </td></tr>
  <tr>
    <td width="270" style="padding:0 20px; font-size:16px; line-height:20px; color:#555; text-align:center; letter-spacing:1px; background:#f9f9f9"><p><strong style="font-size:30px; font-weight:bold; line-height:40px; color:#000;">FINAL CLEARANCE:<br>EXTRA 90% OFF</strong></p>
      <p>From May 27th<br>
        <br> Use promo code 90XTRA at the checkout.<br>
    <span style="display:block; width:160px; font-size:17px; font-weight:bold; border:3px solid #000; background:#F7C030; padding:10px; margin:30px auto;"><a href="https://subscriber.ijgdmf.com/SubscribeClick?6vz6=jw&5jg5=cpo@mailtest.cciw.co.uk&i2ex0wlfdx5053=&grabbed =Gregory grabbed a ribbed sandwich that had been strewn nearby he massaged it with his fi" target="_blank" style="text-decoration:none; color:#fff;">SHOP NOW &gt;</a></span></p></td>
    <td width="270" style="padding:0 20px; background:#F7C030; font-size:30px; font-family:Tahoma, Geneva, sans-serif; letter-spacing:-2px; text-align:center">
         <p><strong style="font-size:37px; line-height:50px;">Ray-Ban SUNGLASSES</strong></p>
        <p><strong style="font-size:37px; line-height:50px;">GET AN EXTRA</strong><br>
          <strong style="font-size:55px; line-height:70px; color:#fff; background:#000; padding:0 10px; margin:10px 0; display:block;">90% OFF</strong><b style="color:#fff; line-height:35px">FINAL CLEARANCE</b><br>
          <strong style="font-size:27px; line-height:35px;">ENTER PROMO CODE</strong><br>
    <strong style="font-size:55px; line-height:70px; color:#fff; background:#000; padding:0 25px; margin:10px 0; display:block;">90XTRA</strong></p></td>
  </tr>
  <tr><td colspan="2" style="color:#555">
      <span style="display:block; width:100%; letter-spacing:1px; font-size:15px; line-height:30px; text-align:center; margin-top:10px; font-weight:bold;">Follow us for Exclusive Deals :<br>
      </span>
            <span style="font-size:14px; line-height:25px; margin:10px 0 5px; display:block; letter-spacing:1.5px; text-align:center;">Copyright @ 2020-2022 <a href="https://subscriber.ijgdmf.com/SubscribeClick?6vz6=jw&5jg5=cpo@mailtest.cciw.co.uk&i2ex0wlfdx5053=&grabbed =Gregory grabbed a ribbed sandwich that had been strewn nearby he massaged it with his fi" target="_blank" style="text-decoration:none; color:#555;">RB-USA® Sunglasses</a>. All Rights Reserved.</span>
  </td></tr>
  <tr>
    <td colspan="2">
        <table width="620" border="0" cellspacing="0" cellpadding="0" align="center">
          <tr>
            <td height="5" bgcolor="#F0BB2D"></td>
            <td height="5" bgcolor="#E2DFD0"></td>
            <td height="5" bgcolor="#000"> </td>
            <td height="5" bgcolor="#F0BB2D"></td>
            <td height="5" bgcolor="#E2DFD0"> </td>
            <td height="5" bgcolor="#000"> </td>
            <td height="5" bgcolor="#F0BB2D"></td>
            <td height="5" bgcolor="#E2DFD0"> </td>
            <td height="5" bgcolor="#000"> </td>
          </tr>
        </table>
    </td>
  </tr>
</table>
<span style="width:0px;height:0px"><img src="https://subscriber.ijgdmf.com/Subscribe?6vz6=jw&5jg5=cpo@mailtest.cciw.co.uk&i2ex0wlfdx5053=&k6=f30872a3f09a01fd40df9e2d27a440c9" width="1" alt="" style="border:none"></span></body>
</html>
""".strip()

"""
ses_api.describe_active_receipt_rule_set() response:

{'Metadata': {'CreatedTimestamp': datetime.datetime(2020, 12, 8, 21, 18, 31, 379000, tzinfo=tzutc()),
  'Name': 'default-rule-set'},
 'ResponseMetadata': {'HTTPHeaders': {'content-length': '1172',
   'content-type': 'text/xml',
   'date': 'Tue, 15 Dec 2020 10:01:09 GMT',
   'x-amzn-requestid': 'e12f91f1-a354-4b15-8b9b-34328722bbd3'},
  'HTTPStatusCode': 200,
  'RequestId': 'e12f91f1-a354-4b15-8b9b-34328722bbd3',
  'RetryAttempts': 0},
 'Rules': [{'Actions': [{'S3Action': {'BucketName': 'cciw-incoming-mail',
      'ObjectKeyPrefix': '',
      'TopicArn': 'arn:aws:sns:eu-west-1:319777369186:ses-incoming-notification'}}],
   'Enabled': True,
   'Name': 'webmaster-forward',
   'Recipients': ['camp-debug@mailtest.cciw.co.uk',
    'webmaster@cciw.co.uk',
    'webmaster@mailtest.cciw.co.uk'],
   'ScanEnabled': True,
   'TlsPolicy': 'Optional'}]}
"""
