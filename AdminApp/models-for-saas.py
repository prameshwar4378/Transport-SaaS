from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string 
from django.core.exceptions import ValidationError



def vehicle_owner_pan_path(instance, filename):
    return f'company_{instance.company.id}/vehicle_owners/pan_cards/{filename}'

def vehicle_owner_adhar_path(instance, filename):
    return f'company_{instance.company.id}/vehicle_owners/adhar_cards/{filename}'

    
def vehicle_owner_document1_path(instance, filename):
    return f'company_{instance.company.id}/vehicle_owners/document1/{filename}'

    
def vehicle_owner_document2_path(instance, filename):
    return f'company_{instance.company.id}/vehicle_owners/document2/{filename}'





def vehicle_document1_path(instance, filename):
    return f'company_{instance.company.id}/vehicle/document1/{filename}'

def vehicle_document2_path(instance, filename):
    return f'company_{instance.company.id}/vehicle/document2/{filename}'

    

def vehicle_party_pan_card_path(instance, filename):
    return f'company_{instance.company.id}/party/pan_card/{filename}'
def vehicle_party_adhar_card_path(instance, filename):
    return f'company_{instance.company.id}/party/adhar_card/{filename}'
def vehicle_party_document1_path(instance, filename):
    return f'company_{instance.company.id}/party/document1/{filename}'
def vehicle_party_document2_path(instance, filename):
    return f'company_{instance.company.id}/party/document2/{filename}'


def vehicle_driver_licence_path(instance, filename):
    return f'company_{instance.company.id}/driver/licence/{filename}'
def vehicle_driver_adhar_card_path(instance, filename):
    return f'company_{instance.company.id}/driver/adhar_cards/{filename}'
def vehicle_driver_document1_path(instance, filename):
    return f'company_{instance.company.id}/driver/other_documents/{filename}'
def vehicle_driver_document2_path(instance, filename):
    return f'company_{instance.company.id}/driver/other_documents/{filename}'
def vehicle_driver_profile_photo_path(instance, filename):
    return f'company_{instance.company.id}/driver/profile_photos/{filename}'
 
