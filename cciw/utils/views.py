from django.http import HttpResponse

def close_window_response():
    return HttpResponse("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
            "http://www.w3.org/TR/html4/loose.dtd"><html><head><title>Close</title><script type="text/javascript">window.close()</script></head><body></body></html>""")
