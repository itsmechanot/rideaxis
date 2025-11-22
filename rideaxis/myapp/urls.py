from django.urls import path
from . import views
from .views import create_ride, Ride
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.index, name="index"),
    path('profile/', views.profile, name='profile'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("delete-profile/", views.delete_profile, name="delete_profile"),
    path("create-ride/", views.create_ride, name="create_ride"),
    path('ride/depart/<int:ride_id>/', views.depart_ride, name='depart_ride'),
    path('ride/complete/<int:ride_id>/', views.complete_ride, name='complete_ride'), 
    path("update-seat-status/", views.update_seat_status, name="update_seat_status"),
    path('driver/<int:driver_id>/', views.driver_detail, name='driver_detail'),
    path('rate-driver/<int:driver_id>/', views.rate_driver, name='rate_driver'),
    path('save-location/', views.save_location, name='save_location'),
    path('history/', views.ride_history, name='ride_history'),
    path('terminal-schedules/', views.terminal_schedules, name='terminal_schedules'),
    
    # Terminal Admin Dashboard
    path('terminal-admin/dashboard/', views.terminal_admin_dashboard, name='terminal_admin_dashboard'),
    
    # Terminal Admin - Manage Drivers
    path('terminal-admin/drivers/', views.terminal_admin_drivers, name='terminal_admin_drivers'),
    path('terminal-admin/drivers/<int:driver_id>/', views.terminal_admin_driver_detail, name='terminal_admin_driver_detail'),
    path('terminal-admin/drivers/<int:driver_id>/toggle/', views.terminal_admin_toggle_driver, name='terminal_admin_toggle_driver'),
    
    # Terminal Admin - Manage Rides
    path('terminal-admin/rides/', views.terminal_admin_rides, name='terminal_admin_rides'),
    path('terminal-admin/rides/<int:ride_id>/update-status/', views.terminal_admin_update_ride_status, name='terminal_admin_update_ride_status'),
    path('terminal-admin/rides/<int:ride_id>/delete/', views.terminal_admin_delete_ride, name='terminal_admin_delete_ride'),

    path('terminal-admin/pending-drivers/', views.terminal_admin_pending_drivers, name='terminal_admin_pending_drivers'),
    path('terminal-admin/drivers/<int:driver_id>/approve/', views.terminal_admin_approve_driver, name='terminal_admin_approve_driver'),
    path('terminal-admin/drivers/<int:driver_id>/reject/', views.terminal_admin_reject_driver, name='terminal_admin_reject_driver'),

    path('terminal-admin/create-schedule/', views.terminal_admin_create_schedule, name='terminal_admin_create_schedule'),
    path('terminal-admin/create-schedule-ajax/', views.terminal_admin_create_schedule_ajax, name='terminal_admin_create_schedule_ajax'),
    path('terminal-admin/delete-schedule/<int:ride_id>/', views.terminal_admin_delete_schedule, name='terminal_admin_delete_schedule'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)