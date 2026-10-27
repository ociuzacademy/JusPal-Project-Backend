from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_login, name='admin_login'),
    path('admin_index/', views.admin_index, name='admin_index'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
    path('add_category/', views.add_category, name='add_category'),
    path('category_list/', views.category_list, name='category_list'),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete_category/<int:category_id>/', views.delete_category, name='delete_category'),
    # path('add_officer/', views.add_officer, name='add_officer'),
    # path('list_officers/', views.list_officers, name='list_officers'),
    # path('edit_officer/<int:officer_id>/', views.edit_officer, name='edit_officer'),
    # path('delete_officer/<int:officer_id>/', views.delete_officer, name='delete_officer'),
]