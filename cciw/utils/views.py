from django.http import HttpResponse

def close_window_response():
    return HttpResponse("""<!DOCTYPE html><html><head><title>Close</title><script type="text/javascript">window.close()</script></head><body></body></html>""")
