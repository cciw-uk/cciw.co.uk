from django.http import HttpResponse

def close_window_response():
    return HttpResponse('<script type="text/javascript">window.close()</script>')
