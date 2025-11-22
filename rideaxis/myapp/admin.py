from django.contrib import admin
from .models import Driver, Ride, Terminal, TerminalAdmin, DriverRating, Seat, RideLocation

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name", "sex", "address", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name", "address")
    list_filter = ("sex", "is_active", "is_staff")

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('driver', 'route', 'departure_time', 'seats_available', 'plate_number')
    search_fields = ('driver__username', 'route', 'terminal', 'plate_number')
    list_filter = ('departure_time',)

@admin.register(Terminal)
class TerminalAdminModel(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone_number', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'address')
    list_filter = ('is_active', 'created_at')

@admin.register(TerminalAdmin)
class TerminalAdminAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'terminal', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'terminal__name')
    list_filter = ('is_active', 'created_at')

@admin.register(DriverRating)
class DriverRatingAdmin(admin.ModelAdmin):
    list_display = ('driver', 'rating', 'created_at')
    search_fields = ('driver__username',)
    list_filter = ('rating', 'created_at')

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('seat_number', 'ride', 'status')
    search_fields = ('seat_number', 'ride__id')
    list_filter = ('status',)

@admin.register(RideLocation)
class RideLocationAdmin(admin.ModelAdmin):
    list_display = ('ride', 'latitude', 'longitude', 'timestamp')
    search_fields = ('ride__id',)
    list_filter = ('timestamp',)