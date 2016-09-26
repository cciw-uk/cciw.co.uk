from django.db.models.signals import post_save

from cciw.cciwmain.models import CampName, generate_colors_less


generate_colors_less_w = lambda sender, **kwargs: generate_colors_less(update_existing=True)
post_save.connect(generate_colors_less_w, CampName)
