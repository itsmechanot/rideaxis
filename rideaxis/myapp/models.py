from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.utils import timezone

ROUTE_CHOICES = (
    ('NAVAL', 'NAVAL'),
    ('ORMOC', 'ORMOC'),
    ('TACLOBAN', 'TACLOBAN'),
    ('LEYTE', 'LEYTE'),
)

TERMINAL_CHOICES = (
    ('NAVAL', 'Naval Terminal'),
    ('ORMOC', 'Ormoc Terminal'),
    ('TACLOBAN', 'Tacloban Terminal'),
    ('LEYTE', 'Leyte Terminal'),
)

# NEW: Approval status choices
APPROVAL_STATUS = (
    ('pending', 'Pending Approval'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)

class Terminal(models.Model):
    """Model for managing terminals dynamically"""
    name = models.CharField(max_length=100, unique=True, help_text="Full terminal name")
    code = models.CharField(max_length=50, unique=True, help_text="Short code (e.g., NAVAL)")
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Terminal"
        verbose_name_plural = "Terminals"
    
    def __str__(self):
        return self.name


class DriverManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        if not email:
            raise ValueError("The Email must be set")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


class Driver(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    sex = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female')],
        blank=True,
        null=True
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        default='profile_pictures/default.png',
        blank=True, 
        null=True
    )
    
    # CHANGED: From CharField to ForeignKey
    assigned_terminal = models.ForeignKey(
        'Terminal',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='drivers',
        help_text="Terminal this driver wants to be assigned to"
    )

    terminal_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default='pending',
        help_text="Approval status for terminal assignment"
    )
    terminal_rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection (if rejected)"
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = DriverManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username
    
    def is_terminal_approved(self):
        """Check if driver is approved for their terminal"""
        return self.assigned_terminal and self.terminal_status == 'approved'
    
    def get_terminal_status_display_color(self):
        """Return color for status badge"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
        }
        return colors.get(self.terminal_status, '#6c757d')


class TerminalAdmin(models.Model):
    """Custom admin model for managing specific terminals"""
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    
    # CHANGED: From CharField to OneToOneField
    terminal = models.OneToOneField(
        'Terminal',
        on_delete=models.CASCADE,
        related_name='admin',
        null=True,  
        blank=True,  
        help_text="Terminal this admin manages"
    )
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Terminal Administrator"
        verbose_name_plural = "Terminal Administrators"

    def __str__(self):
        return f"{self.username} - {self.terminal.name}"

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    

class DriverRating(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField() 
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('driver', 'ip_address') 

    def __str__(self):
        return f"{self.driver.username} - {self.rating}★"


class Ride(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),      # NEW: Created by admin, not yet activated
        ('waiting', 'Waiting at Terminal'),
        ('departed', 'Departed'),
        ('completed', 'Completed'),
    ]

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rides"
    )
    
    # NEW: Track who created this ride
    created_by_admin = models.ForeignKey(
        'TerminalAdmin',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_rides',
        help_text="Terminal admin who created this schedule"
    )
    
    # NEW: Which driver is this ride assigned to (for scheduled rides)
    assigned_driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_rides",
        null=True,
        blank=True,
        help_text="Driver assigned to this scheduled ride"
    )
    
    terminal = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    start_point = models.CharField(
        max_length=100, 
        choices=ROUTE_CHOICES, 
        default='Naval'
    )
    route = models.CharField(max_length=100, choices=ROUTE_CHOICES)
    departure_time = models.DateTimeField()
    seats_available = models.IntegerField()
    plate_number = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,  # Changed from 10 to 20 to accommodate 'scheduled'
        choices=STATUS_CHOICES, 
        default='scheduled'  # Changed default to 'scheduled'
    )
    
    # NEW: Track when ride was activated by driver
    activated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.route} ({self.driver or self.assigned_driver})"

    def total_seats(self):
        """Returns total seat count."""
        return self.seats.count()
    
    # NEW: Check if ride is admin-created
    def is_admin_created(self):
        return self.created_by_admin is not None
    
    # NEW: Check if ride can be edited by driver
    def can_driver_edit(self):
        """Driver can only edit if they created it (not admin-created)"""
        return not self.is_admin_created()


class Seat(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)
    x = models.IntegerField()
    y = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=[("available", "Available"), ("taken", "Taken")],
        default="available"
    )

    def __str__(self):
        return f"{self.seat_number} ({self.status})"
    
class RideLocation(models.Model):
    """Stores a single point in the location history of a departed ride."""
    ride = models.ForeignKey(
        'Ride', 
        on_delete=models.CASCADE, 
        related_name='locations'
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = "Ride Location Point"
        verbose_name_plural = "Ride Location Points"

    def __str__(self):
        return f"Location for Ride {self.ride.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"