class Company(models.Model):
    """Main company/organization that can have multiple branches"""
    company_name = models.CharField(max_length=100)
    company_code = models.CharField(max_length=10, unique=True, editable=False)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15)
    address = models.TextField()
    is_active = models.BooleanField(default=True)
    subscription_plan = models.CharField(max_length=20, choices=[
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise')
    ], default='basic')
    subscription_end_date = models.DateField(null=True, blank=True)
    max_users = models.PositiveIntegerField(default=5)
    max_branches = models.PositiveIntegerField(default=3)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subscription_status(self):
        """Get subscription status"""
        from django.utils import timezone
        if not self.subscription_end_date:
            return "no_subscription"
        elif self.subscription_end_date < timezone.now().date():
            return "expired"
        else:
            return "active"
    @property
    def is_subscription_active(self):
        """Check if company has active subscription"""
        from django.utils import timezone
        if self.subscription_end_date and self.subscription_end_date >= timezone.now().date():
            return True
        return False
    
    @property
    def subscription_days_remaining(self):
        """Get days remaining in subscription"""
        from django.utils import timezone
        if self.subscription_end_date:
            delta = self.subscription_end_date - timezone.now().date()
            return max(0, delta.days)
        return 0
        
    @property
    def total_vehicles(self):
        return self.vehicles.count()
    
    @property
    def total_bills(self):
        return self.bills.count()
    
    def save(self, *args, **kwargs):
        if not self.company_code:
            self.company_code = get_random_string(8).upper()
        super().save(*args, **kwargs)

    @property
    def active_users_count(self):
        return self.users.filter(is_active=True).count()
    
    @property
    def active_branches_count(self):
        return self.branches.filter(is_active=True).count()
    
    @property
    def can_add_user(self):
        return self.active_users_count < self.max_users
    
    @property
    def can_add_branch(self):
        return self.active_branches_count < self.max_branches
    
    @property
    def total_drivers(self):
        return self.drivers.count()
    
    @property
    def total_parties(self):
        return self.parties.count()
    
    @property
    def total_vehicle_owners(self):
        return self.vehicle_owners.count()
    
    @property
    def monthly_revenue(self):
        from django.utils import timezone
        from django.db.models import Sum
        current_month = timezone.now().month
        current_year = timezone.now().year
        return self.bills.filter(
            bill_date__month=current_month, 
            bill_date__year=current_year
        ).aggregate(Sum('rent_amount'))['rent_amount__sum'] or 0
    
    @property
    def pending_commissions(self):
        from django.db.models import Sum
        return self.bills.aggregate(Sum('commission_pending'))['commission_pending__sum'] or 0


    
    @property
    def total_trips(self):
        return self.trips.count()
    
    @property
    def active_trips(self):
        return self.trips.filter(status='in_progress').count()
    
    @property
    def total_expenses(self):
        from django.db.models import Sum
        return self.expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    @property
    def monthly_expenses(self):
        from django.utils import timezone
        from django.db.models import Sum
        current_month = timezone.now().month
        current_year = timezone.now().year
        return self.expenses.filter(
            expense_date__month=current_month, 
            expense_date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    

    def __str__(self):
        return self.company_name





class CompanySettings(models.Model):
    """Company-specific settings and configurations"""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='settings')
    
    # Bill Settings
    auto_generate_bill_number = models.BooleanField(default=True)
    bill_number_prefix = models.CharField(max_length=10, default='BILL', blank=True)
    bill_terms_conditions = models.TextField(blank=True, null=True)
    
    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Financial Settings
    currency = models.CharField(max_length=10, default='INR')
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Vehicle Settings
    default_vehicle_notes = models.TextField(blank=True, null=True)

    default_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    bill_due_days = models.PositiveIntegerField(default=30)
    auto_assign_driver = models.BooleanField(default=False)

    enable_vehicle_tracking = models.BooleanField(default=False)
    maintenance_reminder_days = models.PositiveIntegerField(default=7)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings - {self.company.company_name}"
    


