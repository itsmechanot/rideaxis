from datetime import timezone
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import DriverRegisterForm, DriverProfileForm, RideForm, RideScheduleForm
from .models import TERMINAL_CHOICES, Driver, Ride, Seat, DriverRating, RideLocation, TerminalAdmin
from django.views.decorators.http import require_POST
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F
from django.db.models import Avg, Count
from django.db.models.functions import ExtractMonth, ExtractYear
from django.views.decorators.http import require_http_methods


def index(request):
    rides_qs = (
        Ride.objects.filter(status__in=['waiting', 'departed'])
        .select_related('driver')
        .prefetch_related('seats')
    )

    rides = list(rides_qs)

    for ride in rides:
        ride.seat_classes = ride.seats.all()

    if request.user.is_authenticated:
        active_ride = Ride.objects.filter(driver=request.user, status='active').first()
        if active_ride and active_ride in rides:
            rides.remove(active_ride)
            rides.insert(0, active_ride)

    routes = rides_qs.values_list('route', flat=True).distinct()

    driver_ratings = (
        DriverRating.objects.values('driver')
        .annotate(avg_rating=Avg('rating'))
    )

    rating_dict = {r['driver']: round(r['avg_rating'] or 0, 1) for r in driver_ratings}

    for ride in rides:
        ride.driver_avg_rating = rating_dict.get(ride.driver.id, 0)

    return render(request, "myapp/index.html", {
        "rides": rides,
        "routes": routes
    })


def driver_detail(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)

    current_ride = (
        Ride.objects.filter(driver=driver, status__in=['waiting', 'departed'])
        .select_related('driver')
        .prefetch_related('seats')
        .first()
    )

    latest_location = None
    if current_ride and current_ride.status == 'departed':
        latest_location = current_ride.locations.order_by('-timestamp').first()

    past_rides = (
        Ride.objects.filter(driver=driver, status='completed')
        .select_related('driver')
        .order_by('-departure_time')[:3]
    )

    avg_rating = DriverRating.objects.filter(driver=driver).aggregate(Avg("rating"))["rating__avg"] or 0
    ip = get_client_ip(request)
    already_rated = DriverRating.objects.filter(driver=driver, ip_address=ip).exists()

    if current_ride:
        current_ride.seat_classes = current_ride.seats.all()

    return render(request, "myapp/driver_detail.html", {
        "driver": driver,
        "current_ride": current_ride,
        "past_rides": past_rides,
        "latest_location": latest_location,
        "average_rating": round(avg_rating, 2),
        "already_rated": already_rated,
    })


