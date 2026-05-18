from django.urls import path
from .views import VaultDocumentListView

urlpatterns = [
    path("documents/", VaultDocumentListView.as_view()),
]
