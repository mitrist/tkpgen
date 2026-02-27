from django.urls import path
from . import views

app_name = 'proposals'

urlpatterns = [
    path('table/', views.table_view, name='table'),
    path('contract/<int:tkp_id>/', views.contract_form_view, name='contract_form'),
    path('tariffs/', views.tariffs_view, name='tariffs'),
    path('service-descriptions/', views.service_descriptions_view, name='service_descriptions'),
    path('requisites/', views.requisites_add_view, name='requisites_add'),
    path('counterparties/', views.counterparties_view, name='counterparties'),
    path('counterparties/search/', views.counterparty_search_view, name='counterparty_search'),
    path('counterparty/<int:pk>/json/', views.counterparty_json_view, name='counterparty_json'),
    path('complex/', views.complex_form_view, name='complex_form'),
    path('complex/confirm/', views.complex_confirm_view, name='complex_confirm'),
    path('confirm/', views.confirm_view, name='confirm'),
    path('download-success/', views.download_success_view, name='download_success'),
    path('download/<str:file_type>/', views.download_file_view, name='download_file'),
    path('', views.form_view, name='form'),
]
