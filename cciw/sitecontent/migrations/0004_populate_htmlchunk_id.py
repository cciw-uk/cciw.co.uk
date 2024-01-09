# Generated by Django 4.2.5 on 2024-01-09 21:17

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("sitecontent", "0003_htmlchunk_id"),
    ]

    operations = [
        migrations.RunSQL(
            """
WITH numbered_rows AS (
  SELECT name,
         ROW_NUMBER() OVER (ORDER BY name) AS row_num
  FROM sitecontent_htmlchunk
)
UPDATE sitecontent_htmlchunk
SET id = numbered_rows.row_num
FROM numbered_rows
WHERE numbered_rows.name = sitecontent_htmlchunk.name;
""",
            "",
        )
    ]
