from django.db import models
from users.models import User


class VaultDocument(models.Model):
    DOC_TYPES = [
        ("tender_cps", "CPS / Cahier des Prescriptions Spéciales"),
        ("tender_rc", "RC / Règlement de la Consultation"),
        ("tender_cctp", "CCTP"),
        ("tender_bordereau", "Bordereau de Prix"),
        ("company_rc", "Registre du Commerce"),
        ("company_cnss", "Attestation CNSS"),
        ("company_fiscal", "Attestation Fiscale"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vault_documents")
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512)
    tender_id = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    classification = models.CharField(max_length=100, blank=True)
    ocr_used = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vault_documents"

    def __str__(self):
        return f"{self.doc_type} — {self.original_filename}"
