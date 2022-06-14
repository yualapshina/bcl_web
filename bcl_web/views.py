from django.shortcuts import redirect

def blank(request):
    return redirect("biclustering/")