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