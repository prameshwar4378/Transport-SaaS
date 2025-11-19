from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.html import format_html
import os
import re



from django.core.exceptions import PermissionDenied

class RoleBasedAccessMixin:
    """Mixin for role-based access control"""
    
    def check_business_access(self, user, business):
        """Check if user has access to this business data"""
        if user.is_system_admin:
            return True
        
        if user.is_business_owner and user.business == business:
            return True
            
        if user.is_staff_member and user.business == business:
            return True
            
        return False
    
    def check_object_permission(self, user, obj):
        """Check if user has permission for specific object"""
        if user.is_system_admin:
            return True
            
        # Get business from object
        business = None
        if hasattr(obj, 'business'):
            business = obj.business
        elif hasattr(obj, 'get_business'):  # For Bill model
            business = obj.get_business()
            
        return self.check_business_access(user, business)

class BusinessManager(models.Manager, RoleBasedAccessMixin):
    """Custom manager for business-specific queries"""
    
    def for_user(self, user):
        """Get queryset based on user role"""
        if user.is_system_admin:
            return self.all()
        elif user.is_business_owner or user.is_staff_member:
            return self.filter(pk=user.business.pk)
        return self.none()

class StaffPermissionMixin:
    """Mixin for staff permission checks"""
    
    def can_view(self, user):
        return self.check_business_access(user, self.business)
    
    def can_edit(self, user):
        if user.is_system_admin:
            return True
        return user.is_business_owner and user.business == self.business
    
    def can_delete(self, user):
        return user.is_system_admin or (user.is_business_owner and user.business == self.business)
    


def validate_mobile_number(value):
    """Validate that mobile number contains exactly 10 digits"""
    if value and (len(value) != 10 or not value.isdigit()):
        raise ValidationError('Mobile number must be exactly 10 digits.')

def validate_vehicle_number(value):
    """Basic validation for Indian vehicle numbers"""
    if value:
        value = value.upper().replace(' ', '')
        # Basic pattern for Indian vehicle numbers: XX99XX9999 or similar
        if len(value) < 8:
            raise ValidationError('Vehicle number seems too short.')
        if not re.match(r'^[A-Z0-9]+$', value):
            raise ValidationError('Vehicle number can only contain letters and numbers.')
    return value



