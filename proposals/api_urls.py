"""URL маршруты API для ТКП (OpenClaw / Telegram мост)."""

from django.urls import path

from . import api_views

app_name = 'proposals_api'

urlpatterns = [
    path('tkp/reference/', api_views.tkp_reference_view),
    path('tkp/draft/', api_views.tkp_draft_create_view),
    path('tkp/draft/<int:draft_id>/set-field/', api_views.tkp_draft_set_field_view),
    path('tkp/draft/<int:draft_id>/submit-draft/', api_views.tkp_draft_submit_draft_view),
    path('tkp/draft/<int:draft_id>/submit-final/', api_views.tkp_draft_submit_final_view),
]
