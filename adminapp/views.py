from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from functools import wraps
from .models import tbl_admin, Category, Officer
from django.db.models import Q, Count, Avg
from juspalapp.models import userreg, Complaints, Feedback


# ==============================================================================
# Decorators / Session Guards
# ==============================================================================

def admin_required(view_func):
    """Redirect to login if no active admin session."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_id'):
            messages.warning(request, "Please log in to access the admin portal.")
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper




# ==============================================================================
# Admin Authentication & Dashboard
# ==============================================================================

def admin_login(request):
    """Handles admin login and sets session data."""
    if request.session.get('admin_id'):
        return redirect('admin_index')
    if request.session.get('officer_db_id'):
        return redirect('officer_index')

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


@admin_required
def admin_index(request):
    """Admin dashboard view."""
    officer_count = Officer.objects.count()
    category_count = Category.objects.count()
    user_count = userreg.objects.count()
    context = {
        'officer_count': officer_count,
        'category_count': category_count,
        'user_count': user_count,
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

@admin_required
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


@admin_required
def category_list(request):
    """List all categories / departments."""
    categories = Category.objects.all()
    return render(request, "adminapp/category_list.html", {"categories": categories})


@admin_required
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


@admin_required
def delete_category(request, category_id):
    """Delete a category."""
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, "Category deleted successfully!")
    return redirect("category_list")


# ==============================================================================
# Officer Management
# ==============================================================================

@admin_required
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


@admin_required
def list_officers(request):
    """List all officers with their category details."""
    officers = Officer.objects.select_related('category').all().order_by('-id')
    categories = Category.objects.all()
    return render(request, 'adminapp/list_officers.html', {
        'officers': officers,
        'categories': categories,
    })


@admin_required
def edit_officer(request, officer_id):
    """Change an officer's password from the officers list."""
    officer_instance = get_object_or_404(Officer, id=officer_id)

    if request.method == 'POST':
        new_password = request.POST.get('password', '').strip()

        if new_password:
            officer_instance.Password = new_password
            officer_instance.save(update_fields=['Password'])
            messages.success(request, f"Password for {officer_instance.Fullname} updated successfully!")
        else:
            messages.error(request, "Password cannot be empty.")

    return redirect('list_officers')

@admin_required
def delete_officer(request, officer_id):
    """Delete an officer record."""
    officer_instance = get_object_or_404(Officer, id=officer_id)
    officer_name = officer_instance.Fullname
    officer_instance.delete()
    messages.success(request, f"Officer '{officer_name}' deleted successfully!")
    return redirect('list_officers')



# ==============================================================================
# User Management (registered app users — juspalapp.userreg)
# ==============================================================================

@admin_required
def list_users(request):
    """List all registered app users."""
    users = userreg.objects.all().order_by('-id')
    return render(request, 'adminapp/list_users.html', {'users': users})


@admin_required
def delete_user(request, user_id):
    """Delete a registered user (POST only, CSRF-protected)."""
    if request.method != 'POST':
        return redirect('list_users')
    user_instance = get_object_or_404(userreg, id=user_id)
    user_name = user_instance.fullname
    if user_instance.profile:
        user_instance.profile.delete(save=False)
    user_instance.delete()
    messages.success(request, f"User '{user_name}' deleted successfully!")
    return redirect('list_users')


# ==============================================================================
# Complaint Management
# ==============================================================================

