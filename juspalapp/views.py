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