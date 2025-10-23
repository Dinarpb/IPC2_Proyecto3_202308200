from django.shortcuts import render, redirect
from django.http import JsonResponse

# Create your views here.
import requests

API_URL = "http://localhost:3000/"


def index(request):
    return render(request, "index.html")