@admin_required
def complaint_list(request):
    """Grid of all complaints with search and filters (type / status / priority / department)."""
    complaints = Complaints.objects.select_related('category', 'assigned_officer', 'user')

    # ── Filters from the query string ─────────────────────────────────────────
    q = request.GET.get('q', '').strip()
    filters = {
        'type': request.GET.get('type', ''),
        'status': request.GET.get('status', ''),
        'priority': request.GET.get('priority', ''),
        'category': request.GET.get('category', ''),
        'assigned': request.GET.get('assigned', ''),
    }
    if q:
        complaints = complaints.filter(
            Q(complaint_id__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q)
            | Q(phone__icontains=q) | Q(city__icontains=q) | Q(description__icontains=q)
        )
    if filters['type']:
        complaints = complaints.filter(complaint_type=filters['type'])
    if filters['status']:
        complaints = complaints.filter(status_code=filters['status'])
    if filters['priority']:
        complaints = complaints.filter(priority=filters['priority'])
    if filters['category'].isdigit():
        complaints = complaints.filter(category_id=filters['category'])
    if filters['assigned'] == 'yes':
        complaints = complaints.filter(assigned_officer__isnull=False)
    elif filters['assigned'] == 'no':
        complaints = complaints.filter(assigned_officer__isnull=True)

    # ── Headline counts (over all complaints, not the filtered set) ───────────
    stats = Complaints.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status_code=Complaints.Status.PENDING)),
        in_progress=Count('id', filter=Q(status_code=Complaints.Status.IN_PROGRESS)),
        resolved=Count('id', filter=Q(status_code=Complaints.Status.RESOLVED)),
        unassigned=Count('id', filter=Q(assigned_officer__isnull=True)),
    )

    return render(request, 'adminapp/complaint_list.html', {
        'complaints': complaints,
        'stats': stats,
        'q': q,
        'filters': filters,
        'is_filtered': bool(q or any(filters.values())),
        'categories': Category.objects.all().order_by('name'),
        'type_choices': Complaints.ComplaintType.choices,
        'status_choices': Complaints.Status.choices,
        'priority_choices': Complaints.Priority.choices,
    })


@admin_required
def complaint_detail(request, complaint_pk):
    """Full complaint details, with the assign-officer / status panel."""
    complaint = get_object_or_404(
        Complaints.objects.select_related('category', 'assigned_officer', 'user'),
        pk=complaint_pk,
    )
    # Officers from the complaint's own department are listed first as "recommended"
    officers = Officer.objects.select_related('category').order_by('Fullname')
    recommended_officers = [o for o in officers if o.category_id == complaint.category_id]
    other_officers = [o for o in officers if o.category_id != complaint.category_id]

    # Bounding box (~1 km around the pin) for the embedded OpenStreetMap
    map_bbox = None
    if complaint.latitude is not None and complaint.longitude is not None:
        lat, lng, d = float(complaint.latitude), float(complaint.longitude), 0.01
        map_bbox = f"{lng - d:.6f},{lat - d:.6f},{lng + d:.6f},{lat + d:.6f}"

    return render(request, 'adminapp/complaint_detail.html', {
        'complaint': complaint,
        'map_bbox': map_bbox,
        'recommended_officers': recommended_officers,
        'other_officers': other_officers,
        'status_choices': Complaints.Status.choices,
    })


@admin_required
def assign_complaint_officer(request, complaint_pk):
    """POST: assign / unassign an officer and update the status and remarks."""
    complaint = get_object_or_404(Complaints, pk=complaint_pk)
    if request.method != 'POST':
        return redirect('complaint_detail', complaint_pk=complaint.pk)

    officer_id = request.POST.get('officer', '').strip()
    new_status = request.POST.get('status_code', '').strip()
    remarks = request.POST.get('remarks', '').strip()

    # Officer ('' = unassign)
    if officer_id:
        officer = Officer.objects.filter(pk=officer_id).first() if officer_id.isdigit() else None
        if not officer:
            messages.error(request, "Selected officer was not found.")
            return redirect('complaint_detail', complaint_pk=complaint.pk)
        complaint.assigned_officer = officer
    else:
        complaint.assigned_officer = None

    # Status (ignore anything that isn't a valid choice)
    if new_status in Complaints.Status.values:
        complaint.status_code = new_status

    complaint.remarks = remarks or None
    complaint.save(update_fields=['assigned_officer', 'status_code', 'remarks'])

    if complaint.assigned_officer:
        messages.success(
            request,
            f"Complaint {complaint.complaint_id} assigned to {complaint.assigned_officer.Fullname} "
            f"({complaint.status_code}).",
        )
    else:
        messages.success(request, f"Complaint {complaint.complaint_id} updated ({complaint.status_code}, unassigned).")
    return redirect('complaint_detail', complaint_pk=complaint.pk)