class Branch(models.Model):
    """Branch under a company (replaces Business model)"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    branch_name = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=10, unique=True, editable=False)
    branch_manager = models.CharField(max_length=100, null=True, blank=True)
    mobile_number = models.CharField(max_length=15)
    alternate_mobile_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField()
    email = models.EmailField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def branch_trips(self):
        return self.trips.count()
    
    @property
    def active_branch_trips(self):
        return self.trips.filter(status='in_progress').count()
    
    @property
    def branch_expenses(self):
        from django.db.models import Sum
        return self.expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    class Meta:
        verbose_name_plural = "Branches"
        unique_together = ['company', 'branch_name']

    
    @property
    def branch_drivers(self):
        return self.drivers.count()
    
    @property
    def branch_parties(self):
        return self.parties.count()
    
    @property
    def monthly_branch_revenue(self):
        from django.utils import timezone
        from django.db.models import Sum
        current_month = timezone.now().month
        current_year = timezone.now().year
        return self.bills.filter(
            bill_date__month=current_month, 
            bill_date__year=current_year
        ).aggregate(Sum('rent_amount'))['rent_amount__sum'] or 0
    
    @property
    def total_staff(self):
        return self.users.count()
    
    @property
    def branch_vehicles(self):
        return self.vehicles.count()
    
    @property
    def branch_bills(self):
        return self.bills.count()
    
    def save(self, *args, **kwargs):
        if not self.branch_code:
            self.branch_code = get_random_string(6).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.branch_name} - {self.company.company_name}"


class CustomUser(AbstractUser):
    """Extended user model with four roles"""
    # Role choices
    ROLE_CHOICES = [
        ('admin', 'System Admin (Developer)'),
        ('company_admin', 'Company Admin'),
        ('branch_manager', 'Branch Manager'),
        ('staff', 'Company Staff'),
    ]
    
    # User role and company/branch associations
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    
    # Additional fields
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='user_profiles/', null=True, blank=True)
    
    # Permission flags (for easy querying)
    is_system_admin = models.BooleanField(default=False)
    is_company_admin = models.BooleanField(default=False)
    is_branch_manager = models.BooleanField(default=False)
    is_company_staff = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'email']

    def save(self, *args, **kwargs):
        """Automatically set permission flags based on role"""
        # Reset all flags
        self.is_system_admin = False
        self.is_company_admin = False
        self.is_branch_manager = False
        self.is_company_staff = False
        
        # Set appropriate flag based on role
        if self.role == 'admin':
            self.is_system_admin = True
            self.is_staff = True
            self.is_superuser = True
        elif self.role == 'company_admin':
            self.is_company_admin = True
            self.is_staff = True
        elif self.role == 'branch_manager':
            self.is_branch_manager = True
            self.is_staff = True
        elif self.role == 'staff':
            self.is_company_staff = True
        
        # System admins don't need company/branch association
        if self.role == 'admin':
            self.company = None
            self.branch = None
        
        super().save(*args, **kwargs)

    def clean(self):
        """Validate user role and company/branch associations"""
        errors = {}
        
        # System Admin validations
        if self.role == 'admin':
            if self.company or self.branch:
                errors['role'] = "System Admin cannot be associated with any company or branch"
        
        # Company Admin validations
        elif self.role == 'company_admin':
            if not self.company:
                errors['company'] = "Company Admin must be associated with a company"
            if self.branch:
                errors['branch'] = "Company Admin cannot be associated with a specific branch"
        
        # Branch Manager validations
        elif self.role == 'branch_manager':
            if not self.company:
                errors['company'] = "Branch Manager must be associated with a company"
            if not self.branch:
                errors['branch'] = "Branch Manager must be associated with a branch"
            elif self.branch.company != self.company:
                errors['branch'] = "Branch must belong to the selected company"
        
        # Staff validations
        elif self.role == 'staff':
            if not self.company:
                errors['company'] = "Staff must be associated with a company"
            if not self.branch:
                errors['branch'] = "Staff must be associated with a branch"
            elif self.branch.company != self.company:
                errors['branch'] = "Branch must belong to the selected company"
        
        if errors:
            raise ValidationError(errors)

    @property
    def can_manage_company(self):
        """Check if user can manage company-level data"""
        return self.role in ['admin', 'company_admin']

    @property
    def can_manage_branch(self):
        """Check if user can manage branch-level data"""
        return self.role in ['admin', 'company_admin', 'branch_manager']

    @property
    def accessible_branches(self):
        """Get branches this user can access"""
        if self.role == 'admin':
            return Branch.objects.all()
        elif self.role == 'company_admin':
            return self.company.branches.all()
        elif self.role in ['branch_manager', 'staff']:
            return Branch.objects.filter(id=self.branch.id)
        return Branch.objects.none()


    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='customuser_set',
        related_query_name='customuser',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set',
        related_query_name='customuser',
    )

    def __str__(self):
        role_display = dict(self.ROLE_CHOICES).get(self.role, self.role)
        if self.company:
            return f"{self.username} - {role_display} - {self.company.company_name}"
        return f"{self.username} - {role_display}"

# Update all other models to use Branch instead of Business
class VehicleOwner(models.Model):  
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='vehicle_owners')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='vehicle_owners') 
    owner_name = models.CharField(max_length=255)
    owner_mobile_number = models.CharField(max_length=15)
    owner_alternate_mobile_number = models.CharField(max_length=15, null=True, blank=True) 
    pan_card = models.FileField(upload_to=vehicle_owner_pan_path, null=True, blank=True)
    adhar_card = models.FileField(upload_to=vehicle_owner_adhar_path, null=True, blank=True)
    document1 = models.FileField(upload_to=vehicle_owner_document1_path, null=True, blank=True)
    document2 = models.FileField(upload_to=vehicle_owner_document2_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        unique_together = ['company', 'owner_mobile_number']
        indexes = [
            models.Index(fields=['company', 'owner_name']),
        ]
        ordering = ['owner_name']

    def __str__(self):
        return f"{self.owner_name} - {self.owner_mobile_number}"

class Vehicle(models.Model): 
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='vehicles')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='vehicles') 
    owner = models.ForeignKey(VehicleOwner, on_delete=models.CASCADE, null=True, blank=True, related_name='vehicles') 
    vehicle_number = models.CharField(max_length=20)
    vehicle_name = models.CharField(max_length=100, null=True, blank=True)
    model_name = models.CharField(max_length=255, null=True, blank=True) 
    notes = models.TextField(null=True, blank=True)
    document1 = models.FileField(upload_to=vehicle_document1_path, null=True, blank=True)
    document2 = models.FileField(upload_to=vehicle_document2_path, null=True, blank=True)
    VEHICLE_STATUS = [
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=15, choices=VEHICLE_STATUS, default='active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        unique_together = ['company', 'vehicle_number']
        indexes = [
            models.Index(fields=['company', 'vehicle_number']),
        ]

    def clean(self):
        """Validate vehicle data"""
        if self.vehicle_number:
            # Basic validation for vehicle number format
            if len(self.vehicle_number) < 5:
                raise ValidationError({'vehicle_number': 'Vehicle number seems too short'})
        
        # Validate branch belongs to company
        if self.branch and self.branch.company != self.company:
            raise ValidationError({'branch': 'Branch must belong to the same company'})
        
        # Validate owner belongs to company
        if self.owner and self.owner.company != self.company:
            raise ValidationError({'owner': 'Vehicle owner must belong to the same company'})
        
    def __str__(self):
        if self.vehicle_name:
            return f"{self.vehicle_name} - {self.vehicle_number}"
        return self.vehicle_number


class VehicleMaintenance(models.Model):
    """Track vehicle maintenance and servicing"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='maintenances')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='maintenances')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenances')
    
    MAINTENANCE_TYPES = [
        ('routine', 'Routine Service'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('tire_change', 'Tire Change'),
        ('other', 'Other'),
    ]
    
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    maintenance_date = models.DateField()
    next_maintenance_date = models.DateField(null=True, blank=True)
    odometer_reading = models.PositiveIntegerField(null=True, blank=True)
    service_center = models.CharField(max_length=255, null=True, blank=True)
    invoice_number = models.CharField(max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-maintenance_date']
        indexes = [
            models.Index(fields=['company', 'maintenance_date']),
            models.Index(fields=['vehicle', 'maintenance_date']),
        ]

    def __str__(self):
        return f"{self.vehicle.vehicle_number} - {self.maintenance_type} - {self.maintenance_date}"
    

class Party(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='parties')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='parties') 
    name = models.CharField(max_length=255)
    gst_no = models.CharField(max_length=15, null=True, blank=True, verbose_name="GST Number")
    pan_card = models.FileField(upload_to=vehicle_party_pan_card_path, null=True, blank=True)
    adhar_card = models.FileField(upload_to=vehicle_party_adhar_card_path, null=True, blank=True)
    document1 = models.FileField(upload_to=vehicle_party_document1_path, null=True, blank=True)
    document2 = models.FileField(upload_to=vehicle_party_document2_path, null=True, blank=True)
    mobile = models.CharField(max_length=15, null=True, blank=True)
    alternate_mobile = models.CharField(max_length=15, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'gst_no']
        verbose_name_plural = "Parties"
        indexes = [
            models.Index(fields=['company', 'name']),
        ]
        ordering = ['name']

    def __str__(self):
        return self.name

class Driver(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='drivers')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='drivers') 
    driver_name = models.CharField(max_length=255)
    licence = models.FileField(upload_to=vehicle_driver_licence_path, null=True, blank=True)
    adhar_card = models.FileField(upload_to=vehicle_driver_adhar_card_path, null=True, blank=True)
    document1 = models.FileField(upload_to=vehicle_driver_document1_path, null=True, blank=True)
    document2 = models.FileField(upload_to=vehicle_driver_document2_path, null=True, blank=True)
    profile_photo = models.ImageField(upload_to=vehicle_driver_profile_photo_path, null=True, blank=True)
    mobile = models.CharField(max_length=15, null=True, blank=True)
    alternate_mobile = models.CharField(max_length=15, null=True, blank=True)

    DRIVER_STATUS = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=15, choices=DRIVER_STATUS, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'mobile']
        indexes = [
            models.Index(fields=['company', 'driver_name']),
        ]
        ordering = ['driver_name']

    def __str__(self):
        return self.driver_name