def get_client_ip(request):
    """Helper to get user’s real IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@csrf_exempt
def rate_driver(request, driver_id):
    if request.method == "POST":
        rating = int(request.POST.get("rating", 0))
        ip = get_client_ip(request)

        driver = Driver.objects.get(id=driver_id)
        existing_rating = DriverRating.objects.filter(driver=driver, ip_address=ip).first()

        if existing_rating:
            return JsonResponse({
                "success": False,
                "error": "You already rated this driver."
            })

        DriverRating.objects.create(driver=driver, rating=rating, ip_address=ip)

        avg_rating = DriverRating.objects.filter(driver=driver).aggregate(Avg("rating"))["rating__avg"]

        return JsonResponse({
            "success": True,
            "message": "Thanks for rating!",
            "average_rating": round(avg_rating or 0, 2)
        })

    return JsonResponse({"success": False, "error": "Invalid request"})


def login_view(request):
    """
    Unified login for both Drivers and Terminal Admins.
    Automatically redirects based on account type.
    """
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # First, try to authenticate as a Driver (using Django auth)
        driver = authenticate(request, username=username, password=password)
        
        if driver is not None:
            # It's a driver account
            auth_login(request, driver)
            messages.success(request, "Login successful! Welcome back.")
            return redirect('profile')  # Redirect to driver profile
        
        # If not a driver, check if it's a Terminal Admin
        try:
            admin = TerminalAdmin.objects.get(username=username, is_active=True)
            if admin.check_password(password):
                # It's a terminal admin account
                # Store admin info in session
                request.session['terminal_admin_id'] = admin.id
                request.session['terminal_admin_username'] = admin.username
                request.session['terminal_admin_terminal_id'] = admin.terminal.id
                request.session['terminal_admin_terminal_name'] = admin.terminal.name
                
                # Update last login
                admin.last_login = timezone.now()
                admin.save()
                
                messages.success(request, f'Welcome, {admin.first_name}!')
                return redirect('terminal_admin_dashboard')
            else:
                messages.error(request, "Invalid username or password")
                return render(request, "myapp/login.html", {'show_register': False})
        except TerminalAdmin.DoesNotExist:
            # Neither driver nor admin found
            messages.error(request, "Invalid username or password")
            return render(request, "myapp/login.html", {'show_register': False})
    else:
        return render(request, "myapp/login.html", {'show_register': False})


def logout_view(request):
    """
    Logout for both Drivers and Terminal Admins
    """
    if 'terminal_admin_id' in request.session:
        request.session.flush()
        messages.success(request, 'You have been logged out successfully.')
    else:
        from django.contrib.auth import logout
        logout(request)
        list(messages.get_messages(request))
    
    return redirect('login')


def register(request):
    if request.method == "POST":
        form = DriverRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully!")
            return render(request, 'myapp/login.html', {'show_register': True})
        else:
            error_text = " ".join([str(e) for errors in form.errors.values() for e in errors])
            messages.error(request, error_text)
            return render(request, 'myapp/login.html', {'driver_form': form, 'show_register': True})
    else:
        form = DriverRegisterForm()
        return render(request, 'myapp/login.html', {'driver_form': form, 'show_register': True})


@login_required
def profile(request):
    driver = request.user
    
    # Get the ride assigned to this driver by admin (scheduled status)
    assigned_ride = Ride.objects.filter(
        assigned_driver=driver,
        status='scheduled'
    ).first()
    
    # Get active ride (waiting or departed) - this is the one they're currently managing
    active_ride = Ride.objects.filter(
        driver=driver, 
        status__in=['waiting', 'departed'] 
    ).first()
    
    # Get past completed rides
    past_rides = Ride.objects.filter(
        driver=driver, 
        status='completed'
    ).order_by('-departure_time')[:3]
    
    # Get ALL scheduled rides from driver's terminal (for viewing)
    all_scheduled_rides = []
    if driver.assigned_terminal and driver.is_terminal_approved():
        all_scheduled_rides = Ride.objects.filter(
            start_point=driver.assigned_terminal.code,
            status='scheduled'
        ).select_related('assigned_driver').order_by('departure_time')

    form = DriverProfileForm(instance=driver)
    
    # For assigned ride, create a read-only form
    if assigned_ride:
        ride_form = RideForm(instance=assigned_ride)
        # Disable all fields since it's admin-created
        for field in ride_form.fields:
            ride_form.fields[field].disabled = True
        seat_classes = assigned_ride.seats.all()
        seat_count = seat_classes.count()
    elif active_ride:
        # For active rides created by driver (old system)
        ride_form = RideForm(instance=active_ride)
        if active_ride.is_admin_created():
            # If it's admin-created but activated, make read-only
            for field in ride_form.fields:
                ride_form.fields[field].disabled = True
        seat_classes = active_ride.seats.all()
        seat_count = seat_classes.count()
    else:
        ride_form = RideForm()
        seat_classes = []
        seat_count = 0

    avg_rating = DriverRating.objects.filter(driver=driver).aggregate(Avg("rating"))["rating__avg"]
    avg_rating = round(avg_rating or 0, 2)

    if request.method == "POST":
        if "save_profile" in request.POST:
            form = DriverProfileForm(request.POST, request.FILES, instance=driver)
            if form.is_valid():
                form.save()
                
                if 'assigned_terminal' in form.changed_data:
                    new_terminal = form.cleaned_data.get('assigned_terminal')
                    if new_terminal:
                        messages.success(
                            request, 
                            f"Profile updated! Your request to join {new_terminal.name} "
                            f"has been submitted for approval."
                        )
                    else:
                        messages.success(request, "Profile updated successfully!")
                else:
                    messages.success(request, "Profile updated successfully!")
                return redirect("profile")

        elif "activate_ride" in request.POST:
            # Handle ride activation
            if assigned_ride:
                # Update the ride: change status and set driver
                assigned_ride.status = 'waiting'
                assigned_ride.driver = driver  # Set the driver field
                assigned_ride.activated_at = timezone.now()
                assigned_ride.seats_available = assigned_ride.seats.filter(status='available').count()
                assigned_ride.save()
                
                messages.success(request, "Ride activated successfully! It's now visible to passengers.")
                return redirect("profile")
            else:
                messages.error(request, "No assigned ride to activate.")
                return redirect("profile")

        elif "create_ride" in request.POST:
            # Only allow if no admin-created ride assigned
            if assigned_ride:
                messages.error(
                    request,
                    "You have an assigned schedule from your terminal admin. Please activate it instead."
                )
                return redirect("profile")
            
            # CHECK: Only allow ride creation if terminal is approved
            if not driver.is_terminal_approved():
                messages.error(
                    request, 
                    "You cannot create rides until your terminal registration is approved."
                )
                return redirect("profile")
            
            # CHECK: If this is an admin-created ride, don't allow editing
            if active_ride and active_ride.is_admin_created():
                messages.error(
                    request,
                    "This ride was scheduled by your terminal admin and cannot be modified."
                )
                return redirect("profile")
            
            # Only process form for driver-created rides
            ride_form = RideForm(request.POST, instance=active_ride)
            if ride_form.is_valid():
                ride = ride_form.save(commit=False)
                ride.driver = request.user
                ride.status = 'waiting'
                ride.start_point = driver.assigned_terminal.code
                ride.save()

                if not ride.seats.exists():
                    create_default_seats(ride)

                ride.seats_available = ride.seats.filter(status='available').count()
                ride.save()

                messages.success(
                    request,
                    "Ride updated successfully!" if active_ride else "Ride created successfully!"
                )
                return redirect("profile")

    # Add terminal status info for template
    terminal_info = {
        'assigned_terminal': driver.assigned_terminal,
        'terminal_name': driver.assigned_terminal.name if driver.assigned_terminal else 'None',
        'status': driver.terminal_status,
        'status_display': driver.get_terminal_status_display(),
        'status_color': driver.get_terminal_status_display_color(),
        'rejection_reason': driver.terminal_rejection_reason,
        'is_approved': driver.is_terminal_approved(),
    }

    return render(request, "myapp/profile.html", {
        "driver": driver,
        "form": form,
        "ride_form": ride_form,
        "assigned_ride": assigned_ride,
        "active_ride": active_ride,
        "seat_classes": seat_classes,
        "seat_count": seat_count,
        "past_rides": past_rides,
        "all_scheduled_rides": all_scheduled_rides,
        "average_rating": avg_rating,
        "terminal_info": terminal_info,
    })

    

def create_default_seats(ride):
    from .models import Seat
    positions = [
        # driver + front passenger
        (40, 40), (140, 40),
        # Row 1
        (20, 110), (80, 110), (140, 110),
        # Row 2
        (20, 170), (80, 170), (140, 170),
        # Row 3
        (20, 230), (80, 230), (140, 230),
        # Row 4
        (15, 290), (64, 290), (115, 290), (163, 290),
    ]

    for i, (x, y) in enumerate(positions, start=1):
        Seat.objects.create(
            ride=ride,
            seat_number=f"S{i}",
            x=x,
            y=y,
            status="taken" if i == 1 else "available"  
        )

@login_required
def complete_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user)
    
    # Check if the ride is in the correct status to be completed
    if ride.status == 'departed':
        ride.status = 'completed'
        ride.save()
        messages.success(request, f"Ride {ride.id} completed successfully! It has been archived.")
    else:
        messages.error(request, f"Ride {ride.id} must be 'departed' before being marked as completed.")
        
    return redirect('profile')

def delete_profile(request):
    if request.method == "POST":
        request.user.delete()
        messages.success(request, "Your profile has been deleted.")
        return redirect("index")


@login_required
def create_ride(request):
    if request.method == 'POST':
        form = RideForm(request.POST)
        if form.is_valid():
            ride = form.save(commit=False)
            ride.driver = request.user  
            ride.save()
            return redirect('profile') 
    else:
        form = RideForm()
    return render(request, 'profile.html', {'form': form})


@login_required
def edit_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user)

    if request.method == "POST":
        form = RideForm(request.POST, instance=ride)
        if form.is_valid():
            form.save()
            messages.success(request, "Ride updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RideForm(instance=ride)

    return render(request, "myapp/edit_ride.html", {"form": form, "ride": ride})


@login_required
def depart_ride(request, ride_id):
    ride = get_object_or_404(Ride, id=ride_id, driver=request.user)
    ride.status = 'departed'
    ride.save()
    messages.success(request, "Ride departed successfully!")
    return redirect('profile')


@csrf_exempt 
@login_required
def update_seat_status(request):
    if request.method == "POST":
        data = json.loads(request.body)
        seat_id = data.get("seat_id")
        new_status = data.get("status")

        try:
            seat = Seat.objects.get(id=seat_id)
            seat.status = new_status
            seat.save()

            ride = seat.ride
            available_count = ride.seats.filter(status='available').count()
            ride.seats_available = available_count
            ride.save()

            return JsonResponse({
                "success": True,
                "available_count": available_count
            })

        except Seat.DoesNotExist:
            return JsonResponse({"success": False, "error": "Seat not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


def get_seat_classes(ride):
    if not ride:
        return []

    total_seats = 14
    seat_classes = []

    positions = [
        # driver + front passenger
        (40, 20), (140, 20),
        # Row 1 (3 seats)
        (20, 80), (80, 80), (140, 80),
        # Row 2 (3 seats)
        (20, 140), (80, 140), (140, 140),
        # Row 3 (3 seats)
        (20, 200), (80, 200), (140, 200),
        # Row 4 (4 seats)
        (10, 260), (60, 260), (110, 260), (160, 260),
    ]

    # Load seat_map if available; else default by taken count
    seat_map = getattr(ride, "seat_map", None)
    if not seat_map:
        seat_map = {str(i): "taken" if i < ride.seats_taken else "available" for i in range(total_seats)}

    for i, pos in enumerate(positions):
        status = seat_map.get(str(i), "available")
        if i == 0:  # driver seat always taken
            status = "taken"
        seat_classes.append({'x': pos[0], 'y': pos[1], 'status': status})

    return seat_classes


@login_required
@require_POST
def save_location(request):
    # Ensure the request body is valid JSON
    try:
        data = json.loads(request.body)
        ride_id = data.get('ride_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    
    # Basic validation
    if not all([ride_id, latitude, longitude]):
        return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
    
    try:
        # 1. Check if the ride exists and belongs to the authenticated driver
        ride = Ride.objects.get(id=ride_id, driver=request.user)
        
        # 2. Crucially, only save location if the ride is in the 'departed' status
        if ride.status != 'departed':
            return JsonResponse({'status': 'error', 'message': 'Ride is not currently departed for tracking.'}, status=440)

        # 3. Create the location point
        RideLocation.objects.create(
            ride=ride,
            latitude=latitude,
            longitude=longitude
        )
        return JsonResponse({'status': 'success', 'message': 'Location saved.'})

    except Ride.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Ride not found or unauthorized.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@login_required
def terminal_schedules(request):
    driver = request.user
    
    # Get ALL scheduled rides from driver's terminal
    all_scheduled_rides = []
    terminal_name = 'None'
    if driver.assigned_terminal and driver.is_terminal_approved():
        all_scheduled_rides = Ride.objects.filter(
            start_point=driver.assigned_terminal.code,
            status='scheduled'
        ).select_related('assigned_driver').order_by('departure_time')
        terminal_name = driver.assigned_terminal.name
    
    return render(request, "myapp/terminal_schedules.html", {
        "driver": driver,
        "all_scheduled_rides": all_scheduled_rides,
        "terminal_name": terminal_name,
    })

@login_required 
def ride_history(request):
    driver = request.user
    
    # 1. Fetch ALL completed rides for the list
    all_past_rides = (
        Ride.objects.filter(driver=driver, status='completed')
        .order_by('-departure_time')
    )
    
    # 2. CRITICAL FIX: Calculate monthly ride counts using ExtractYear and ExtractMonth
    # This approach is much more compatible across different databases (like SQLite)
    monthly_rides_qs = ( 
        Ride.objects.filter(driver=driver, status='completed')
        .annotate(
            year=ExtractYear('departure_time'),
            month=ExtractMonth('departure_time')
        )
        .values('year', 'month')
        .annotate(count=Count('id'))
        .order_by('year', 'month')
    )
    
    # 3. Explicitly build the chart data structure using the extracted fields
    months = []
    counts = []
    
    # Simple map of month number to name (for display)
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }

    for item in monthly_rides_qs:
        # Create the chart label (e.g., "Jan 2024")
        label = f"{month_names.get(item['month'], 'Unknown')} {item['year']}"
        months.append(label)
        
        # Ensure the count is an integer
        counts.append(item['count']) 

    # Final structure for safe JSON transfer
    chart_data = {
        'months': months, 
        'counts': counts,
    }
    
    return render(request, "myapp/ride_history.html", {
        "all_past_rides": all_past_rides,
        "chart_data": chart_data,
    })

def terminal_admin_required(view_func):
    """Decorator to check if terminal admin is logged in"""
    def wrapper(request, *args, **kwargs):
        if 'terminal_admin_id' not in request.session:
            messages.warning(request, 'Please login to access the admin panel.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# TERMINAL ADMIN VIEWS
# ============================================

@terminal_admin_required
def terminal_admin_dashboard(request):
    import json
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    terminal = admin.terminal
    
    # Statistics - Updated to only count APPROVED drivers
    total_drivers = Driver.objects.filter(
        assigned_terminal=terminal,
        terminal_status='approved'
    ).count()
    
    pending_drivers_count = Driver.objects.filter(
        assigned_terminal=terminal,
        terminal_status='pending'
    ).count()
    
    # UPDATED: Use terminal.code instead of terminal object
    total_rides = Ride.objects.filter(start_point=terminal.code).count()
    active_rides = Ride.objects.filter(start_point=terminal.code, status='waiting').count()
    completed_rides = Ride.objects.filter(start_point=terminal.code, status='completed').count()
    
    # NEW: Count scheduled rides
    scheduled_rides_count = Ride.objects.filter(
        start_point=terminal.code, 
        status='scheduled'
    ).count()
    
    recent_rides = Ride.objects.filter(start_point=terminal.code).select_related('driver').order_by('-departure_time')[:10]
    all_rides = Ride.objects.filter(start_point=terminal.code).select_related('driver').order_by('-departure_time')
    
    # NEW: Get scheduled rides for display
    scheduled_rides = Ride.objects.filter(
        start_point=terminal.code,
        status='scheduled'
    ).select_related('assigned_driver', 'created_by_admin').order_by('departure_time')
    
    # Get APPROVED drivers only
    drivers = Driver.objects.filter(
        assigned_terminal=terminal,
        terminal_status='approved'
    )
    
    drivers_data = []
    drivers_json = []
    for driver in drivers:
        ride_count = driver.rides.filter(start_point=terminal.code).count()
        avg_rating = driver.ratings.aggregate(Avg('rating'))['rating__avg'] or 0
        
        driver_dict = {
            'driver': driver,
            'ride_count': ride_count,
            'avg_rating': avg_rating,
        }
        drivers_data.append(driver_dict)
        
        drivers_json.append({
            'id': driver.id,
            'username': driver.username,
            'email': driver.email,
            'first_name': driver.first_name or '',
            'last_name': driver.last_name or '',
            'address': driver.address or '',
            'sex': driver.sex or '',
            'profile_picture': driver.profile_picture.url if driver.profile_picture else '',
            'is_active': driver.is_active,
            'ride_count': ride_count,
            'avg_rating': float(avg_rating),
        })
    
    # Get pending drivers for the Pending tab
    pending_drivers = Driver.objects.filter(
        assigned_terminal=terminal,
        terminal_status='pending'
    ).order_by('-date_joined')
    
    # NEW: Create the schedule form
    schedule_form = RideScheduleForm(terminal)
    
    context = {
        'admin': admin,
        'terminal': terminal,
        'stats': {
            'total_drivers': total_drivers,
            'pending_drivers': pending_drivers_count,
            'total_rides': total_rides,
            'active_rides': active_rides,
            'completed_rides': completed_rides,
            'scheduled_rides': scheduled_rides_count,  # NEW
        },
        'recent_rides': recent_rides,
        'all_rides': all_rides,
        'scheduled_rides': scheduled_rides,  # NEW
        'drivers_data': drivers_data,
        'drivers_json': json.dumps(drivers_json),
        'pending_drivers': pending_drivers,
        'schedule_form': schedule_form,  # NEW: Pass form to template
    }
    
    return render(request, 'terminal_admin/dashboard.html', context)


@terminal_admin_required
def terminal_admin_drivers(request):
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    terminal = admin.terminal
    
    # Get drivers who have created rides from this terminal
    drivers = Driver.objects.filter(rides__start_point=terminal).distinct()
    
    # Add ride count and average rating for each driver
    drivers_data = []
    for driver in drivers:
        ride_count = driver.rides.filter(start_point=terminal).count()
        avg_rating = driver.ratings.aggregate(Avg('rating'))['rating__avg']
        drivers_data.append({
            'driver': driver,
            'ride_count': ride_count,
            'avg_rating': avg_rating or 0,
        })
    
    context = {
        'admin': admin,
        'drivers_data': drivers_data,
    }
    
    return redirect('terminal_admin_dashboard')


@terminal_admin_required
def terminal_admin_rides(request):
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    terminal = admin.terminal
    
    # Filter options
    status_filter = request.GET.get('status', 'all')
    
    # Get rides from this terminal
    rides = Ride.objects.filter(start_point=terminal).select_related('driver').order_by('-departure_time')
    
    if status_filter != 'all':
        rides = rides.filter(status=status_filter)
    
    context = {
        'admin': admin,
        'rides': rides,
        'status_filter': status_filter,
    }
    
    return render(request, 'terminal_admin/rides.html', context)


@terminal_admin_required
@require_http_methods(["POST"])
def terminal_admin_update_ride_status(request, ride_id):
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    
    ride = get_object_or_404(Ride, id=ride_id, start_point=admin.terminal)
    new_status = request.POST.get('status')
    
    if new_status in ['waiting', 'departed', 'completed']:
        ride.status = new_status
        ride.save()
        messages.success(request, f'Ride status updated to {ride.get_status_display()}.')
    else:
        messages.error(request, 'Invalid status.')
    
    return redirect('terminal_admin_rides')


@terminal_admin_required
@require_http_methods(["POST"])
def terminal_admin_delete_ride(request, ride_id):
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    
    ride = get_object_or_404(Ride, id=ride_id, start_point=admin.terminal)
    ride.delete()
    messages.success(request, 'Ride deleted successfully.')
    
    return redirect('terminal_admin_rides')


@terminal_admin_required
def terminal_admin_driver_detail(request, driver_id):
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    terminal = admin.terminal
    
    driver = get_object_or_404(Driver, id=driver_id)
    
    # Get driver's rides from this terminal
    driver_rides = Ride.objects.filter(driver=driver, start_point=terminal).order_by('-departure_time')
    
    # Get driver ratings
    ratings = driver.ratings.all().order_by('-created_at')
    avg_rating = driver.ratings.aggregate(Avg('rating'))['rating__avg']
    
    context = {
        'admin': admin,
        'driver': driver,
        'driver_rides': driver_rides,
        'ratings': ratings,
        'avg_rating': avg_rating or 0,
    }
    
    return render(request, 'terminal_admin/driver_detail.html', context)


@terminal_admin_required
@require_http_methods(["POST"])
def terminal_admin_toggle_driver(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    driver.is_active = not driver.is_active
    driver.save()
    
    status = "activated" if driver.is_active else "deactivated"
    messages.success(request, f'Driver {driver.username} has been {status}.')
    
    return redirect('terminal_admin_drivers')


@terminal_admin_required
def terminal_admin_pending_drivers(request):
    """View pending driver registrations for this terminal"""
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    terminal = admin.terminal

    pending_drivers = Driver.objects.filter(
        assigned_terminal=terminal,
        terminal_status='pending'
    ).order_by('-date_joined')
    
    context = {
        'admin': admin,
        'pending_drivers': pending_drivers,
        'pending_count': pending_drivers.count(),
    }
    
    return render(request, 'terminal_admin/pending_drivers.html', context)


# ============================================
# NEW: Terminal Admin - Approve driver
# ============================================
@terminal_admin_required
@require_http_methods(["POST"])
def terminal_admin_approve_driver(request, driver_id):
    """Approve a driver's terminal registration"""
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    
    driver = get_object_or_404(
        Driver, 
        id=driver_id, 
        assigned_terminal=admin.terminal,
        terminal_status='pending'
    )
    
    driver.terminal_status = 'approved'
    driver.terminal_rejection_reason = None
    driver.save()
    
    messages.success(request, f'Driver {driver.username} has been approved!')
    return redirect('terminal_admin_pending_drivers')


