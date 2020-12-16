# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='HtmlChunk',
            fields=[
                ('name', models.SlugField(verbose_name='name', primary_key=True, serialize=False)),
                ('html', models.TextField(verbose_name='HTML')),
                ('page_title', models.CharField(verbose_name='page title (for chunks that are pages)', blank=True, max_length=100)),
            ],
            options={
                'verbose_name': 'HTML chunk',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MenuLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(verbose_name='title', max_length=50)),
                ('url', models.CharField(verbose_name='URL', max_length=100)),
                ('extra_title', models.CharField(verbose_name='Disambiguation title', blank=True, max_length=100)),
                ('listorder', models.SmallIntegerField(verbose_name='order in list')),
                ('visible', models.BooleanField(verbose_name='Visible', default=True)),
                ('parent_item', models.ForeignKey(verbose_name='Parent item (none = top level)', null=True, to='sitecontent.MenuLink', blank=True, related_name='child_links', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('-parent_item__id', 'listorder'),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='htmlchunk',
            name='menu_link',
            field=models.ForeignKey(verbose_name='Associated URL', null=True, to='sitecontent.MenuLink', blank=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
