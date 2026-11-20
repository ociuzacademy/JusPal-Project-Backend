import logging

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import *
from .models import *
from adminapp.models import *
# Create your views here.


#----------------------------------------------------------------------------------------------------------
# USER API'S
#----------------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------------
# User Creation
#----------------------------------------------------------------------------------------------------------
class UserCreateView(APIView):
    serializer_class = UserRegSerializers
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        request_body=UserRegSerializers,
        responses={201: UserRegSerializers, 400: "Validation errors"},
        tags=["User"],
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            success_response = {
                "message": "User created successfully!",
                "role": "user",
                "data": serializer.data
            }
            return Response(success_response, status=status.HTTP_201_CREATED)

        error_response = {
            "message": "User creation failed. Please check the input.",
            "errors": serializer.errors
        }
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
#-----------------------------------------------------------------------------------------------------------
# User Login
#-----------------------------------------------------------------------------------------------------------
class loginCreateView(APIView):
    serializer_class = loginSerializers

    @swagger_auto_schema(
        operation_summary="User login",
        request_body=loginSerializers,
        responses={200: "Login successful", 400: "Invalid credentials"},
        tags=["User"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            password = serializer.validated_data['password']
            email = serializer.validated_data['email']

            # Authenticate user
            user = userreg.objects.filter(email=email).first()
            if user and user.password == password:
                return Response({'message': 'User Login successful','id':user.id,'role': 'user','email':user.email,'password':user.password,'username':user.fullname}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#-----------------------------------------------------------------------------------------------------------
# User profile
#-----------------------------------------------------------------------------------------------------------
class UserProfileView(APIView):
    """GET /userapp/profile/<id>/ — view a user's profile."""
    serializer_class = UserProfileSerializer

    @swagger_auto_schema(
        operation_summary="View user profile",
        responses={200: UserProfileSerializer, 404: "User not found"},
        tags=["Profile"],
    )
    def get(self, request, pk):
        user = userreg.objects.filter(pk=pk).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(user, context={'request': request})
        return Response({'message': 'Profile fetched successfully', 'data': serializer.data},
                        status=status.HTTP_200_OK)

#-----------------------------------------------------------------------------------------------------------
# User Profile Update
#-----------------------------------------------------------------------------------------------------------
class UserProfileUpdateView(APIView):
    """PUT/PATCH /userapp/profile/<id>/edit/ — edit a user's profile (multipart/form-data, supports image upload)."""
    serializer_class = UserProfileUpdateSerializer
    parser_classes = [MultiPartParser, FormParser]

    def _update(self, request, pk):
        user = userreg.objects.filter(pk=pk).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(user, data=request.data, partial=True,
                                           context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile updated successfully', 'data': serializer.data},
                            status=status.HTTP_200_OK)
        return Response({'message': 'Profile update failed. Please check the input.',
                         'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Edit user profile (full update)",
        request_body=UserProfileUpdateSerializer,
        responses={200: UserProfileUpdateSerializer, 400: "Validation errors", 404: "User not found"},
        tags=["Profile"],
    )
    def put(self, request, pk):
        return self._update(request, pk)

    @swagger_auto_schema(
        operation_summary="Edit user profile (partial update)",
        request_body=UserProfileUpdateSerializer,
        responses={200: UserProfileUpdateSerializer, 400: "Validation errors", 404: "User not found"},
        tags=["Profile"],
    )
    def patch(self, request, pk):
        return self._update(request, pk)



#-----------------------------------------------------------------------------------------------------------
# Officer API's
#-----------------------------------------------------------------------------------------------------------


#----------------------------------------------------------------------------------------------------------Officer Loginpdate
# Officer Login
#-----------------------------------------------------------------------------------------------------------
class OfficerLoginView(APIView):
    serializer_class = OfficerLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            officer = serializer.validated_data
            return Response({"message": "Login successful", "id":officer.id,"officer_id": officer.officer_id,"password":officer.Password}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#-----------------------------------------------------------------------------------------------------------
# Complaint API's
#-----------------------------------------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def predict_social_priority(text):
    """
    Predict a Social complaint's priority with the ML model in ai_model/.
    Returns (priority, confidence %) or (None, None) if prediction isn't possible,
    so a model problem never blocks a citizen from filing a complaint.
    The model is imported lazily: it loads once, on the first Social complaint.
    """
    try:
        from ai_model.predict_priority import predict_priority
        label, confidence = predict_priority(text)
        label = str(label)
        if label not in Complaints.Priority.values:
            logger.warning("Priority model returned unknown label %r", label)
            return None, None
        return label, float(confidence)
    except Exception:
        logger.exception("Priority prediction failed")
        return None, None


class ComplaintCreateView(APIView):
    """POST /userapp/complaints/create/ — file a Social or Personal complaint."""
    serializer_class = ComplaintCreateSerializer
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="File a complaint (Social or Personal)",
        operation_description=(
            "Social complaints get their priority predicted automatically from the description "
            "by the ML model. Personal complaints have no priority."
        ),
        request_body=ComplaintCreateSerializer,
        responses={201: ComplaintCreateSerializer, 400: "Validation errors"},
        tags=["Complaints"],
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({'message': 'Complaint submission failed. Please check the input.',
                             'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        extra = {}
        confidence = None
        if serializer.validated_data['complaint_type'] == Complaints.ComplaintType.SOCIAL:
            priority, confidence = predict_social_priority(serializer.validated_data['description'])
            extra['priority'] = priority

        complaint = serializer.save(**extra)
        response = {
            'message': f"Complaint {complaint.complaint_id} submitted successfully!",
            'data': ComplaintSerializer(complaint, context={'request': request}).data,
        }
        if complaint.complaint_type == Complaints.ComplaintType.SOCIAL:
            response['priority_confidence'] = confidence
        return Response(response, status=status.HTTP_201_CREATED)


class UserComplaintListView(APIView):
    """GET /userapp/complaints/user/<user_id>/ — all complaints filed by a user."""
    serializer_class = ComplaintSerializer

    @swagger_auto_schema(
        operation_summary="List a user's complaints",
        manual_parameters=[
            openapi.Parameter('type', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=Complaints.ComplaintType.values,
                              description="Filter by complaint type"),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=Complaints.Status.values,
                              description="Filter by status"),
        ],
        responses={200: ComplaintSerializer(many=True), 404: "User not found"},
        tags=["Complaints"],
    )
    def get(self, request, user_id):
        if not userreg.objects.filter(pk=user_id).exists():
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        complaints = Complaints.objects.filter(user_id=user_id).select_related('category', 'assigned_officer')
        complaint_type = request.query_params.get('type')
        status_filter = request.query_params.get('status')
        if complaint_type:
            complaints = complaints.filter(complaint_type=complaint_type)
        if status_filter:
            complaints = complaints.filter(status_code=status_filter)

        serializer = self.serializer_class(complaints, many=True, context={'request': request})
        return Response({'message': 'Complaints fetched successfully',
                         'count': len(serializer.data),
                         'data': serializer.data},
                        status=status.HTTP_200_OK)


class ComplaintDetailView(APIView):
    """GET /userapp/complaints/<complaint_id>/ — one complaint, e.g. SOC-2026-0001."""
    serializer_class = ComplaintSerializer

    @swagger_auto_schema(
        operation_summary="Get complaint details by complaint ID",
        responses={200: ComplaintSerializer, 404: "Complaint not found"},
        tags=["Complaints"],
    )
    def get(self, request, complaint_id):
        complaint = (Complaints.objects.select_related('category', 'assigned_officer')
                     .filter(complaint_id=complaint_id).first())
        if not complaint:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(complaint, context={'request': request})
        return Response({'message': 'Complaint fetched successfully', 'data': serializer.data},
                        status=status.HTTP_200_OK)