class Business(models.Model):
    BUSINESS_STATUS = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    ]
    
    business_name = models.CharField(max_length=100)
    business_label = models.CharField(max_length=15, unique=True)  # Unique identifier
    mobile_number = models.CharField(max_length=10, validators=[validate_mobile_number])
    alternate_mobile_number = models.CharField(max_length=10, null=True, blank=True, validators=[validate_mobile_number])
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    business_number = models.CharField(max_length=50, null=True, blank=True)
    
    # Business status and limits
    status = models.CharField(max_length=20, choices=BUSINESS_STATUS, default='active')
    max_staff_users = models.IntegerField(default=5)  # Simple user limit
    max_vehicles = models.IntegerField(default=10)    # Simple vehicle limit
    
    # Business photos
    business_logo = models.ImageField(upload_to='business_logos/', null=True, blank=True)
    business_photo1 = models.ImageField(upload_to='business_photos/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.business_name

    @property
    def display_name(self):
        return f"{self.business_name} - {self.mobile_number}"

    @property
    def total_staff_users(self):
        """Count active staff users for this business"""
        return self.customuser_set.filter(role='staff', is_active_staff=True).count()

    @property
    def total_vehicles(self):
        """Count vehicles for this business"""
        return self.vehicle_set.count()

    @property
    def total_bills(self):
        """Count bills for this business"""
        return self.bill_set.count()

    @property
    def is_active(self):
        return self.status == 'active'

    def can_add_staff(self):
        """Check if business can add more staff"""
        return self.total_staff_users < self.max_staff_users

    def can_add_vehicle(self):
        """Check if business can add more vehicles"""
        return self.total_vehicles < self.max_vehicles

    def get_business_owner(self):
        """Get the business owner user"""
        return self.customuser_set.filter(role='business_owner').first()
    
class VehicleOwner(models.Model, RoleBasedAccessMixin):   
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    owner_name = models.CharField(max_length=255, unique=False)
    owner_mobile_number = models.CharField(max_length=10, validators=[validate_mobile_number])
    owner_alternate_mobile_number = models.CharField(max_length=10, null=True, blank=True, validators=[validate_mobile_number])
    pan_card = models.FileField(upload_to='vehicle_owner_documents/pan_cards/', null=True, blank=True)
    adhar_card = models.FileField(upload_to='vehicle_owner_documents/adhar_cards/', null=True, blank=True)
    document1 = models.FileField(upload_to='vehicle_owner_documents/other_documents/', null=True, blank=True)
    document2 = models.FileField(upload_to='vehicle_owner_documents/other_documents/', null=True, blank=True)
    owner_photo = models.ImageField(upload_to='vehicle_owner_photos/', null=True, blank=True, verbose_name="Owner Photo")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.owner_name} - {self.owner_mobile_number}"

    @property
    def display_name(self):
        """Display owner name with mobile for admin"""
        return f"{self.owner_name} - {self.owner_mobile_number}"

    @property
    def photo_preview(self):
        """Display photo preview in admin"""
        if self.owner_photo:
            return format_html('<img src="{}" width="50" height="50" />', self.owner_photo.url)
        return "No Photo"
    
    photo_preview.fget.short_description = 'Photo Preview'

    @property
    def total_vehicles(self):
        """Count of vehicles owned by this owner"""
        return self.vehicle_set.count()
    
    total_vehicles.fget.short_description = 'Total Vehicles'

    def clean(self):
        """Enhanced validation that prevents duplicate name + mobile in same business"""
        super().clean()  # Call parent clean first
        
        # Only run validation if we have name, mobile, and business
        if self.owner_name and self.owner_mobile_number and self.business_id:
            queryset = VehicleOwner.objects.filter(
                business_id=self.business_id,
                owner_name=self.owner_name,
                owner_mobile_number=self.owner_mobile_number
            )
            
            # Exclude current instance when editing
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            
            if queryset.exists():
                raise ValidationError({
                    'owner_mobile_number': 'An owner with this name and mobile number already exists in your business.',
                    'owner_name': 'An owner with this name and mobile number already exists in your business.'
                })

    objects = BusinessManager()
    
    class Meta:
        unique_together = ['business', 'owner_name', 'owner_mobile_number']



