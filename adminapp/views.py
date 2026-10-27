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


# ==============================================================================
# Officer Management
# ==============================================================================

def add_officer(request):
    """Add a new officer with profile and ID card."""
    if request.method == 'POST':
        fullname = request.POST.get('Fullname', '').strip()
        email = request.POST.get('Email', '').strip()
        password = request.POST.get('Password', '').strip()
        phone = request.POST.get('Phone', '').strip()
        gender = request.POST.get('Gender', '').strip()
        category_id = request.POST.get('category')
        officer_id = request.POST.get('officer_id', '').strip()
        id_card = request.FILES.get('id_card')
        profile = request.FILES.get('profile')

        if not all([fullname, email, password, phone, gender, category_id, officer_id]):
            messages.error(request, "All required fields must be filled.")
        else:
            category = get_object_or_404(Category, id=category_id)
            Officer.objects.create(
                Fullname=fullname,
                Email=email,
                Password=password,
                Phone=phone,
                Gender=gender,
                category=category,
                officer_id=officer_id,
                id_card=id_card,
                profile=profile,
            )
            messages.success(request, f"Officer '{fullname}' registered successfully!")
            return redirect('list_officers')

    categories = Category.objects.all()
    return render(request, 'adminapp/add_officer.html', {'categories': categories})


def list_officers(request):
    """List all officers with their category details."""
    officers = Officer.objects.select_related('category').all().order_by('-id')
    categories = Category.objects.all()
    return render(request, 'adminapp/list_officers.html', {
        'officers': officers,
        'categories': categories,
    })


def edit_officer(request, officer_id):
    """Edit officer status and/or password directly from the list."""
    officer_instance = get_object_or_404(Officer, id=officer_id)

    if request.method == 'POST':
        new_password = request.POST.get('password', '').strip()
        is_active = request.POST.get('is_active', '').strip()
        changed = False

        # Status: only act on a valid submitted value
        if is_active in ('True', 'False'):
            new_status = (is_active == 'True')
            if new_status != officer_instance.is_active:
                officer_instance.is_active = new_status
                state = "activated" if new_status else "deactivated"
                messages.success(request, f"Officer '{officer_instance.Fullname}' {state} successfully!")
                changed = True

        # Password: optional
        if new_password:
            officer_instance.Password = new_password
            messages.success(request, f"Password for {officer_instance.Fullname} updated successfully!")
            changed = True

        if changed:
            officer_instance.save()
        else:
            messages.info(request, "No changes were made.")

    return redirect('list_officers')

def delete_officer(request, officer_id):
    """Delete an officer record."""
    officer_instance = get_object_or_404(Officer, id=officer_id)
    officer_name = officer_instance.Fullname
    officer_instance.delete()
    messages.success(request, f"Officer '{officer_name}' deleted successfully!")
    return redirect('list_officers')

