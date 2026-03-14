from django.urls import path
from . import views
from .telegram_webhook import telegram_webhook_view
from .telegram_miniapp import (
    miniapp_page_view,
    miniapp_reference_view,
    miniapp_submit_view,
    miniapp_download_view,
)

app_name = 'proposals'

urlpatterns = [
    path('telegram/webhook/', telegram_webhook_view),
    path('tkp-app/', miniapp_page_view),
    path('tkp-app/reference/', miniapp_reference_view),
    path('tkp-app/submit/', miniapp_submit_view),
    path('tkp-app/download/<str:token>/', miniapp_download_view),
    path('table/', views.table_view, name='table'),
    path('kanban/', views.kanban_view, name='kanban'),
    path('kanban/card/<int:tkp_id>/', views.kanban_card_detail_view, name='kanban_card_detail'),
    path('kanban/card/<int:tkp_id>/notes/', views.kanban_save_notes_view, name='kanban_save_notes'),
    path('kanban/card/<int:tkp_id>/field/', views.kanban_card_field_save_view, name='kanban_card_field_save'),
    path('kanban/column/title/', views.kanban_column_title_view, name='kanban_column_title'),
    path('kanban/column/create/', views.kanban_column_create_view, name='kanban_column_create'),
    path('kanban/column/reorder/', views.kanban_column_reorder_view, name='kanban_column_reorder'),
    path('kanban/card/move/', views.kanban_card_move_view, name='kanban_card_move'),
    path('contracts/', views.contract_table_view, name='contract_table'),
    path('contract/<int:tkp_id>/', views.contract_form_view, name='contract_form'),
    path('contract/editor/', views.contract_editor_view, name='contract_editor'),
    path('contract/editor/save/', views.contract_save_from_editor_view, name='contract_save_from_editor'),
    path('contract/<int:contract_id>/card/', views.contract_card_view, name='contract_card'),
    path('contract/<int:contract_id>/download/<str:file_type>/', views.contract_download_file_view, name='contract_download'),
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
    path('send-tkp-email/', views.send_tkp_pdf_email_view, name='send_tkp_email'),
    path('download/<str:file_type>/', views.download_file_view, name='download_file'),
    path('start/', views.start_view, name='start'),
    path('instruction/', views.instruction_view, name='instruction'),
    path('', views.form_view, name='form'),
]