class Vehicle(models.Model, RoleBasedAccessMixin): 
    owner = models.ForeignKey(VehicleOwner, on_delete=models.CASCADE, null=True, blank=True) 
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    vehicle_number = models.CharField(max_length=20, unique=False)
    vehicle_name = models.CharField(max_length=100, null=True, blank=True)
    model_name = models.CharField(max_length=255, null=True, blank=True) 
    notes = models.TextField(null=True, blank=True)
    document1 = models.FileField(upload_to='vehicle_documents/', null=True, blank=True)
    document2 = models.FileField(upload_to='vehicle_documents/', null=True, blank=True)
    vehicle_photo1 = models.ImageField(upload_to='vehicle_photos/', null=True, blank=True, verbose_name="Vehicle Photo 1")
    vehicle_photo2 = models.ImageField(upload_to='vehicle_photos/', null=True, blank=True, verbose_name="Vehicle Photo 2")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = BusinessManager()

    def __str__(self):
        return f"{self.vehicle_name or 'Vehicle'} - {self.vehicle_number}"

    @property
    def display_name(self):
        """Display vehicle name with number for admin"""
        if self.vehicle_name:
            return f"{self.vehicle_name} - {self.vehicle_number}"
        return self.vehicle_number

    @property
    def photo_preview(self):
        """Display vehicle photo preview in admin"""
        if self.vehicle_photo1:
            return format_html('<img src="{}" width="50" height="50" />', self.vehicle_photo1.url)
        return "No Photo"
    
    photo_preview.fget.short_description = 'Photo Preview'

    @property
    def total_bills(self):
        """Count of bills for this vehicle"""
        return self.bills.count()
    
    total_bills.fget.short_description = 'Total Bills'

    @property
    def owner_info(self):
        """Get owner information"""
        if self.owner:
            return f"{self.owner.owner_name} - {self.owner.owner_mobile_number}"
        return "No Owner"
    
    owner_info.fget.short_description = 'Owner Information'

    def clean(self):
        """Comprehensive validation for Vehicle model"""
        super().clean()
        
        # Validate and format vehicle number
        self._validate_vehicle_number()
        
        # Validate owner-business consistency
        self._validate_owner_business_consistency()
         

    def _validate_vehicle_number(self):
        """Validate and format vehicle number"""
        if self.vehicle_number:
            # Format vehicle number
            self.vehicle_number = validate_vehicle_number(self.vehicle_number)
            
            # Additional validation for Indian vehicle numbers
            if len(self.vehicle_number) < 8:
                raise ValidationError({
                    'vehicle_number': 'Vehicle number seems too short. Minimum 8 characters required.'
                })
            
            # Check format: Should contain both letters and numbers
            if not any(char.isdigit() for char in self.vehicle_number):
                raise ValidationError({
                    'vehicle_number': 'Vehicle number should contain at least one number.'
                })
            
            if not any(char.isalpha() for char in self.vehicle_number):
                raise ValidationError({
                    'vehicle_number': 'Vehicle number should contain at least one letter.'
                })

    def _validate_owner_business_consistency(self):
        """Validate owner belongs to the same business as vehicle"""
        if self.owner and self.business_id:
            if self.owner.business != self.business:
                print()
                print(f"🚀 DEBUG: Owner business ({self.owner.business.business_name}) does not match vehicle business ({self.business.business_name})")
                print()
                raise ValidationError({
                    'owner': f'Selected owner belongs to different business ({self.owner.business.business_name}).'
                })
        
        # If no owner selected, ensure it's intentional
        if not self.owner and self.pk:
            # For existing vehicles without owner, show warning but allow
            pass
 

    def save(self, *args, **kwargs):
        """Ensure business is set and validations pass"""
        # Set business from user if not set (for new objects)
        if not self.pk and not self.business_id:
            try:
                from crum import get_current_user
                current_user = get_current_user()
                if current_user and hasattr(current_user, 'business') and current_user.business:
                    self.business = current_user.business
                    print(f"DEBUG: Auto-set business to {self.business} for new vehicle")
            except Exception:
                pass  # Business will be set by admin save_model
        
        # Convert empty strings to None for optional fields
        self.vehicle_name = self.vehicle_name or None
        self.model_name = self.model_name or None
        self.notes = self.notes or None
        
        # Ensure vehicle number is properly formatted
        if self.vehicle_number:
            self.vehicle_number = self.vehicle_number.upper().replace(' ', '')
        
        # Run full validation (including limit checks)
        self.clean()
        
        super().save(*args, **kwargs)

    class Meta:
        # REMOVE the database constraint - we handle uniqueness in form
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['business', 'vehicle_number'],
        #         name='unique_vehicle_number_business'
        #     ),
        # ]
        pass