class Bill(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bills')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='bills') 
    bill_number = models.CharField(max_length=10, unique=True, editable=False, db_index=True)
    party = models.ForeignKey('Party', on_delete=models.SET_NULL, related_name='bills', verbose_name="Party Name", null=True, blank=True)
    driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills', verbose_name="Driver")
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='bills', verbose_name="Vehicle")
    reference = models.ForeignKey('VehicleOwner', on_delete=models.SET_NULL, null=True, blank=True, related_name='referenced_bills', verbose_name="Referenced By")
    
    from_location = models.CharField(max_length=255, verbose_name="From Location")
    to_location = models.CharField(max_length=255, verbose_name="To Location")
    material_type = models.CharField(max_length=255, null=True, blank=True, verbose_name="Type of Material")
    rent_amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Rent Amount")
    advance_amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Advance Amount")
    pending_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Pending Amount")
    commission = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission")
    commission_charge = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission Amount")
    commission_received = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission Received")
    commission_pending = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, default=0, verbose_name="Commission Pending")
    
    notes = models.TextField(null=True, blank=True, verbose_name="Additional Notes")
    bill_date = models.DateField(verbose_name="Bill Date")
    commission_received_date = models.DateField(null=True, blank=True, verbose_name="Commission Received Date")
 
    class Meta: 
        ordering = ['-bill_date']
        indexes = [
            models.Index(fields=['company', 'bill_date']),
            models.Index(fields=['branch', 'bill_date']),
        ]

    def clean(self):
        """Enhanced validation with company/branch consistency"""
        errors = {}
        
        # Validate company consistency
        related_objects = [
            (self.party, 'party'),
            (self.driver, 'driver'),
            (self.vehicle, 'vehicle'),
            (self.reference, 'reference'),
        ]
        
        for obj, field_name in related_objects:
            if obj and obj.company != self.company:
                errors[field_name] = f"{field_name.capitalize()} must belong to the same company"
        
        # Validate branch consistency if provided
        if self.branch and self.branch.company != self.company:
            errors['branch'] = "Branch must belong to the same company"
            
        if self.branch:
            for obj, field_name in related_objects:
                if obj and obj.branch and obj.branch != self.branch:
                    errors[field_name] = f"{field_name.capitalize()} branch must match bill branch"

        # Validate amount calculations
        if self.pending_amount != (self.rent_amount - self.advance_amount):
            errors['pending_amount'] = "Pending amount must be Rent minus Advance"
            
        if self.commission_pending != (self.commission_charge - self.commission_received):
            errors['commission_pending'] = "Commission pending must be Commission charge minus Commission received"

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.bill_number:
            last_bill = Bill.objects.filter(company=self.company).order_by('-id').first()
            if last_bill and last_bill.bill_number:
                try:
                    last_number = int(last_bill.bill_number)
                    self.bill_number = str(last_number + 1).zfill(5)
                except ValueError:
                    self.bill_number = '00001'
            else:
                self.bill_number = '00001'
        
        # Auto-calculate amounts
        self.pending_amount = self.rent_amount - self.advance_amount
        if self.commission_charge:
            self.commission_pending = self.commission_charge - (self.commission_received or 0)
            
        super().save(*args, **kwargs)


    @property
    def is_fully_paid(self):
        """Check if bill is fully paid"""
        return self.pending_amount <= 0
    
    @property
    def commission_fully_received(self):
        """Check if commission is fully received"""
        return self.commission_pending <= 0
    
    def __str__(self):
        return f"Bill #{self.bill_number} - {self.company.company_name}"

