from .models import *  # Import your model
from rest_framework import serializers
from adminapp.models import *

class UserRegSerializers(serializers.ModelSerializer):
    class Meta:
        model = userreg
        fields = '__all__'

class loginSerializers(serializers.ModelSerializer):
    class Meta:
        model = userreg
        fields = ['email', 'password']

class UserProfileSerializer(serializers.ModelSerializer):
    """Read-only profile view (never exposes the password)."""
    class Meta:
        model = userreg
        fields = ['id', 'fullname', 'email', 'profile']
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.ModelSerializer):
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
# Complaint serializers
#-----------------------------------------------------------------------------------------------------------

SOCIAL_ONLY_FIELDS = ['latitude', 'longitude', 'photo', 'aadhaar_photo', 'proof_of_work']
PERSONAL_ONLY_FIELDS = [
    'complaint_date', 'complaint_regarding', 'nature_of_complaint',
    'person_company_against', 'complaint_field', 'specific_complaint',
]


class ComplaintCreateSerializer(serializers.ModelSerializer):
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


class ComplaintSerializer(serializers.ModelSerializer):
    """Read-only complaint details, with readable category / officer names."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_officer_name = serializers.CharField(
        source='assigned_officer.Fullname', read_only=True, default=None,
    )

    class Meta:
        model = Complaints
        fields = '__all__'
        read_only_fields = [f.name for f in Complaints._meta.fields]