class Party(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE) 
    name = models.CharField(max_length=255)
    gst_no = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="GST Number")
    pan_card = models.FileField(upload_to='party_documents/pan_cards/', null=True, blank=True)
    adhar_card = models.FileField(upload_to='party_documents/adhar_cards/', null=True, blank=True)
    document1 = models.FileField(upload_to='party_documents/other_documents/', null=True, blank=True)
    document2 = models.FileField(upload_to='party_documents/other_documents/', null=True, blank=True)
    mobile = models.CharField(max_length=10, null=True, blank=True, validators=[validate_mobile_number])
    alternate_mobile = models.CharField(max_length=10, null=True, blank=True, validators=[validate_mobile_number])
    party_photo = models.ImageField(upload_to='party_photos/', null=True, blank=True, verbose_name="Party Photo")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = BusinessManager()

    def __str__(self):
        return f"{self.name} - {self.mobile}" if self.mobile else self.name

    @property
    def display_name(self):
        """Display party name with mobile for admin"""
        if self.mobile:
            return f"{self.name} - {self.mobile}"
        return self.name

    @property
    def photo_preview(self):
        """Display party photo preview in admin"""
        if self.party_photo:
            return format_html('<img src="{}" width="50" height="50" />', self.party_photo.url)
        return "No Photo"
    
    photo_preview.fget.short_description = 'Photo Preview'

    @property
    def total_bills(self):
        """Count of bills for this party"""
        return self.bills.count()
    
    total_bills.fget.short_description = 'Total Bills'

    def clean(self):
        """Enhanced validation that prevents duplicate name + mobile in same business"""
        super().clean()  # Call parent clean first
        
        # Only run validation if we have name, mobile, and business
        if self.name and self.mobile and self.business_id:
            queryset = Party.objects.filter(
                business_id=self.business_id,
                name=self.name,
                mobile=self.mobile
            )
            
            # Exclude current instance when editing
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            
            if queryset.exists():
                raise ValidationError({
                    'mobile': f'A party with name "{self.name}" and mobile number {self.mobile} already exists in your business.',
                    'name': f'A party with name "{self.name}" and mobile number {self.mobile} already exists in your business.'
                })

    def save(self, *args, **kwargs):
        """Ensure business is set and format fields"""
        # Set business from user if not set (for new objects)
        if not self.pk and not self.business_id:
            try:
                from crum import get_current_user
                current_user = get_current_user()
                if current_user and hasattr(current_user, 'business') and current_user.business:
                    self.business = current_user.business
            except Exception:
                pass
        
        # Convert empty strings to None for mobile fields
        self.mobile = self.mobile or None
        self.alternate_mobile = self.alternate_mobile or None
        self.gst_no = self.gst_no or None
        
        # Clean GST number format
        if self.gst_no:
            self.gst_no = self.gst_no.strip().upper()
        
        # Run validation before saving
        self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name_plural = "Parties"
        unique_together = ['business', 'name', 'mobile']
        constraints = [
            # Only enforce unique name+mobile when mobile is NOT null
            models.UniqueConstraint(
                fields=['business', 'name', 'mobile'],
                name='unique_party_name_mobile_business',
                condition=models.Q(mobile__isnull=False)
            ),
            # Only enforce unique mobile when mobile is NOT null
            models.UniqueConstraint(
                fields=['business', 'mobile'],
                name='unique_party_mobile',
                condition=models.Q(mobile__isnull=False)
            ),
            # Only enforce unique alternate_mobile when alternate_mobile is NOT null
            models.UniqueConstraint(
                fields=['business', 'alternate_mobile'],
                name='unique_party_alternate_mobile', 
                condition=models.Q(alternate_mobile__isnull=False)
            ),
            # Global GST uniqueness (only when GST is provided)
            models.UniqueConstraint(
                fields=['gst_no'],
                name='unique_party_gst',
                condition=models.Q(gst_no__isnull=False)
            ),
        ]


