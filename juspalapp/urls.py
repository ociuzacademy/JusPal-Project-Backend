from django.urls import path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from . import views
from .views import *

schema_view = get_schema_view(
    openapi.Info(
        title="JusPal User API",
        default_version='v1',
        description="API documentation for the JusPal user app (registration, login, profile, complaints).",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    #----------------------------------------------------------------------------------------------------------
    #    User URL's
    #----------------------------------------------------------------------------------------------------------
    
    #---------------------------------------------------------------------------------------------------------
    #   User Authentication URL's
    #-----------------------------------------------------------------------------------------------------------
    path('register/', UserCreateView.as_view(), name='user_register'),
    path('login/', loginCreateView.as_view(), name='user_login'),

    #---------------------------------------------------------------------------------------------------------
    #   User Profile URL's
    #-----------------------------------------------------------------------------------------------------------
    path('profile/<int:pk>/', UserProfileView.as_view(), name='user_profile'),
    path('profile/<int:pk>/edit/', UserProfileUpdateView.as_view(), name='user_profile_edit'),

    #---------------------------------------------------------------------------------------------------------
    #   User Complaint URL's
    #-----------------------------------------------------------------------------------------------------------
    path('complaints/create/', ComplaintCreateView.as_view(), name='complaint_create'),
    path('complaints/user/<int:user_id>/', UserComplaintListView.as_view(), name='user_complaints'),
    path('complaints/<str:complaint_id>/', ComplaintDetailView.as_view(), name='complaint_detail'),

    #---------------------------------------------------------------------------------------------------------
    #   User Legal Aid Chatbot URL's
    #-----------------------------------------------------------------------------------------------------------
    path('chatbot/ask/', ChatbotAskView.as_view(), name='chatbot_ask'),
    

    #---------------------------------------------------------------------------------------------------------
    #   Officer URL's
    #-----------------------------------------------------------------------------------------------------------
    
    #---------------------------------------------------------------------------------------------------------
    #   Officer Authentication URL's
    #-----------------------------------------------------------------------------------------------------------
    path('officer/login/', OfficerLoginView.as_view(), name='officer-login'),

    #---------------------------------------------------------------------------------------------------------
    #   Officer Profile URL's
    #-----------------------------------------------------------------------------------------------------------
    path('officer/profile/<int:pk>/', OfficerProfileView.as_view(), name='officer_profile'),
    path('officer/profile/<int:pk>/edit/', OfficerProfileUpdateView.as_view(), name='officer_profile_edit'),

    #---------------------------------------------------------------------------------------------------------
    #   Officer Assigned Complaint URL's
    #-----------------------------------------------------------------------------------------------------------
    path('officer/<int:officer_pk>/complaints/', OfficerAssignedComplaintListView.as_view(), name='officer_complaints'),
    path('officer/<int:officer_pk>/complaints/<str:complaint_id>/', OfficerAssignedComplaintDetailView.as_view(), name='officer_complaint_detail'),
    path('officer/<int:officer_pk>/complaints/<str:complaint_id>/update/', OfficerComplaintUpdateView.as_view(), name='officer_complaint_update'),



    #------------------------------------------------------------------------------------------------------------
    # Swagger / OpenAPI docs
    #------------------------------------------------------------------------------------------------------------
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