# ============================================
# NEW: Terminal Admin - Reject driver
# ============================================
@terminal_admin_required
@require_http_methods(["POST"])
def terminal_admin_reject_driver(request, driver_id):
    """Reject a driver's terminal registration"""
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    
    driver = get_object_or_404(
        Driver, 
        id=driver_id, 
        assigned_terminal=admin.terminal,
        terminal_status='pending'
    )
    
    reason = request.POST.get('rejection_reason', 'No reason provided')
    
    driver.terminal_status = 'rejected'
    driver.terminal_rejection_reason = reason
    driver.save()
    
    messages.success(request, f'Driver {driver.username} has been rejected.')
    return redirect('terminal_admin_pending_drivers')


@terminal_admin_required
@require_http_methods(["GET", "POST"])
def terminal_admin_create_schedule(request):
    """
    Create a new ride schedule and assign it to a driver
    """
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    terminal = admin.terminal
    
    if request.method == 'POST':
        form = RideScheduleForm(terminal, request.POST)
        
        if form.is_valid():
            ride = form.save(commit=False)
            
            # Set admin-controlled fields
            ride.created_by_admin = admin
            ride.terminal = terminal.name
            ride.location = terminal.address or terminal.name
            ride.start_point = terminal.code
            ride.status = 'scheduled'
            ride.driver = form.cleaned_data['assigned_driver']  # Set driver
            ride.seats_available = 0  # Will be set when driver activates
            
            ride.save()
            
            # Create default seats for the ride
            create_default_seats(ride)
            
            messages.success(
                request, 
                f'Ride schedule created and assigned to {ride.assigned_driver.get_full_name() or ride.assigned_driver.username}!'
            )
            return redirect('terminal_admin_dashboard')
        else:
            messages.error(request, 'Please fix the errors in the form.')
    else:
        form = RideScheduleForm(terminal)
    
    context = {
        'admin': admin,
        'form': form,
    }
    
    return render(request, 'terminal_admin/create_schedule.html', context)


