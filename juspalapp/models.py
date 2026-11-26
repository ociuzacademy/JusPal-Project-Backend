from django.db import models, transaction, IntegrityError
from django.db.models.functions import Length
from django.utils import timezone

# Create your models here.

# ==============================================================================
# User Registration Model
# ==============================================================================

class userreg(models.Model):
    fullname = models.CharField(max_length=50)
    password = models.CharField(max_length=50)  
    email = models.EmailField()
    profile = models.ImageField(null=True, blank=True, upload_to='profiles/')

    def __str__(self):
        return self.fullname


# ==============================================================================
# Complaints — ONE model / ONE table for both Social and Personal complaints
# ==============================================================================

class Complaints(models.Model):

    # ── Choices ───────────────────────────────────────────────────────────────
    class ComplaintType(models.TextChoices):
        SOCIAL = 'Social', 'Social'
        PERSONAL = 'Personal', 'Personal'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        IN_PROGRESS = 'In Progress', 'In Progress'
        RESOLVED = 'Resolved', 'Resolved'
        CLOSED = 'Closed', 'Closed'

    class Priority(models.TextChoices):
        CRITICAL = 'Critical', 'Critical'
        HIGH = 'High', 'High'
        MEDIUM = 'Medium', 'Medium'
        LOW = 'Low', 'Low'

    # Prefix used in the generated complaint_id for each type
    ID_PREFIXES = {
        ComplaintType.SOCIAL: 'SOC',
        ComplaintType.PERSONAL: 'PER',
    }

    # ── Common fields (both types) ────────────────────────────────────────────
    user = models.ForeignKey(
        userreg, on_delete=models.CASCADE, related_name='complaints',
    )
    complaint_id = models.CharField(
        max_length=20, unique=True, editable=False, blank=True,
        help_text="Auto-generated, e.g. SOC-2026-0001 / PER-2026-0001",
    )
    complaint_type = models.CharField(max_length=10, choices=ComplaintType.choices)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(
        'adminapp.Category', on_delete=models.PROTECT, related_name='complaints',
    )
    assigned_officer = models.ForeignKey(
        'adminapp.Officer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_complaints',
    )
    status_code = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    date_of_incident = models.DateField()
    remarks = models.TextField(null=True, blank=True)

    # ── Social-only fields ────────────────────────────────────────────────────
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    photo = models.ImageField(upload_to='complaints/photos/', null=True, blank=True)
    aadhaar_photo = models.ImageField(upload_to='complaints/aadhaar/', null=True, blank=True)
    proof_of_work = models.ImageField(upload_to='complaints/proof_of_work/', null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, null=True, blank=True)

    # ── Personal-only fields ──────────────────────────────────────────────────
    complaint_date = models.DateField(null=True, blank=True)
    complaint_regarding = models.CharField(max_length=200, null=True, blank=True)
    nature_of_complaint = models.CharField(max_length=200, null=True, blank=True)
    person_company_against = models.CharField(max_length=200, null=True, blank=True)
    complaint_field = models.CharField(max_length=200, null=True, blank=True)
    specific_complaint = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'complaints'
        ordering = ['-created_at']
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'
        indexes = [
            models.Index(fields=['complaint_type', 'status_code']),
        ]

    def __str__(self):
        return f"{self.complaint_id} - {self.complaint_type} - {self.name} ({self.status_code})"

    # ── Automatic complaint ID generation ─────────────────────────────────────
    MAX_ID_RETRIES = 5

    def _next_complaint_id(self):
        """
        Build the next ID for this complaint's type and the current year,
        e.g. 'SOC-2026-0007'. Must be called inside a transaction: the latest
        matching row is locked (SELECT ... FOR UPDATE) so concurrent creators
        of the same type/year wait for each other instead of reading the same number.
        """
        prefix = f"{self.ID_PREFIXES[self.complaint_type]}-{timezone.now().year}-"
        last = (
            Complaints.objects.select_for_update()
            .filter(complaint_id__startswith=prefix)
            # Sort by length first so 10000 sorts after 9999 (string sort alone would not)
            .order_by(Length('complaint_id').desc(), '-complaint_id')
            .values_list('complaint_id', flat=True)
            .first()
        )
        next_number = int(last.rsplit('-', 1)[1]) + 1 if last else 1
        return f"{prefix}{next_number:04d}"

    def save(self, *args, **kwargs):
        # Existing complaints (or one with an ID already set) save normally
        if self.pk or self.complaint_id:
            return super().save(*args, **kwargs)

        # New complaint: generate the ID and insert in one transaction.
        # The row lock prevents most clashes; if two inserts still race
        # (e.g. the very first complaint of a year, when there's no row to lock),
        # the unique constraint rejects one and we retry with a fresh number.
        for attempt in range(self.MAX_ID_RETRIES):
            try:
                with transaction.atomic():
                    self.complaint_id = self._next_complaint_id()
                    return super().save(*args, **kwargs)
            except IntegrityError:
                clashed_id = self.complaint_id
                self.complaint_id = ''
                self.pk = None
                # Only retry on a duplicate complaint_id; re-raise any other error
                id_taken = Complaints.objects.filter(complaint_id=clashed_id).exists()
                if not id_taken or attempt == self.MAX_ID_RETRIES - 1:
                    raise

class Feedback(models.Model):
    user = models.ForeignKey('userreg', on_delete=models.CASCADE)  # Linking feedback to a user
    rate = models.PositiveIntegerField()  # Rating (out of 5)
    feedback = models.TextField()  # User's feedback text
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for feedback submission

    def __str__(self):
        return f"Feedback from {self.user.fullname} - {self.rate}/5"
