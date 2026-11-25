import logging

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField, Count, Q, OuterRef, Subquery
from .serializers import *
from .models import *
from adminapp.models import *
from . import chatbot
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
    """
    POST /userapp/complaints/create/ — file a Social or Personal complaint.
    Accepts multipart/form-data (needed for photo uploads) or JSON (no files).
    """
    serializer_class = ComplaintCreateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_summary="File a complaint (Social or Personal)",
        operation_description=(
            "Social complaints get their priority predicted automatically from the description "
            "by the ML model. Personal complaints have no priority. "
            "Send multipart/form-data to upload photos, or application/json when there are no files."
        ),
        # Docs show the form-data version so Swagger UI keeps its file upload fields
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
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


#-----------------------------------------------------------------------------------------------------------
# Legal Aid Chatbot API's (Google Gemini)
#-----------------------------------------------------------------------------------------------------------

ELIGIBILITY_LABELS = {
    'likely_eligible': 'Likely eligible for free legal aid',
    'possibly_eligible': 'Possibly eligible for free legal aid',
    'not_eligible': 'Probably not eligible for free legal aid',
    'need_more_info': 'Need more details to check eligibility',
    'not_applicable': None,
}


#-----------------------------------------------------------------------------------------------------------
# Chatbot Ask API
#-----------------------------------------------------------------------------------------------------------
class ChatbotAskView(APIView):
    """POST /userapp/chatbot/ask/ — ask the legal aid assistant."""

    serializer_class = ChatAskSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @swagger_auto_schema(
        operation_summary="Ask the legal aid chatbot",
        operation_description=(
            "Send a question to the JusPal legal aid assistant. "
            "The chatbot does not save messages or conversation history."
        ),
        request_body=ChatAskSerializer,
        responses={
            200: "Assistant reply",
            400: "Validation errors",
            503: "Chatbot unavailable"
        },
        tags=["Legal Aid Chatbot"],
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'message': 'Please check the input.',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        question = serializer.validated_data['message']

        try:
            # No conversation history is passed
            answer = chatbot.ask_legal_assistant([], question)

        except chatbot.ChatbotUnavailable as exc:
            return Response(
                {'message': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        answer['eligibility_label'] = ELIGIBILITY_LABELS.get(
            answer['eligibility']
        )

        return Response(
            {
                'message': 'Reply generated successfully',
                'data': {
                    **answer,
                    'disclaimer': chatbot.DISCLAIMER
                }
            },
            status=status.HTTP_200_OK
        )


#-----------------------------------------------------------------------------------------------------------
# Officer API's
#-----------------------------------------------------------------------------------------------------------


#----------------------------------------------------------------------------------------------------------Officer Loginpdate
# Officer Login API
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
# Officer Profile API's
#-----------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------
# Officer Profile View API's
#-----------------------------------------------------------------------------------------------------------
class OfficerProfileView(APIView):
    """GET /userapp/officer/profile/<id>/ — view an officer's profile."""
    serializer_class = OfficerProfileSerializer

    @swagger_auto_schema(
        operation_summary="View officer profile",
        responses={200: OfficerProfileSerializer, 404: "Officer not found"},
        tags=["Officer Profile"],
    )
    def get(self, request, pk):
        officer = Officer.objects.select_related('category').filter(pk=pk).first()
        if not officer:
            return Response({'error': 'Officer not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(officer, context={'request': request})
        return Response({'message': 'Profile fetched successfully', 'data': serializer.data},
                        status=status.HTTP_200_OK)


#-----------------------------------------------------------------------------------------------------------
# Officer Profile Update API
#-----------------------------------------------------------------------------------------------------------
class OfficerProfileUpdateView(APIView):
    """
    PUT/PATCH /userapp/officer/profile/<id>/edit/ — edit an officer's profile.
    officer_id and Password cannot be changed here (they are ignored if sent).
    """
    serializer_class = OfficerProfileUpdateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _update(self, request, pk):
        officer = Officer.objects.select_related('category').filter(pk=pk).first()
        if not officer:
            return Response({'error': 'Officer not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(officer, data=request.data, partial=True,
                                           context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile updated successfully', 'data': serializer.data},
                            status=status.HTTP_200_OK)
        return Response({'message': 'Profile update failed. Please check the input.',
                         'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Edit officer profile (full update)",
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        request_body=OfficerProfileUpdateSerializer,
        responses={200: OfficerProfileUpdateSerializer, 400: "Validation errors", 404: "Officer not found"},
        tags=["Officer Profile"],
    )
    def put(self, request, pk):
        return self._update(request, pk)

    @swagger_auto_schema(
        operation_summary="Edit officer profile (partial update)",
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        request_body=OfficerProfileUpdateSerializer,
        responses={200: OfficerProfileUpdateSerializer, 400: "Validation errors", 404: "Officer not found"},
        tags=["Officer Profile"],
    )
    def patch(self, request, pk):
        return self._update(request, pk)


#-----------------------------------------------------------------------------------------------------------
# Officer Assigned Complaints API's
#-----------------------------------------------------------------------------------------------------------

# Critical first, then High, Medium, Low; complaints with no priority (Personal) last
PRIORITY_ORDER = Case(
    When(priority=Complaints.Priority.CRITICAL, then=Value(0)),
    When(priority=Complaints.Priority.HIGH, then=Value(1)),
    When(priority=Complaints.Priority.MEDIUM, then=Value(2)),
    When(priority=Complaints.Priority.LOW, then=Value(3)),
    default=Value(4),
    output_field=IntegerField(),
)


def officer_summary(officer):
    """Small officer block shown at the top of the officer complaint responses."""
    return {
        'id': officer.id,
        'officer_id': officer.officer_id,
        'officer_name': officer.Fullname,
        'department': officer.category.name if officer.category_id else None,
    }


#-----------------------------------------------------------------------------------------------------------
# Officer Assigned Complaint List API
#-----------------------------------------------------------------------------------------------------------
class OfficerAssignedComplaintListView(APIView):
    """GET /userapp/officer/<officer_pk>/complaints/ — complaints the admin assigned to this officer."""
    serializer_class = ComplaintSerializer

    @swagger_auto_schema(
        operation_summary="List complaints assigned to an officer",
        operation_description="Sorted by priority (Critical first), then newest first. "
                              "`counts` gives the officer's totals per status (ignores filters).",
        manual_parameters=[
            openapi.Parameter('type', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=Complaints.ComplaintType.values, description="Filter by complaint type"),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=Complaints.Status.values, description="Filter by status"),
            openapi.Parameter('priority', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=Complaints.Priority.values, description="Filter by priority"),
        ],
        responses={200: ComplaintSerializer(many=True), 404: "Officer not found"},
        tags=["Officer Complaints"],
    )
    def get(self, request, officer_pk):
        officer = Officer.objects.select_related('category').filter(pk=officer_pk).first()
        if not officer:
            return Response({'error': 'Officer not found'}, status=status.HTTP_404_NOT_FOUND)

        assigned = Complaints.objects.filter(assigned_officer_id=officer_pk)
        counts = assigned.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status_code=Complaints.Status.PENDING)),
            in_progress=Count('id', filter=Q(status_code=Complaints.Status.IN_PROGRESS)),
            resolved=Count('id', filter=Q(status_code=Complaints.Status.RESOLVED)),
            closed=Count('id', filter=Q(status_code=Complaints.Status.CLOSED)),
        )

        complaints = assigned.select_related('category', 'assigned_officer')
        complaint_type = request.query_params.get('type')
        status_filter = request.query_params.get('status')
        priority = request.query_params.get('priority')
        if complaint_type:
            complaints = complaints.filter(complaint_type=complaint_type)
        if status_filter:
            complaints = complaints.filter(status_code=status_filter)
        if priority:
            complaints = complaints.filter(priority=priority)
        complaints = complaints.order_by(PRIORITY_ORDER, '-created_at')

        serializer = self.serializer_class(complaints, many=True, context={'request': request})
        return Response({'message': 'Assigned complaints fetched successfully',
                         'officer': officer_summary(officer),
                         'counts': counts,
                         'count': len(serializer.data),
                         'data': serializer.data},
                        status=status.HTTP_200_OK)


#-----------------------------------------------------------------------------------------------------------
# Officer Assigned Complaint Detail API
#-----------------------------------------------------------------------------------------------------------
class OfficerAssignedComplaintDetailView(APIView):
    """GET /userapp/officer/<officer_pk>/complaints/<complaint_id>/ — one complaint assigned to this officer."""
    serializer_class = ComplaintSerializer

    @swagger_auto_schema(
        operation_summary="Get an assigned complaint's details",
        operation_description="Returns 404 if the complaint isn't assigned to this officer.",
        responses={200: ComplaintSerializer, 404: "Officer or complaint not found"},
        tags=["Officer Complaints"],
    )
    def get(self, request, officer_pk, complaint_id):
        officer = Officer.objects.select_related('category').filter(pk=officer_pk).first()
        if not officer:
            return Response({'error': 'Officer not found'}, status=status.HTTP_404_NOT_FOUND)

        complaint = (Complaints.objects.select_related('category', 'assigned_officer')
                     .filter(complaint_id=complaint_id, assigned_officer_id=officer_pk).first())
        if not complaint:
            return Response({'error': 'Complaint not found or not assigned to this officer'},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(complaint, context={'request': request})
        return Response({'message': 'Complaint fetched successfully',
                         'officer': officer_summary(officer),
                         'data': serializer.data},
                        status=status.HTTP_200_OK)


#-----------------------------------------------------------------------------------------------------------
# Officer Complaint Update API
#-----------------------------------------------------------------------------------------------------------
class OfficerComplaintUpdateView(APIView):
    """
    PATCH/PUT /userapp/officer/<officer_pk>/complaints/<complaint_id>/update/
    Personal: status_code + remarks (required).
    Social:   status_code + proof_of_work image (required unless already uploaded), remarks optional.
    """
    serializer_class = OfficerComplaintUpdateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _update(self, request, officer_pk, complaint_id):
        if not Officer.objects.filter(pk=officer_pk).exists():
            return Response({'error': 'Officer not found'}, status=status.HTTP_404_NOT_FOUND)

        complaint = (Complaints.objects.select_related('category', 'assigned_officer')
                     .filter(complaint_id=complaint_id, assigned_officer_id=officer_pk).first())
        if not complaint:
            return Response({'error': 'Complaint not found or not assigned to this officer'},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(complaint, data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({'message': 'Complaint update failed. Please check the input.',
                             'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # Replace the old proof image file when a new one is uploaded
        old_proof = complaint.proof_of_work.name if complaint.proof_of_work else None
        complaint = serializer.save()
        if old_proof and complaint.proof_of_work.name != old_proof:
            complaint.proof_of_work.storage.delete(old_proof)

        return Response({'message': f"Complaint {complaint.complaint_id} updated to {complaint.status_code}.",
                         'data': ComplaintSerializer(complaint, context={'request': request}).data},
                        status=status.HTTP_200_OK)

    _schema = dict(
        operation_description=(
            "**Personal:** `status_code` and `remarks` are required; `proof_of_work` is ignored.\n\n"
            "**Social:** `status_code` and `proof_of_work` (image) are required — proof can be skipped "
            "only if one was already uploaded; `remarks` is optional.\n\n"
            "Send multipart/form-data to upload the proof image."
        ),
        consumes=['multipart/form-data', 'application/x-www-form-urlencoded'],
        request_body=OfficerComplaintUpdateSerializer,
        responses={200: ComplaintSerializer, 400: "Validation errors",
                   404: "Officer or complaint not found"},
        tags=["Officer Complaints"],
    )

    @swagger_auto_schema(operation_summary="Update an assigned complaint (status / remarks / proof of work)", **_schema)
    def patch(self, request, officer_pk, complaint_id):
        return self._update(request, officer_pk, complaint_id)

    @swagger_auto_schema(operation_summary="Update an assigned complaint (PUT)", **_schema)
    def put(self, request, officer_pk, complaint_id):
        return self._update(request, officer_pk, complaint_id)

