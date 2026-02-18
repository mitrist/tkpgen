from django.urls import path
from . import views

app_name = 'proposals'

urlpatterns = [
    path('table/', views.table_view, name='table'),
    path('confirm/', views.confirm_view, name='confirm'),
    path('', views.form_view, name='form'),
]
