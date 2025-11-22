from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Driver, Terminal, Ride

class DriverRegisterForm(UserCreationForm):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=True)
    address = forms.CharField(required=False)
    sex = forms.ChoiceField(choices=[('Male', 'Male'), ('Female', 'Female')], required=False)

    class Meta:
        model = Driver  
        fields = ['username', 'email', 'password1', 'password2']

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def save(self, commit=True):
        driver = super().save(commit=False)
        driver.first_name = self.cleaned_data['first_name']
        driver.last_name = self.cleaned_data['last_name']
        driver.email = self.cleaned_data.get('email', '')
        driver.address = self.cleaned_data['address']
        driver.sex = self.cleaned_data['sex']
        if commit:
            driver.save()
        return driver
    
class DriverProfileForm(forms.ModelForm):
    """
    Profile form with terminal selection field.
    The assigned_terminal field allows drivers to request to join a terminal.
    """
    
    # Override to use ModelChoiceField - USE Terminal, NOT TERMINAL_CHOICES
    assigned_terminal = forms.ModelChoiceField(
        queryset=Terminal.objects.none(),  # Will be set in __init__
        required=False,
        empty_label="-- Select a Terminal --",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Register to Terminal'
    )
    
    class Meta:
        model = Driver
        fields = [
            'first_name', 
            'last_name', 
            'email', 
            'username', 
            'address', 
            'sex', 
            'profile_picture',
            'assigned_terminal',
        ]
        
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'username': 'Username',
            'address': 'Address',
            'sex': 'Sex',
            'profile_picture': 'Profile Picture',
        }
        
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically populate terminal choices from database
        self.fields['assigned_terminal'].queryset = Terminal.objects.filter(
            is_active=True
        ).order_by('name')
        
        # If driver is already approved, disable the field
        if self.instance and self.instance.pk:
            if self.instance.terminal_status == 'approved':
                self.fields['assigned_terminal'].disabled = True
                self.fields['assigned_terminal'].help_text = 'You are already approved for this terminal. Contact admin to change.'
    
    def save(self, commit=True):
        driver = super().save(commit=False)

        # If terminal assignment changed, reset status to pending
        if self.instance.pk and 'assigned_terminal' in self.changed_data:
            new_terminal = self.cleaned_data.get('assigned_terminal')
            if new_terminal:
                driver.terminal_status = 'pending'
                driver.terminal_rejection_reason = None
            else:
                driver.assigned_terminal = None
                driver.terminal_status = 'pending'
                driver.terminal_rejection_reason = None
        
        if commit:
            driver.save()
        return driver


class RideForm(forms.ModelForm):
    class Meta:
        model = Ride
        fields = [
            'terminal',
            'location',
            'start_point',
            'route',
            'departure_time',
            'seats_available',
            'plate_number',
        ]

        labels = {
            'terminal': 'Terminal Name',
            'location': 'Terminal Location',
            'start_point': 'Starting Point',
            'route': 'Destination Point',
            'departure_time': 'Departure Date & Time',
            'seats_available': 'Seats Available',
            'plate_number': 'Vehicle Plate Number',
        }

        widgets = {
            'terminal': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'start_point': forms.Select(attrs={'class': 'form-control'}),
            'route': forms.Select(attrs={'class': 'form-control'}),
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'seats_available': forms.NumberInput(attrs={'class': 'form-control'}),
            'plate_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class RideScheduleForm(forms.ModelForm):
    """
    Form for terminal admin to create ride schedules
    """
    assigned_driver = forms.ModelChoiceField(
        queryset=Driver.objects.none(),
        required=True,
        label='Assign to Driver',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Ride
        fields = [
            'route',
            'departure_time',
            'plate_number',
            'assigned_driver',
        ]
        
        labels = {
            'route': 'Destination',
            'departure_time': 'Departure Date & Time',
            'plate_number': 'Vehicle Plate Number',
        }
        
        widgets = {
            'route': forms.Select(attrs={'class': 'form-control'}),
            'departure_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'plate_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, terminal, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show approved drivers from this terminal
        self.fields['assigned_driver'].queryset = Driver.objects.filter(
            assigned_terminal=terminal,
            terminal_status='approved',
            is_active=True
        ).order_by('first_name', 'last_name')
        
        # Set empty label
        self.fields['assigned_driver'].empty_label = "-- Select Driver --"