class Driver(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE) 
    driver_name = models.CharField(max_length=255)
    licence = models.FileField(upload_to='driver_documents/licence/', null=True, blank=True)
    adhar_card = models.FileField(upload_to='driver_documents/adhar_cards/', null=True, blank=True)
    document1 = models.FileField(upload_to='driver_documents/other_documents/', null=True, blank=True)
    document2 = models.FileField(upload_to='driver_documents/other_documents/', null=True, blank=True)
    profile_photo = models.ImageField(upload_to='driver_documents/profile_photos/', null=True, blank=True)
    mobile = models.CharField(max_length=10, null=True, blank=True, validators=[validate_mobile_number])
    alternate_mobile = models.CharField(max_length=10, null=True, blank=True, validators=[validate_mobile_number])
    driver_photo1 = models.ImageField(upload_to='driver_photos/', null=True, blank=True, verbose_name="Driver Photo 1")
    driver_photo2 = models.ImageField(upload_to='driver_photos/', null=True, blank=True, verbose_name="Driver Photo 2")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BusinessManager()
 
    def __str__(self):
        return f"{self.driver_name} - {self.mobile}" if self.mobile else self.driver_name

    @property
    def display_name(self):
        """Display driver name with mobile for admin"""
        if self.mobile:
            return f"{self.driver_name} - {self.mobile}"
        return self.driver_name

    @property
    def photo_preview(self):
        """Display driver photo preview in admin"""
        if self.profile_photo:
            return format_html('<img src="{}" width="50" height="50" />', self.profile_photo.url)
        return "No Photo"
    
    photo_preview.fget.short_description = 'Photo Preview'

    @property
    def total_bills(self):
        """Count of bills for this driver"""
        return self.bills.count()
    
    total_bills.fget.short_description = 'Total Bills'

    def clean(self):
        """Comprehensive validation for Driver model"""
        super().clean()
        
        # Handle mobile validation
        if self.mobile:
            # Validate mobile doesn't exist in same business
            self._validate_mobile_unique('mobile', self.mobile)
            
            # Validate mobile and alternate_mobile are not same
            if self.mobile == self.alternate_mobile:
                raise ValidationError({
                    'alternate_mobile': 'Alternate mobile cannot be same as primary mobile.'
                })
        
        # # Handle alternate mobile validation  
        # if self.alternate_mobile:
        #     # Validate alternate mobile doesn't exist as primary mobile in same business
        #     self._validate_mobile_unique('alternate_mobile', self.alternate_mobile)
            
        #     # Validate alternate mobile doesn't match any other driver's primary mobile
        #     queryset = Driver.objects.filter(
        #         business_id=self.business_id,
        #         mobile=self.alternate_mobile
        #     )
        #     if self.pk:
        #         queryset = queryset.exclude(pk=self.pk)
        #     if queryset.exists():
        #         raise ValidationError({
        #             'alternate_mobile': 'This mobile number is already registered as primary mobile for another driver.'
        #         })

    def _validate_mobile_unique(self, field_name, mobile_value):
        """Helper method to validate mobile uniqueness"""
        if not mobile_value or not self.business_id:
            return
            
        # Check against primary mobile numbers
        mobile_queryset = Driver.objects.filter(
            business_id=self.business_id,
            mobile=mobile_value
        )
        
        # Check against alternate mobile numbers  
        alternate_queryset = Driver.objects.filter(
            business_id=self.business_id,
            alternate_mobile=mobile_value
        )
        
        if self.pk:
            mobile_queryset = mobile_queryset.exclude(pk=self.pk)
            alternate_queryset = alternate_queryset.exclude(pk=self.pk)
        
        if mobile_queryset.exists():
            raise ValidationError({
                field_name: f'Mobile number {mobile_value} is already registered as primary mobile for another driver.'
            })
        
        # if alternate_queryset.exists():
        #     raise ValidationError({
        #         field_name: f'Mobile number {mobile_value} is already registered as alternate mobile for another driver.'
        #     })
 
    def save(self, *args, **kwargs):
        """Ensure business is set and validations pass"""
        # Set business from user if not set (for new objects)
        if not self.pk and not self.business_id:
            try:
                from crum import get_current_user
                current_user = get_current_user()
                if current_user and hasattr(current_user, 'business') and current_user.business:
                    self.business = current_user.business
            except Exception:
                pass  # Business will be set by admin save_model
        
        # Convert empty strings to None for mobile fields
        self.mobile = self.mobile or None
        self.alternate_mobile = self.alternate_mobile or None
        
        # Run full validation
        self.clean()
        
        super().save(*args, **kwargs)
        
    class Meta:
        unique_together = ['business', 'mobile']
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'mobile'],
                name='unique_driver_mobile',
                condition=models.Q(mobile__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['business', 'alternate_mobile'], 
                name='unique_driver_alternate_mobile',
                condition=models.Q(alternate_mobile__isnull=False)
            ),
        ]





