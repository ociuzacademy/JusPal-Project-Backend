from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import tbl_admin, Category, Officer


# ==============================================================================
# Admin Authentication & Dashboard
# ==============================================================================

def admin_login(request):
    """Handles admin login and sets session data."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        admin = tbl_admin.objects.filter(email=email, password=password, is_active=True).first()
        if admin:
            request.session['admin_id'] = admin.id
            request.session['admin_name'] = admin.name
            request.session['admin_role'] = admin.role
            return redirect('admin_index')
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "adminapp/login.html")


def admin_index(request):
    """Admin dashboard view."""
    officer_count = Officer.objects.count()
    category_count = Category.objects.count()
    context = {
        'officer_count': officer_count,
        'category_count': category_count,
    }
    return render(request, "adminapp/admin_index.html", context)


def admin_logout(request):
    """Clears the admin session and redirects to login."""
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect('admin_login')


# ==============================================================================
# Category Management
# ==============================================================================

def add_category(request):
    """Create a new category / department."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            messages.error(request, "Department name is required.")
        else:
            Category.objects.create(name=name, description=description)
            messages.success(request, "Department added successfully!")
            return redirect("category_list")

    return render(request, "adminapp/add_category.html")


def category_list(request):
    """List all categories / departments."""
    categories = Category.objects.all()
    return render(request, "adminapp/category_list.html", {"categories": categories})


def edit_category(request, category_id):
    """Edit an existing category / department."""
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            messages.error(request, "Department name is required.")
        else:
            category.name = name
            category.description = description
            category.save()
            messages.success(request, "Department updated successfully!")
            return redirect("category_list")

    return render(request, "adminapp/edit_category.html", {"category": category})


def delete_category(request, category_id):
    """Delete a category."""
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, "Category deleted successfully!")
    return redirect("category_list")


# # ==============================================================================
# # Officer Management
# # ==============================================================================

# def add_officer(request):
#     """Add a new officer with profile and ID card."""
#     if request.method == 'POST':
#         fullname = request.POST.get('Fullname', '').strip()
#         email = request.POST.get('Email', '').strip()
#         password = request.POST.get('Password', '').strip()
#         phone = request.POST.get('Phone', '').strip()
#         gender = request.POST.get('Gender', '').strip()
#         category_id = request.POST.get('category')
#         officer_id = request.POST.get('officer_id', '').strip()
#         id_card = request.FILES.get('id_card')
#         profile = request.FILES.get('profile')

#         if not all([fullname, email, password, phone, gender, category_id, officer_id]):
#             messages.error(request, "All required fields must be filled.")
#         else:
#             category = get_object_or_404(Category, id=category_id)
#             Officer.objects.create(
#                 Fullname=fullname,
#                 Email=email,
#                 Password=password,
#                 Phone=phone,
#                 Gender=gender,
#                 category=category,
#                 officer_id=officer_id,
#                 id_card=id_card,
#                 profile=profile,
#             )
#             messages.success(request, "Officer added successfully!")
#             return redirect('list_officers')

#     categories = Category.objects.all()
#     return render(request, 'add_officer.html', {'categories': categories})


# def list_officers(request):
#     """List all officers with their category details."""
#     officers = Officer.objects.select_related('category').all()
#     return render(request, 'list_officers.html', {'officers': officers})


# def edit_officer(request, officer_id):
#     """Edit officer details (e.g. password)."""
#     officer_instance = get_object_or_404(Officer, id=officer_id)

#     if request.method == 'POST':
#         new_password = request.POST.get('password', '').strip()
#         if new_password:
#             officer_instance.Password = new_password
#             officer_instance.save()
#             messages.success(request, 'Password updated successfully!')
#             return redirect('list_officers')
#         else:
#             messages.error(request, 'Password cannot be empty.')

#     return render(request, 'edit_officer.html', {'officer': officer_instance})


# def delete_officer(request, officer_id):
#     """Delete an officer record."""
#     officer_instance = get_object_or_404(Officer, id=officer_id)
#     officer_instance.delete()
#     messages.success(request, 'Officer deleted successfully!')
#     return redirect('list_officers')
