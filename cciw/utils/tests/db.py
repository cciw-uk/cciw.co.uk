def refresh(obj):
    return obj.__class__.objects.get(id=obj.id)