# Keep your other models (SubscriptionPlan, CompanySubscription, Payment, AuditLog) as they are
# Just update any references from Business to Branch


class SubscriptionPlan(models.Model):
    """Predefined subscription plans"""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    max_users = models.PositiveIntegerField()
    max_vehicles = models.PositiveIntegerField()
    features = models.JSONField(default=dict)  # Store features as JSON
    is_active = models.BooleanField(default=True)
    max_branches = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CompanySubscription(models.Model):
    """Track company subscriptions"""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.company_name} - {self.plan.name}"


class Payment(models.Model):
    """Payment records for subscriptions"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(CompanySubscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, choices=[
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('bank_transfer', 'Bank Transfer')
    ])
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ], default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company.company_name} - {self.amount}"


class AuditLog(models.Model):
    """Audit logs for important actions"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action}"



class Trip(models.Model):
    """Track individual trips for vehicles"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='trips')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='trips')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, null=True, blank=True, related_name='trips')
    
    trip_number = models.CharField(max_length=15, unique=True, editable=False)
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fuel_consumed = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='scheduled')
    
    notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['company', 'start_date']),
            models.Index(fields=['vehicle', 'start_date']),
            models.Index(fields=['status', 'start_date']),  # Add this
        ]
    
 
    def save(self, *args, **kwargs):
        if not self.trip_number:
            last_trip = Trip.objects.filter(company=self.company).order_by('-id').first()
            if last_trip and last_trip.trip_number:
                try:
                    # Extract number from format "TRIP-ABC123-000001"
                    last_number = int(last_trip.trip_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.trip_number = f"TRIP-{self.company.company_code}-{new_number:06d}"
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.trip_number} - {self.vehicle.vehicle_number}"



def expense_receipt_path(instance, filename):
    return f'company_{instance.company.id}/expense_receipts/{filename}'

class Expense(models.Model):
    """Track vehicle and operational expenses"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='expenses')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='expenses')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True, related_name='expenses')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, null=True, blank=True, related_name='expenses')
    receipt_image = models.ImageField(upload_to=expense_receipt_path, null=True, blank=True)
    
    EXPENSE_CATEGORIES = [
        ('fuel', 'Fuel'),
        ('maintenance', 'Maintenance'),
        ('repair', 'Repair'),
        ('toll', 'Toll'),
        ('driver_allowance', 'Driver Allowance'),
        ('other', 'Other'),
    ]
    
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    expense_date = models.DateField()
    receipt_number = models.CharField(max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date']
        indexes = [
            models.Index(fields=['company', 'expense_date']),
            models.Index(fields=['vehicle', 'expense_date']),
            models.Index(fields=['category', 'expense_date']),  # Add this
        ]

    def __str__(self):
        return f"{self.category} - {self.amount} - {self.expense_date}"
    













from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Company)
def create_company_settings(sender, instance, created, **kwargs):
    if created:
        CompanySettings.objects.get_or_create(company=instance)

@receiver(post_save, sender=Company)
def save_company_settings(sender, instance, **kwargs):
    instance.settings.save()


@receiver(post_save, sender=Company)
def create_company_settings(sender, instance, created, **kwargs):
    """Automatically create CompanySettings when a new Company is created"""
    if created:
        CompanySettings.objects.get_or_create(company=instance)

@receiver(post_save, sender=Company)
def save_company_settings(sender, instance, **kwargs):
    """Save CompanySettings when Company is saved"""
    if hasattr(instance, 'settings'):
        instance.settings.save()
