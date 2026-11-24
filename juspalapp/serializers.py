from django.db import models as dj_models
from rest_framework import serializers
from .models import *  # Import your model
from adminapp.models import *


#-----------------------------------------------------------------------------------------------------------
# Media path fields - return images/files as "/media/..." instead of "http://host/media/..."
#-----------------------------------------------------------------------------------------------------------

class MediaPathFileField(serializers.FileField):
    def to_representation(self, value):
        if not value:
            return None
        return value.url  # e.g. /media/profiles/photo.jpg


class MediaPathImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None
        return value.url


class MediaPathModelSerializer(serializers.ModelSerializer):
    """ModelSerializer whose ImageField / FileField values are relative /media/... paths."""
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        dj_models.ImageField: MediaPathImageField,
        dj_models.FileField: MediaPathFileField,
    }

#-----------------------------------------------------------------------------------------------------------
# User Serializers
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
# User Register Serializer
#-----------------------------------------------------------------------------------------------------------

class UserRegSerializers(MediaPathModelSerializer):
    class Meta:
        model = userreg
        fields = '__all__'

#-----------------------------------------------------------------------------------------------------------
# User Login Serializer
#-----------------------------------------------------------------------------------------------------------

class loginSerializers(MediaPathModelSerializer):
    class Meta:
        model = userreg
        fields = ['email', 'password']

#-----------------------------------------------------------------------------------------------------------
# User Profile Serializers
#-----------------------------------------------------------------------------------------------------------

class UserProfileSerializer(MediaPathModelSerializer):
    """Read-only profile view (never exposes the password)."""
    class Meta:
        model = userreg
        fields = ['id', 'fullname', 'email', 'profile']
        read_only_fields = fields

#-----------------------------------------------------------------------------------------------------------
# User Profile Update Serializer
#-----------------------------------------------------------------------------------------------------------

class UserProfileUpdateSerializer(MediaPathModelSerializer):
    """Edit profile: all fields optional; password is write-only."""
    password = serializers.CharField(write_only=True, required=False, max_length=50)

    class Meta:
        model = userreg
        fields = ['id', 'fullname', 'email', 'password', 'profile']
        read_only_fields = ['id']
        extra_kwargs = {
            'fullname': {'required': False},
            'email': {'required': False},
            'profile': {'required': False},
        }

    def validate_email(self, value):
        qs = userreg.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


#-----------------------------------------------------------------------------------------------------------
# Complaint serializers
#-----------------------------------------------------------------------------------------------------------

SOCIAL_ONLY_FIELDS = ['latitude', 'longitude', 'photo', 'aadhaar_photo', 'proof_of_work']
PERSONAL_ONLY_FIELDS = [
    'complaint_date', 'complaint_regarding', 'nature_of_complaint',
    'person_company_against', 'complaint_field', 'specific_complaint',
]


class ComplaintCreateSerializer(MediaPathModelSerializer):
    """
    Create a Social or Personal complaint.
    complaint_id, status, priority, officer and remarks are set by the system, not the user.
    """
    class Meta:
        model = Complaints
        fields = [
            'id', 'complaint_id', 'user', 'complaint_type',
            'name', 'email', 'phone', 'address', 'city', 'description',
            'category', 'date_of_incident',
            *SOCIAL_ONLY_FIELDS,
            *PERSONAL_ONLY_FIELDS,
            'priority', 'status_code', 'assigned_officer', 'remarks', 'created_at',
        ]
        read_only_fields = [
            'id', 'complaint_id', 'priority', 'status_code',
            'assigned_officer', 'remarks', 'created_at',
        ]

    def validate(self, data):
        # Drop fields that don't belong to the chosen complaint type,
        # so a Personal complaint never stores a location/photo and vice versa.
        if data.get('complaint_type') == Complaints.ComplaintType.SOCIAL:
            for field in PERSONAL_ONLY_FIELDS:
                data.pop(field, None)
        else:
            for field in SOCIAL_ONLY_FIELDS:
                data.pop(field, None)
        return data


class ComplaintSerializer(MediaPathModelSerializer):
    """Read-only complaint details, with readable category / officer names."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_officer_name = serializers.CharField(
        source='assigned_officer.Fullname', read_only=True, default=None,
    )

    class Meta:
        model = Complaints
        fields = '__all__'
        read_only_fields = [f.name for f in Complaints._meta.fields]

#-----------------------------------------------------------------------------------------------------------
# Officer Serializers
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
# Officer Login Serializer
#-----------------------------------------------------------------------------------------------------------
class OfficerLoginSerializer(serializers.Serializer):
    officer_id = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        officer_id = data.get("officer_id")
        password = data.get("password")

        try:
            officer = Officer.objects.get(officer_id=officer_id)
        except Officer.DoesNotExist:
            raise serializers.ValidationError("Invalid officer ID or password.")

        if officer.Password != password:
            raise serializers.ValidationError("Invalid officer ID or password.")

        return officer

#-----------------------------------------------------------------------------------------------------------
# Officer Profile Serializers
#-----------------------------------------------------------------------------------------------------------

class OfficerProfileSerializer(MediaPathModelSerializer):
    """Read-only officer profile (never exposes the password)."""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Officer
        fields = ['id', 'officer_id', 'Fullname', 'Email', 'Phone', 'Gender',
                  'category', 'category_name', 'profile', 'id_card']
        read_only_fields = fields


class OfficerProfileUpdateSerializer(MediaPathModelSerializer):
    """
    Edit officer profile. officer_id and Password are not editable here;
    category (department) stays admin-controlled. All fields are optional.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Officer
        fields = ['id', 'officer_id', 'Fullname', 'Email', 'Phone', 'Gender',
                  'category', 'category_name', 'profile', 'id_card']
        read_only_fields = ['id', 'officer_id', 'category']
        extra_kwargs = {
            'Fullname': {'required': False},
            'Email': {'required': False},
            'Phone': {'required': False},
            'Gender': {'required': False},
            'profile': {'required': False},
            'id_card': {'required': False},
        }

    def validate_Email(self, value):
        qs = Officer.objects.filter(Email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_Phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

#-----------------------------------------------------------------------------------------------------------
# Officer Complaint Update Serializer
#-----------------------------------------------------------------------------------------------------------

class OfficerComplaintUpdateSerializer(MediaPathModelSerializer):
    """
    Officer updates a complaint assigned to them.
      Personal: status_code + remarks (required). proof_of_work is not used and is ignored.
      Social:   status_code + proof_of_work (required unless one is already uploaded),
                remarks optional.
    """
    status_code = serializers.ChoiceField(choices=Complaints.Status.choices)
    remarks = serializers.CharField(required=False, allow_blank=True)
    proof_of_work = serializers.ImageField(required=False)

    class Meta:
        model = Complaints
        fields = ['status_code', 'remarks', 'proof_of_work']

    def validate(self, data):
        complaint = self.instance
        remarks = (data.get('remarks') or '').strip()

        if complaint.complaint_type == Complaints.ComplaintType.PERSONAL:
            data.pop('proof_of_work', None)
            if not remarks:
                raise serializers.ValidationError(
                    {'remarks': 'Remarks are required when updating a Personal complaint.'})
            data['remarks'] = remarks
        else:  # Social
            if not data.get('proof_of_work') and not complaint.proof_of_work:
                raise serializers.ValidationError(
                    {'proof_of_work': 'Proof of work is required when updating a Social complaint.'})
            if 'remarks' in data:
                data['remarks'] = remarks or None
        return data
