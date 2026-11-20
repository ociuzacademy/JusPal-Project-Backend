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
        description="API documentation for the JusPal user app (registration, login, profile).",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # User APIs
    path('register/', UserCreateView.as_view(), name='user_register'),
    path('login/', loginCreateView.as_view(), name='user_login'),
    path('profile/<int:pk>/', UserProfileView.as_view(), name='user_profile'),
    path('profile/<int:pk>/edit/', UserProfileUpdateView.as_view(), name='user_profile_edit'),

    # Swagger / OpenAPI docs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
