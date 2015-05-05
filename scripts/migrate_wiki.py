#!/usr/bin/env python

import os
import re
import subprocess

os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'


from djiki.models import Page
from wiki.models import Article, ArticleRevision, URLPath, ArticleForObject


def creole_to_markdown(creole):
    from creole import Parser
    from creole.html_emitter import HtmlEmitter

    html = HtmlEmitter(Parser(creole).parse()).emit().encode('utf-8', 'ignore')
    p = subprocess.Popen(["pandoc", "-f", "html", "-t", "markdown"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    md = p.communicate(html)[0]
    md = re.sub(r"\[([A-Za-z0-9]+)\]\(\1\)", r"[\1](/wiki/\1/)", md)
    return md


def main():
    ArticleForObject.objects.all().delete()
    URLPath.objects.all().delete()
    Article.objects.all().delete()
    ArticleRevision.objects.all().delete()

    root = URLPath.create_root()
    rev = root.article.current_revision
    rev.title = "Index"
    rev.content = "[article_list]"
    rev.save()

    for p in Page.objects.all():
        if p.title == "Index":
            continue
        first_rev = p.revisions.all().order_by('created')[0]
        last_rev = p.revisions.all().order_by('-created')[0]
        article = Article.objects.create(
            owner=first_rev.author,
        )
        previous_revision = None
        for revno, r in enumerate(p.revisions.all().order_by('created')):
            revision = ArticleRevision.objects.create(
                article=article,
                content=creole_to_markdown(r.content),
                title=p.title,
                revision_number=revno + 1,
                previous_revision=previous_revision,
                user=r.author,
            )
            revision.save()
            # Must be after last save:
            ArticleRevision.objects.filter(id=revision.id).update(
                created=r.created,
                modified=r.created,
            )
            previous_revision = revision
        article.current_revision = article.articlerevision_set.latest()
        article.save()
        # Must be after last save:
        Article.objects.filter(id=article.id).update(
            created=first_rev.created,
            modified=last_rev.created,
        )
        urlpath = URLPath.objects.create(site_id=1,
                                         parent=root,
                                         slug=p.title,
                                         article=article,
                                         )
        article.add_object_relation(urlpath)


if __name__ == '__main__':
    main()