# ==============================================================================
# Admin Profile
# ==============================================================================

@admin_required
def admin_profile(request):
    """
    View and update the logged-in admin's own profile.
    Two forms post here, told apart by the hidden 'action' field:
      action=profile  → update name and email
      action=password → change password (current password required)
    Role and account status are not editable here.
    """
    admin = tbl_admin.objects.filter(pk=request.session.get('admin_id'), is_active=True).first()
    if not admin:
        request.session.flush()
        messages.error(request, "Your admin account was not found. Please log in again.")
        return redirect('admin_login')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'profile':
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            if not name or not email:
                messages.error(request, "Name and email are required.")
            elif tbl_admin.objects.filter(email__iexact=email).exclude(pk=admin.pk).exists():
                messages.error(request, "This email is already used by another admin.")
            else:
                admin.name = name
                admin.email = email
                admin.save(update_fields=['name', 'email', 'updated_at'])
                request.session['admin_name'] = admin.name  # keep the navbar in sync
                messages.success(request, "Profile updated successfully!")
                return redirect('admin_profile')

        elif action == 'password':
            current = request.POST.get('current_password', '')
            new = request.POST.get('new_password', '').strip()
            confirm = request.POST.get('confirm_password', '').strip()
            if current != admin.password:
                messages.error(request, "Current password is incorrect.")
            elif len(new) < 6:
                messages.error(request, "New password must be at least 6 characters.")
            elif new != confirm:
                messages.error(request, "New password and confirmation do not match.")
            elif new == admin.password:
                messages.error(request, "New password must be different from the current one.")
            else:
                admin.password = new
                admin.save(update_fields=['password', 'updated_at'])
                messages.success(request, "Password changed successfully!")
                return redirect('admin_profile')

    return render(request, 'adminapp/admin_profile.html', {'admin': admin})


# ==============================================================================
# Feedback (submitted by app users — juspalapp.Feedback)
# ==============================================================================

FEEDBACK_SORTS = {
    'newest': ('-created_at', '-id'),
    'oldest': ('created_at', 'id'),
    'highest': ('-rate', '-created_at'),
    'lowest': ('rate', '-created_at'),
}


@admin_required
def feedback_list(request):
    """All user feedback with rating summary, search, star filter and sorting."""
    all_feedback = Feedback.objects.all()

    # ── Summary over all feedback (not affected by filters) ──────────────────
    total = all_feedback.count()
    average = all_feedback.aggregate(avg=Avg('rate'))['avg'] or 0
    counts = dict(all_feedback.values_list('rate').annotate(n=Count('id')))
    distribution = [
        {'stars': s, 'count': counts.get(s, 0),
         'percent': round(counts.get(s, 0) * 100 / total) if total else 0}
        for s in range(5, 0, -1)
    ]

    # ── Filters ──────────────────────────────────────────────────────────────
    q = request.GET.get('q', '').strip()
    rating = request.GET.get('rating', '')
    sort = request.GET.get('sort', 'newest')
    if sort not in FEEDBACK_SORTS:
        sort = 'newest'

    feedbacks = all_feedback.select_related('user')
    if q:
        feedbacks = feedbacks.filter(
            Q(feedback__icontains=q) | Q(user__fullname__icontains=q) | Q(user__email__icontains=q)
        )
    if rating in {'1', '2', '3', '4', '5'}:
        feedbacks = feedbacks.filter(rate=int(rating))
    feedbacks = feedbacks.order_by(*FEEDBACK_SORTS[sort])

    return render(request, 'adminapp/feedback_list.html', {
        'feedbacks': feedbacks,
        'total': total,
        'average': round(average, 1),
        'average_stars': round(average),
        'positive': sum(d['count'] for d in distribution if d['stars'] >= 4),
        'negative': sum(d['count'] for d in distribution if d['stars'] <= 2),
        'distribution': distribution,
        'q': q,
        'rating': rating,
        'sort': sort,
        'is_filtered': bool(q or rating),
        'star_range': range(1, 6),
    })