@terminal_admin_required
@require_http_methods(["POST"])
def terminal_admin_create_schedule_ajax(request):
    """
    Handle schedule creation from modal via AJAX
    """
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    terminal = admin.terminal
    
    form = RideScheduleForm(terminal, request.POST)
    
    if form.is_valid():
        ride = form.save(commit=False)
        
        # Set admin-controlled fields
        ride.created_by_admin = admin
        ride.terminal = terminal.name
        ride.location = terminal.address or terminal.name
        ride.start_point = terminal.code
        ride.status = 'scheduled'
        ride.driver = form.cleaned_data['assigned_driver']
        ride.seats_available = 0
        
        ride.save()
        
        # Create default seats
        create_default_seats(ride)
        
        return JsonResponse({
            'success': True,
            'message': f'Schedule created and assigned to {ride.assigned_driver.first_name or ride.assigned_driver.username}!'
        })
    else:
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({
            'success': False,
            'errors': errors
        })
    
@terminal_admin_required
@require_http_methods(["POST"])
def terminal_admin_delete_schedule(request, ride_id):
    """Delete a scheduled ride (only if not yet activated)"""
    admin_id = request.session.get('terminal_admin_id')
    admin = get_object_or_404(TerminalAdmin, id=admin_id)
    
    ride = get_object_or_404(
        Ride, 
        id=ride_id, 
        start_point=admin.terminal.code,
        status='scheduled'  # Can only delete if still scheduled
    )
    
    ride.delete()
    messages.success(request, 'Schedule deleted successfully.')
    
    return redirect('terminal_admin_dashboard')