class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'System Admin'),
        ('business_owner', 'Business Owner'),
        ('staff', 'Staff'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True, blank=True) 
    profile_picture = models.ImageField(upload_to='user_profile_pictures/', null=True, blank=True)
    
    # Staff specific fields
    is_active_staff = models.BooleanField(default=True)
    permissions = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        role_display = "Superuser" if self.is_superuser else self.get_role_display()
        return f"{self.username} - {role_display}"

    @property
    def display_name(self):
        role_display = "Superuser" if self.is_superuser else self.get_role_display()
        business_name = self.business.business_name if self.business else 'No Business'
        return f"{self.username} ({role_display}) - {business_name}"

    @property
    def is_system_admin(self):
        if not hasattr(self, 'is_superuser') or not hasattr(self, 'role'):
            return False
        return self.is_superuser or self.role == 'admin'
    
    @property
    def is_business_owner(self):
        if not hasattr(self, 'is_superuser') or not hasattr(self, 'role'):
            return False
        return self.role == 'business_owner' and not self.is_superuser
    
    @property
    def is_staff_member(self):
        if not hasattr(self, 'is_superuser') or not hasattr(self, 'role'):
            return False
        return self.role == 'staff' and not self.is_superuser
    
    def clean(self):
        # Superuser bypasses all role-based validations
        if hasattr(self, 'is_superuser') and not self.is_superuser:
            # Validation rules for non-superusers
            if self.role == 'staff' and not self.business_id:
                raise ValidationError({'business': 'Staff members must be assigned to a business.'})
            
            if self.role == 'admin' and self.business_id:
                raise ValidationError({'business': 'System admin cannot be assigned to a business.'})
            
            # Check staff limit when creating new staff users
            if (self.role == 'staff' and self.business_id and 
                not self.pk and self.is_active_staff):  # Only for new active staff
                business = Business.objects.get(pk=self.business_id)
                if not business.can_add_staff():
                    print("##################")
                    raise ValidationError({
                        'role': f'Staff limit reached for {business.business_name}. '
                               f'Maximum {business.max_staff_users} staff members allowed. '
                               f'Current: {business.total_staff_users}.'
                    })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        if hasattr(self, 'is_superuser') and self.is_superuser:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if hasattr(self, 'is_superuser') and self.is_superuser:
            return True
        return super().has_module_perms(app_label)



