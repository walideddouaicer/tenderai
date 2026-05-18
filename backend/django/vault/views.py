from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import VaultDocument


class VaultDocumentListView(APIView):
    def get(self, request):
        docs = VaultDocument.objects.filter(user=request.user).values(
            "id", "doc_type", "original_filename", "uploaded_at", "ocr_used"
        )
        return Response(list(docs))