class Bill(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    bill_number = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    party = models.ForeignKey('Party', on_delete=models.SET_NULL, related_name='bills', verbose_name="Party Name", null=True, blank=True)
    driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills', verbose_name="Driver")
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='bills', verbose_name="Vehicle")
    reference = models.ForeignKey('VehicleOwner', on_delete=models.SET_NULL, null=True, blank=True, related_name='referenced_bills', verbose_name="Referenced By")
    
    from_location = models.CharField(max_length=255, verbose_name="From Location")
    to_location = models.CharField(max_length=255, verbose_name="To Location")
    material_type = models.CharField(max_length=255, null=True, blank=True, verbose_name="Type of Material")
    rent_amount = models.DecimalField(max_digits=10, decimal_places=0,default=0, verbose_name="Rent Amount")
    advance_amount = models.DecimalField(max_digits=10, decimal_places=0,default=0, verbose_name="Advance Amount")
    pending_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Pending Amount")
    commission = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission %")
    commission_charge = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission Amount")
    commission_received = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission Received")
    commission_pending = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission Pending")
    
    notes = models.TextField(null=True, blank=True, verbose_name="Additional Notes")
    
    # Bill related photos
    loading_photo = models.ImageField(upload_to='bill_photos/loading/', null=True, blank=True, verbose_name="Loading Photo")
    unloading_photo = models.ImageField(upload_to='bill_photos/unloading/', null=True, blank=True, verbose_name="Unloading Photo")
    document_photo = models.ImageField(upload_to='bill_photos/documents/', null=True, blank=True, verbose_name="Document Photo")
 
    bill_date = models.DateField(verbose_name="Bill Date")
    commission_received_date = models.DateField(null=True, blank=True, verbose_name="Commission Received Date")

    # Add these missing fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BusinessManager()
    
    class Meta: 
        ordering = ['-bill_date']  # Remove '-created_at' since it's not in ordering anymore
        verbose_name = "Bill"
        verbose_name_plural = "Bills"

    # ... rest of your Bill model methods remain the same

    def __str__(self):
        return f"Bill #{self.bill_number} - {self.party.name if self.party else 'Unknown'}"

    @property
    def display_name(self):
        """Display bill number with party name for admin"""
        party_name = self.party.name if self.party else 'Unknown Party'
        return f"Bill #{self.bill_number} - {party_name}"

    @property
    def photo_preview(self):
        """Display loading photo preview in admin"""
        if self.loading_photo:
            return format_html('<img src="{}" width="50" height="50" />', self.loading_photo.url)
        return "No Photo"
    
    photo_preview.fget.short_description = 'Loading Photo'

    @property
    def payment_status(self):
        """Calculate payment status"""
        if self.pending_amount == 0:
            return "Paid"
        elif self.advance_amount == 0:
            return "Pending"
        else:
            return "Partially Paid"
    
    payment_status.fget.short_description = 'Payment Status'

    @property
    def commission_status(self):
        """Calculate commission status"""
        if not self.commission_charge or self.commission_charge == 0:
            return "No Commission"
        elif self.commission_pending == 0:
            return "Commission Paid"
        elif self.commission_received == 0:
            return "Commission Pending"
        else:
            return "Commission Partially Paid"
    
    commission_status.fget.short_description = 'Commission Status'

    @property
    def trip_route(self):
        """Display trip route"""
        return f"{self.from_location} to {self.to_location}"
    
    trip_route.fget.short_description = 'Trip Route'

    def clean(self):
        """Enhanced validation for bill data"""
        # Auto-calculate pending amount
        self.pending_amount = self.rent_amount - self.advance_amount
        
        # Auto-calculate commission charge if commission percentage is provided
        if self.commission and self.commission > 0 and not self.commission_charge:
            self.commission_charge = (self.rent_amount * self.commission) / 100
        
        # Auto-calculate commission pending
        if self.commission_charge:
            self.commission_pending = self.commission_charge - (self.commission_received or 0)
 
    def save(self, *args, **kwargs):
        # Only generate bill number if it's a new record and bill_number is empty
        if not self.pk and not self.bill_number:
            try:
                # Generate a prefix from business label
                if self.business and self.business.business_label:
                    words = self.business.business_label.strip().split()

                    if len(words) == 1:
                        # Single word → take first 3 letters
                        business_prefix = words[0][:3].upper()
                    elif len(words) == 2:
                        # Two words → take first letter of each
                        business_prefix = (words[0][0] + words[1][0]).upper()
                    else:
                        # Three or more → take first letter of each up to 3 letters
                        business_prefix = ''.join(w[0] for w in words[:3]).upper()
                else:
                    business_prefix = "BILL"

                # Find the last bill for this business with proper error handling
                try:
                    last_bill = Bill.objects.filter(business=self.business).order_by('-id').first()
                    if last_bill and last_bill.bill_number:
                        try:
                            # Extract number from format like "ABC-0001"
                            last_number_str = last_bill.bill_number.split('-')[-1]
                            last_number = int(last_number_str)
                            next_number = last_number + 1
                        except (ValueError, IndexError):
                            next_number = 1
                    else:
                        next_number = 1
                except Exception as e:
                    # Fallback if there's any issue querying the database
                    print(f"DEBUG: Error getting last bill: {e}")
                    next_number = 1

                # Generate bill number and ensure uniqueness
                max_attempts = 10
                for attempt in range(max_attempts):
                    bill_number_candidate = f"{business_prefix}-{str(next_number).zfill(4)}"
                    
                    # Check if this bill number already exists
                    if not Bill.objects.filter(bill_number=bill_number_candidate).exists():
                        self.bill_number = bill_number_candidate
                        break
                        
                    next_number += 1
                else:
                    # If we exhausted all attempts, use a timestamp-based fallback
                    import time
                    timestamp = int(time.time())
                    self.bill_number = f"{business_prefix}-{timestamp}"

            except Exception as e:
                # Ultimate fallback
                import time
                timestamp = int(time.time())
                self.bill_number = f"BILL-{timestamp}"
                print(f"DEBUG: Error generating bill number, using fallback: {e}")

        # Ensure calculations are done before saving
        self.clean()
        super().save(*args, **kwargs)


    def get_business(self):
        return self.business
 