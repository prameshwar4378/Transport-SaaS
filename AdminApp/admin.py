# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import *

from django import forms


from django import forms
from django.contrib import admin


from import_export import resources
from import_export.admin import ExportMixin, ExportActionModelAdmin
from import_export.formats import base_formats
from django.http import HttpResponse
import csv
import xlwt
from datetime import datetime
 

class BusinessAwareAdmin(admin.ModelAdmin):
    """Base admin class for all business-related models with Jazzmin support"""
    
    # Jazzmin settings
    list_per_page = 25
    show_full_result_count = True
    
    def get_list_display(self, request):
        list_display = super().get_list_display(request) or []
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return ('business',) + tuple(list_display)
        return list_display
    
    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request) or []
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return ('business', 'created_at') + tuple(list_filter)
        return tuple(list_filter) + ('created_at',) if list_filter else ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return qs
        elif hasattr(request.user, 'business') and request.user.business:
            return qs.filter(business=request.user.business)
        return qs.none()
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj) or ()
        
        # For non-admin users, make business field read-only when editing existing objects
        if (not hasattr(request.user, 'is_system_admin') or 
            not request.user.is_system_admin) and obj and hasattr(obj, 'business'):
            return ('business',) + tuple(readonly_fields)
        return readonly_fields
    
    def get_exclude(self, request, obj=None):
        exclude = super().get_exclude(request, obj) or ()
        
        # For non-admin users, hide business field from form entirely
        if not hasattr(request.user, 'is_system_admin') or not request.user.is_system_admin:
            # Check if model has business field
            field_names = [f.name for f in self.model._meta.get_fields()]
            if 'business' in field_names:
                return ('business',) + tuple(exclude)
        return exclude
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # For non-admin users, handle business field logic
        if not (hasattr(request.user, 'is_system_admin') and request.user.is_system_admin):
            if 'business' in form.base_fields:
                # Limit business choices to user's business only
                if hasattr(request.user, 'business') and request.user.business:
                    form.base_fields['business'].queryset = Business.objects.filter(
                        pk=request.user.business.pk
                    )
                
                # For new objects: pre-populate and hide the field
                if not obj:
                    if hasattr(request.user, 'business') and request.user.business:
                        form.base_fields['business'].initial = request.user.business
                    form.base_fields['business'].widget = forms.HiddenInput()
                # For existing objects: make it read-only
                else:
                    form.base_fields['business'].disabled = True
                    form.base_fields['business'].widget.can_add_related = False
                    form.base_fields['business'].widget.can_change_related = False
                    form.base_fields['business'].widget.can_delete_related = False
                    form.base_fields['business'].widget.can_view_related = False
        
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Further restrict business choices for non-admin users
        if db_field.name == "business":
            if not (hasattr(request.user, 'is_system_admin') and request.user.is_system_admin):
                if hasattr(request.user, 'business') and request.user.business:
                    kwargs["queryset"] = Business.objects.filter(pk=request.user.business.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """
        SIMPLE & BULLETPROOF business auto-setting with debugging
        """
        # FORCE SET BUSINESS for new objects
        if not change:
            if hasattr(request.user, 'business') and request.user.business:
                obj.business = request.user.business
        
        # Call parent save
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        """
        Business owners can add records to all models EXCEPT Business model
        """
        # System admins have all permissions
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return True
        
        # Business owners cannot add Business records
        if self.model.__name__ == 'Business' and hasattr(request.user, 'is_business_owner') and request.user.is_business_owner:
            return False
        
        # Business owners can add records if they have a business
        if hasattr(request.user, 'business') and request.user.business:
            return True
        
        return False
    
    def has_change_permission(self, request, obj=None):
        """
        Business owners can change records in all models EXCEPT Business model
        """
        # System admins have all permissions
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return True
        
        # Business owners cannot change Business records
        if self.model.__name__ == 'Business' and hasattr(request.user, 'is_business_owner') and request.user.is_business_owner:
            return False
        
        # For business-related models, check if object belongs to user's business
        if obj and hasattr(obj, 'business') and hasattr(request.user, 'business'):
            return obj.business == request.user.business
        
        # Business owners have change permission for their business data
        if hasattr(request.user, 'business') and request.user.business:
            return True
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Business owners can delete records in all models EXCEPT Business model
        """
        # System admins have all permissions
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return True
        
        # Business owners cannot delete Business records
        if self.model.__name__ == 'Business' and hasattr(request.user, 'is_business_owner') and request.user.is_business_owner:
            return False
        
        # For business-related models, check if object belongs to user's business
        if obj and hasattr(obj, 'business') and hasattr(request.user, 'business'):
            return obj.business == request.user.business
        
        # Business owners have delete permission for their business data
        if hasattr(request.user, 'business') and request.user.business:
            return True
        
        return False
    
    def has_view_permission(self, request, obj=None):
        """
        Business owners can view records in all models EXCEPT other Business records
        """
        # System admins have all permissions
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return True
        
        # Business owners can only view their own business record
        if self.model.__name__ == 'Business':
            if obj and hasattr(request.user, 'business') and request.user.business:
                return obj == request.user.business
            return False
        
        # For other models, check business ownership
        if obj and hasattr(obj, 'business') and hasattr(request.user, 'business'):
            return obj.business == request.user.business
        
        # Business owners can view lists of their business data
        if hasattr(request.user, 'business') and request.user.business:
            return True
        
        return False
    
    def has_module_permission(self, request):
        """
        Control access to the app module in admin
        """
        # System admins have all permissions
        if hasattr(request.user, 'is_system_admin') and request.user.is_system_admin:
            return True
        
        # Business owners can access all modules
        if hasattr(request.user, 'is_business_owner') and request.user.is_business_owner:
            return True
        
        # Staff members can access the module
        if hasattr(request.user, 'is_staff_member') and request.user.is_staff_member:
            return True
        
        return False
    # Create Resource class for Bill model
class BillResource(resources.ModelResource):
    party_name = resources.Field()
    vehicle_number = resources.Field()
    driver_name = resources.Field()
    reference_name = resources.Field()
    payment_status = resources.Field()
    commission_status = resources.Field()
    business_name = resources.Field()
    
    class Meta:
        model = Bill
        fields = (
            'bill_number',
            'bill_date',
            'party_name',
            'vehicle_number', 
            'driver_name',
            'reference_name',
            'from_location',
            'to_location',
            'material_type',
            'rent_amount',
            'advance_amount',
            'pending_amount',
            'commission',
            'commission_charge',
            'commission_received',
            'commission_pending',
            'commission_received_date',
            'payment_status',
            'commission_status',
            'business_name',
            'notes',
            'created_at',
        )
        export_order = fields
    
    def dehydrate_party_name(self, bill):
        return bill.party.name if bill.party else "No Party"
    
    def dehydrate_vehicle_number(self, bill):
        return bill.vehicle.vehicle_number if bill.vehicle else "No Vehicle"
    
    def dehydrate_driver_name(self, bill):
        return bill.driver.driver_name if bill.driver else "No Driver"
    
    def dehydrate_reference_name(self, bill):
        return bill.reference.owner_name if bill.reference else "No Reference"
    
    def dehydrate_payment_status(self, bill):
        return bill.payment_status
    
    def dehydrate_commission_status(self, bill):
        return bill.commission_status
    
    def dehydrate_business_name(self, bill):
        return bill.business.business_name if bill.business else "No Business"

# Create Resource class for VehicleOwner
class VehicleOwnerResource(resources.ModelResource):
    business_name = resources.Field()
    total_vehicles_count = resources.Field()
    
    class Meta:
        model = VehicleOwner
        fields = (
            'owner_name',
            'owner_mobile_number',
            'owner_alternate_mobile_number',
            'business_name',
            'total_vehicles_count',
            'created_at',
            'updated_at',
        )
        export_order = fields
    
    def dehydrate_business_name(self, vehicle_owner):
        return vehicle_owner.business.business_name if vehicle_owner.business else "No Business"
    
    def dehydrate_total_vehicles_count(self, vehicle_owner):
        return vehicle_owner.total_vehicles

# Create Resource class for Vehicle
class VehicleResource(resources.ModelResource):
    owner_name = resources.Field()
    owner_mobile = resources.Field()
    business_name = resources.Field()
    total_bills_count = resources.Field()
    
    class Meta:
        model = Vehicle
        fields = (
            'vehicle_number',
            'vehicle_name',
            'model_name',
            'owner_name',
            'owner_mobile',
            'business_name',
            'total_bills_count',
            'notes',
            'created_at',
            'updated_at',
        )
        export_order = fields
    
    def dehydrate_owner_name(self, vehicle):
        return vehicle.owner.owner_name if vehicle.owner else "No Owner"
    
    def dehydrate_owner_mobile(self, vehicle):
        return vehicle.owner.owner_mobile_number if vehicle.owner else "No Mobile"
    
    def dehydrate_business_name(self, vehicle):
        return vehicle.business.business_name if vehicle.business else "No Business"
    
    def dehydrate_total_bills_count(self, vehicle):
        return vehicle.total_bills

# Create Resource class for Party
class PartyResource(resources.ModelResource):
    business_name = resources.Field()
    total_bills_count = resources.Field()
    total_amount = resources.Field()
    
    class Meta:
        model = Party
        fields = (
            'name',
            'gst_no',
            'mobile',
            'alternate_mobile',
            'business_name',
            'total_bills_count',
            'total_amount',
            'created_at',
            'updated_at',
        )
        export_order = fields
    
    def dehydrate_business_name(self, party):
        return party.business.business_name if party.business else "No Business"
    
    def dehydrate_total_bills_count(self, party):
        return party.total_bills
    
    def dehydrate_total_amount(self, party):
        from django.db.models import Sum
        total = party.bills.aggregate(Sum('rent_amount'))['rent_amount__sum'] or 0
        return total

# Create Resource class for Driver
class DriverResource(resources.ModelResource):
    business_name = resources.Field()
    total_bills_count = resources.Field()
    total_trip_amount = resources.Field()
    
    class Meta:
        model = Driver
        fields = (
            'driver_name',
            'mobile',
            'alternate_mobile',
            'business_name',
            'total_bills_count',
            'total_trip_amount',
            'created_at',
            'updated_at',
        )
        export_order = fields
    
    def dehydrate_business_name(self, driver):
        return driver.business.business_name if driver.business else "No Business"
    
    def dehydrate_total_bills_count(self, driver):
        return driver.total_bills
    
    def dehydrate_total_trip_amount(self, driver):
        from django.db.models import Sum
        total = driver.bills.aggregate(Sum('rent_amount'))['rent_amount__sum'] or 0
        return total
       


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role_display', 'business_display', 'is_active', 'is_superuser', 'last_login')
    list_filter = ('role', 'business', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'business__business_name')
    ordering = ('-date_joined',)
    readonly_fields = ('last_login', 'date_joined', 'role_display', 'user_type_display')
    
    # Fieldsets for edit form
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture')}),
        ('Role & Business', {'fields': ('role', 'role_display', 'user_type_display', 'business', 'is_active_staff')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Fieldsets for add form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'business', 'is_superuser'),
        }),
    )
    
    def role_display(self, obj):
        return "Superuser" if obj.is_superuser else obj.get_role_display()
    role_display.short_description = 'Role'
    
    def user_type_display(self, obj):
        return "Superuser (All Access)" if obj.is_superuser else "Regular User"
    user_type_display.short_description = 'User Type'
    
    def business_display(self, obj):
        return obj.business.business_name if obj.business else "No Business"
    business_display.short_description = 'Business'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request.user, 'is_superuser') and request.user.is_superuser:
            return qs
        elif hasattr(request.user, 'is_business_owner') and request.user.is_business_owner:
            return qs.filter(business=request.user.business)
        else:
            return qs.filter(pk=request.user.pk)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        if not (hasattr(request.user, 'is_superuser') and request.user.is_superuser):
            # Non-superusers cannot change superuser status or role for superusers
            if 'is_superuser' in form.base_fields:
                form.base_fields['is_superuser'].disabled = True
            if 'role' in form.base_fields and obj and obj.is_superuser:
                form.base_fields['role'].disabled = True
            if 'business' in form.base_fields:
                form.base_fields['business'].disabled = True
            if 'groups' in form.base_fields:
                form.base_fields['groups'].disabled = True
            if 'user_permissions' in form.base_fields:
                form.base_fields['user_permissions'].disabled = True
                
        return form
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new user
            if (hasattr(request.user, 'is_business_owner') and 
                request.user.is_business_owner and 
                not (hasattr(request.user, 'is_superuser') and request.user.is_superuser)):
                # Business owners can only create staff users
                obj.role = 'staff'
                obj.business = request.user.business
                obj.is_staff = True
        
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete other superusers
        if obj and obj.is_superuser:
            return hasattr(request.user, 'is_superuser') and request.user.is_superuser
        return super().has_delete_permission(request, obj)
    
    # Add safe permission methods for AnonymousUser
    def has_add_permission(self, request):
        if hasattr(request.user, 'is_superuser') and request.user.is_superuser:
            return True
        if hasattr(request.user, 'is_business_owner') and request.user.is_business_owner:
            return True
        return False
    
    def has_change_permission(self, request, obj=None):
        if hasattr(request.user, 'is_superuser') and request.user.is_superuser:
            return True
        if obj and hasattr(request.user, 'business'):
            return obj.business == request.user.business
        if obj:
            return obj == request.user
        return True
    

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        'business_name', 
        'business_label', 
        'mobile_number', 
        'status_badge', 
        'total_staff_display', 
        'total_vehicles_display',
        'created_at'
    )
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('business_name', 'business_label', 'mobile_number', 'email', 'business_number')
    readonly_fields = (
        'total_staff_display', 
        'total_vehicles_display', 
        'total_bills_display',
        'created_at',
        'updated_at',
        'logo_preview'
    )
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'business_name', 
                'business_label', 
                'mobile_number', 
                'alternate_mobile_number'
            )
        }),
        ('Contact Details', {
            'fields': ('email', 'address', 'business_number')
        }),
        ('Business Media', {
            'fields': ('business_logo', 'logo_preview', 'business_photo1')
        }),
        ('Settings & Limits', {
            'fields': ('status', 'max_staff_users', 'max_vehicles')
        }),
        ('Statistics', {
            'fields': ('total_staff_display', 'total_vehicles_display', 'total_bills_display')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'active': 'success',
            'suspended': 'warning',
            'inactive': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def total_staff_display(self, obj):
        return f"{obj.total_staff_users} / {obj.max_staff_users}"
    total_staff_display.short_description = 'Staff Users'
    
    def total_vehicles_display(self, obj):
        return f"{obj.total_vehicles} / {obj.max_vehicles}"
    total_vehicles_display.short_description = 'Vehicles'
    
    def total_bills_display(self, obj):
        return obj.total_bills
    total_bills_display.short_description = 'Total Bills'
    
    def logo_preview(self, obj):
        if obj.business_logo:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 8px; border: 1px solid #ddd;" />',
                obj.business_logo.url
            )
        return "No Logo"
    logo_preview.short_description = 'Logo Preview'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_system_admin:
            return qs
        elif hasattr(request.user, 'business') and request.user.business:
            # Business owners can only see their own business
            return qs.filter(pk=request.user.business.pk)
        else:
            return qs.none()
    
    def has_add_permission(self, request):
        # Only system admins can create businesses
        return request.user.is_system_admin
    
    def has_change_permission(self, request, obj=None):
        # System admins can change any business
        if request.user.is_system_admin:
            return True
        
        # Business owners can only change their own business
        if obj and hasattr(request.user, 'business') and request.user.business:
            return obj == request.user.business
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only system admins can delete businesses
        return request.user.is_system_admin
    
    def has_view_permission(self, request, obj=None):
        # System admins can view all businesses
        if request.user.is_system_admin:
            return True
        
        # Business owners can only view their own business
        if obj and hasattr(request.user, 'business') and request.user.business:
            return obj == request.user.business
        
        # Allow business owners to see the business list (but only their business will appear)
        if hasattr(request.user, 'business') and request.user.business:
            return True
        
        return False
    




from django import forms

# class VehicleOwnerForm(forms.ModelForm):
#     class Meta:
#         model = VehicleOwner
#         fields = '__all__'
    
#     def __init__(self, *args, **kwargs):
#         self.request = kwargs.pop('request', None)
#         super().__init__(*args, **kwargs)
    
#     def clean(self):
#         cleaned_data = super().clean()
#         mobile_number = cleaned_data.get('owner_mobile_number')
        
#         # Only validate if we have mobile number and request context
#         if (mobile_number and 
#             self.request and 
#             hasattr(self.request.user, 'business') and 
#             self.request.user.business):
            
#             queryset = VehicleOwner.objects.filter(
#                 business=self.request.user.business,
#                 owner_mobile_number=mobile_number
#             )
            
#             # Exclude current instance when editing
#             if self.instance and self.instance.pk:
#                 queryset = queryset.exclude(pk=self.instance.pk)
            
#             if queryset.exists():
#                 raise forms.ValidationError({
#                     'owner_mobile_number': f'Mobile number {mobile_number} is already registered with another owner in your business.'
#                 })
        
#         return cleaned_data


class VehicleOwnerForm(forms.ModelForm):
    class Meta:
        model = VehicleOwner
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        mobile_number = cleaned_data.get('owner_mobile_number')
        
        # Only validate if we have mobile number and request context
        if (mobile_number and 
            self.request and 
            hasattr(self.request.user, 'business') and 
            self.request.user.business):
            
            queryset = VehicleOwner.objects.filter(
                business=self.request.user.business,
                owner_mobile_number=mobile_number
            )
            
            # Exclude current instance when editing
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError({
                    'owner_mobile_number': f'Mobile number {mobile_number} is already registered with another owner in your business.'
                })
        
        return cleaned_data    
    

@admin.register(VehicleOwner)
class VehicleOwnerAdmin(ExportMixin, BusinessAwareAdmin):
    resource_class = VehicleOwnerResource
    formats = [base_formats.XLSX, base_formats.CSV]
    
    list_display = (
        'owner_name', 
        'owner_mobile_number', 
        'owner_alternate_mobile_number', 
        'photo_preview', 
        'total_vehicles_badge',
        'created_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('owner_name', 'owner_mobile_number', 'owner_alternate_mobile_number')
    readonly_fields = ('photo_preview', 'total_vehicles_badge', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    # Override changelist to add custom export buttons
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_buttons'] = [
            {
                'label': '📤 Export Excel',
                'url': f'{request.path}export/?format=xlsx',
                'class': 'export-link',
            },
            {
                'label': '📤 Export CSV', 
                'url': f'{request.path}export/?format=csv',
                'class': 'export-link',
            },
        ]
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'owner_name', 
                'owner_mobile_number', 
                'owner_alternate_mobile_number', 
                'owner_photo', 
                'photo_preview'
            )
        }),
        ('Documents', {
            'fields': ('pan_card', 'adhar_card', 'document1', 'document2'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_vehicles_badge',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def photo_preview(self, obj):
        if obj.owner_photo:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius: 50%; border: 2px solid #ddd;" />',
                obj.owner_photo.url
            )
        return format_html(
            '<div style="width: 60px; height: 60px; border-radius: 50%; background: #f8f9fa; border: 2px dashed #dee2e6; display: flex; align-items: center; justify-content: center; color: #6c757d;">No Photo</div>'
        )
    photo_preview.short_description = 'Photo'
    
    def total_vehicles_badge(self, obj):
        count = obj.total_vehicles
        color = 'success' if count > 0 else 'secondary'
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            f"{count} Vehicle{'s' if count != 1 else ''}"
        )
    total_vehicles_badge.short_description = 'Total Vehicles'

    def get_form(self, request, obj=None, **kwargs):
        """Inject request into the form"""
        kwargs['form'] = VehicleOwnerForm
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form
    








# admin.py - VehicleAdmin
class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        # Extract request before calling super
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Limit owner choices to current business
        if self.request and hasattr(self.request.user, 'business') and self.request.user.business:
            self.fields['owner'].queryset = VehicleOwner.objects.filter(
                business=self.request.user.business
            )
    
    def clean(self):
        cleaned_data = super().clean()
        vehicle_number = cleaned_data.get('vehicle_number')
        owner = cleaned_data.get('owner')
        business = cleaned_data.get('business')
        
        # SAFE way to get business from request
        if not business and self.request and hasattr(self.request.user, 'business') and self.request.user.business:
            business = self.request.user.business
            cleaned_data['business'] = business
        
        # Validate vehicle number uniqueness
        if vehicle_number:
            vehicle_number = vehicle_number.upper().replace(' ', '')
            cleaned_data['vehicle_number'] = vehicle_number
            
            # Global uniqueness check
            queryset = Vehicle.objects.filter(vehicle_number=vehicle_number)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                self.add_error('vehicle_number', 
                    f'Vehicle with number {vehicle_number} already exists.')
            
            # Business-level uniqueness check (only if we have business)
            if business:
                business_queryset = Vehicle.objects.filter(
                    business=business, 
                    vehicle_number=vehicle_number
                )
                if self.instance and self.instance.pk:
                    business_queryset = business_queryset.exclude(pk=self.instance.pk)
                
                if business_queryset.exists():
                    self.add_error('vehicle_number',
                        f'Vehicle number {vehicle_number} is already registered in your business.')
        
        # Validate owner-business consistency (only if we have both)
        if owner and business:
            if owner.business != business:
                self.add_error('owner',
                    f'Selected owner belongs to {owner.business.business_name}, but vehicle is for {business.business_name}.')
        
        return cleaned_data
    






@admin.register(Vehicle)
class VehicleAdmin(ExportMixin, BusinessAwareAdmin):
    resource_class = VehicleResource
    formats = [base_formats.XLSX, base_formats.CSV]
    
    list_display = (
        'vehicle_number', 
        'vehicle_name', 
        'model_name', 
        'owner_link', 
        'photo_preview', 
        'total_bills_badge',
        'created_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('vehicle_number', 'vehicle_name', 'model_name', 'owner__owner_name')
    readonly_fields = ('photo_preview', 'owner_info', 'total_bills_badge', 'created_at', 'updated_at')
    list_select_related = ('owner', 'business')
    date_hierarchy = 'created_at'
    
    # Override changelist to add custom export buttons
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_buttons'] = [
            {
                'label': '📤 Export Excel',
                'url': f'{request.path}export/?format=xlsx',
                'class': 'export-link',
            },
            {
                'label': '📤 Export CSV', 
                'url': f'{request.path}export/?format=csv',
                'class': 'export-link',
            },
        ]
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ('Vehicle Information', {
            'fields': ('vehicle_number', 'vehicle_name', 'model_name', 'owner')
        }),
        ('Media & Documents', {
            'fields': ('vehicle_photo1', 'vehicle_photo2', 'photo_preview', 'document1', 'document2')
        }),
        ('Additional Information', {
            'fields': ('notes', 'owner_info')
        }),
        ('Statistics', {
            'fields': ('total_bills_badge',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def photo_preview(self, obj):
        if obj.vehicle_photo1:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius: 8px; border: 2px solid #ddd;" />',
                obj.vehicle_photo1.url
            )
        return format_html(
            '<div style="width: 60px; height: 60px; border-radius: 8px; background: #f8f9fa; border: 2px dashed #dee2e6; display: flex; align-items: center; justify-content: center; color: #6c757d;">No Photo</div>'
        )
    photo_preview.short_description = 'Photo'
    
    def owner_link(self, obj):
        if obj.owner:
            url = f"/admin/AdminApp/vehicleowner/{obj.owner.id}/change/"
            return format_html(
                '<a href="{}" style="color: #007bff; text-decoration: none;">{}</a>',
                url,
                obj.owner.owner_name
            )
        return "No Owner"
    owner_link.short_description = 'Owner'

    def owner_info(self, obj):
        if obj.owner:
            return f"{obj.owner.owner_name} - {obj.owner.owner_mobile_number}"
        return "No Owner"
    owner_info.short_description = 'Owner Information'
    
    def total_bills_badge(self, obj):
        count = obj.total_bills
        color = 'success' if count > 0 else 'secondary'
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            f"{count} Bill{'s' if count != 1 else ''}"
        )
    total_bills_badge.short_description = 'Total Bills'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('owner', 'business')
    
    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = VehicleForm
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # Pass request to form
        return form
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Further restrict owner choices to user's business
        if db_field.name == "owner":
            if hasattr(request.user, 'business') and request.user.business:
                kwargs["queryset"] = VehicleOwner.objects.filter(business=request.user.business)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
            


class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = '__all__'
    
    
    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        gst_no = cleaned_data.get('gst_no')
        mobile = cleaned_data.get('mobile')
        alternate_mobile = cleaned_data.get('alternate_mobile')
        business = cleaned_data.get('business')
        
        # If business not in form data, get from request
        if not business and self.request and hasattr(self.request.user, 'business') and self.request.user.business:
            business = self.request.user.business
            cleaned_data['business'] = business
        
        # Validate name uniqueness
        if name and business:
            queryset = Party.objects.filter(business=business, name=name)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                self.add_error('name', 
                    f'Party with name "{name}" already exists in your business.')
        
        # Validate GST uniqueness
        if gst_no:
            gst_no = gst_no.strip().upper()
            queryset = Party.objects.filter(gst_no=gst_no)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                self.add_error('gst_no',
                    f'GST number {gst_no} is already registered with another party.')
        
        # Validate mobile conflicts
        if mobile and business:
            primary_queryset = Party.objects.filter(business=business, mobile=mobile)
            alternate_queryset = Party.objects.filter(business=business, alternate_mobile=mobile)
            
            if self.instance and self.instance.pk:
                primary_queryset = primary_queryset.exclude(pk=self.instance.pk)
                alternate_queryset = alternate_queryset.exclude(pk=self.instance.pk)
            
            if primary_queryset.exists():
                self.add_error('mobile',
                    f'Mobile {mobile} is already registered as primary mobile for another party.')
            elif alternate_queryset.exists():
                self.add_error('mobile',
                    f'Mobile {mobile} is already registered as alternate mobile for another party.')
        
        # Validate alternate mobile conflicts
        if alternate_mobile and business:
            primary_queryset = Party.objects.filter(business=business, mobile=alternate_mobile)
            alternate_queryset = Party.objects.filter(business=business, alternate_mobile=alternate_mobile)
            
            if self.instance and self.instance.pk:
                primary_queryset = primary_queryset.exclude(pk=self.instance.pk)
                alternate_queryset = alternate_queryset.exclude(pk=self.instance.pk)
            
            if primary_queryset.exists():
                self.add_error('alternate_mobile',
                    f'This mobile is already registered as primary mobile for another party.')
            elif alternate_queryset.exists():
                self.add_error('alternate_mobile',
                    f'This mobile is already registered as alternate mobile for another party.')
        
        # Validate mobile and alternate_mobile are not same
        if mobile and alternate_mobile and mobile == alternate_mobile:
            self.add_error('alternate_mobile',
                'Alternate mobile cannot be same as primary mobile.')
        
        return cleaned_data
    



# from django.db import IntegrityError
#  # admin.py - PartyForm with database error handling
# # admin.py - PartyForm with proper validation stopping
# class PartyForm(forms.ModelForm):
#     class Meta:
#         model = Party
#         fields = '__all__'
    
#     def __init__(self, *args, **kwargs):
#         self.request = kwargs.pop('request', None)
#         super().__init__(*args, **kwargs)
    
#     def clean(self):
#         cleaned_data = super().clean()
#         name = cleaned_data.get('name')
#         gst_no = cleaned_data.get('gst_no')
#         mobile = cleaned_data.get('mobile')
#         alternate_mobile = cleaned_data.get('alternate_mobile')
#         business = cleaned_data.get('business')
        
#         # If business not in form data, get from request
#         if not business and self.request and hasattr(self.request.user, 'business') and self.request.user.business:
#             business = self.request.user.business
#             cleaned_data['business'] = business
        
#         # Validate name uniqueness
#         if name and business:
#             queryset = Party.objects.filter(business=business, name=name)
#             if self.instance and self.instance.pk:
#                 queryset = queryset.exclude(pk=self.instance.pk)
#             if queryset.exists():
#                 self.add_error('name', 
#                     f'Party with name "{name}" already exists in your business.')
        
#         # Validate GST uniqueness
#         if gst_no:
#             gst_no = gst_no.strip().upper()
#             queryset = Party.objects.filter(gst_no=gst_no)
#             if self.instance and self.instance.pk:
#                 queryset = queryset.exclude(pk=self.instance.pk)
#             if queryset.exists():
#                 self.add_error('gst_no',
#                     f'GST number {gst_no} is already registered with another party.')
        
#         # Validate mobile conflicts
#         if mobile and business:
#             primary_queryset = Party.objects.filter(business=business, mobile=mobile)
#             alternate_queryset = Party.objects.filter(business=business, alternate_mobile=mobile)
            
#             if self.instance and self.instance.pk:
#                 primary_queryset = primary_queryset.exclude(pk=self.instance.pk)
#                 alternate_queryset = alternate_queryset.exclude(pk=self.instance.pk)
            
#             if primary_queryset.exists():
#                 self.add_error('mobile',
#                     f'Mobile {mobile} is already registered as primary mobile for another party.')
#             elif alternate_queryset.exists():
#                 self.add_error('mobile',
#                     f'Mobile {mobile} is already registered as alternate mobile for another party.')
        
#         # Validate alternate mobile conflicts
#         if alternate_mobile and business:
#             primary_queryset = Party.objects.filter(business=business, mobile=alternate_mobile)
#             alternate_queryset = Party.objects.filter(business=business, alternate_mobile=alternate_mobile)
            
#             if self.instance and self.instance.pk:
#                 primary_queryset = primary_queryset.exclude(pk=self.instance.pk)
#                 alternate_queryset = alternate_queryset.exclude(pk=self.instance.pk)
            
#             if primary_queryset.exists():
#                 self.add_error('alternate_mobile',
#                     f'This mobile is already registered as primary mobile for another party.')
#             elif alternate_queryset.exists():
#                 self.add_error('alternate_mobile',
#                     f'This mobile is already registered as alternate mobile for another party.')
        
#         # Validate mobile and alternate_mobile are not same
#         if mobile and alternate_mobile and mobile == alternate_mobile:
#             self.add_error('alternate_mobile',
#                 'Alternate mobile cannot be same as primary mobile.')
        
#         return cleaned_data
    




@admin.register(Party)
class PartyAdmin(ExportMixin, BusinessAwareAdmin):
    resource_class = PartyResource
    formats = [base_formats.XLSX, base_formats.CSV]
    
    list_display = (
        'name', 
        'gst_no_formatted', 
        'mobile_display', 
        'photo_preview', 
        'total_bills_badge',
        'created_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'gst_no', 'mobile', 'alternate_mobile', 'business__business_name')
    readonly_fields = ('photo_preview', 'total_bills_badge', 'created_at', 'updated_at')
    list_select_related = ('business',)
    date_hierarchy = 'created_at'
    
    # Override changelist to add custom export buttons
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_buttons'] = [
            {
                'label': '📤 Export Excel',
                'url': f'{request.path}export/?format=xlsx',
                'class': 'export-link',
            },
            {
                'label': '📤 Export CSV', 
                'url': f'{request.path}export/?format=csv',
                'class': 'export-link',
            },
        ]
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ('Party Information', {
            'fields': ('name', 'gst_no', 'mobile', 'alternate_mobile', 'party_photo', 'photo_preview')
        }),
        ('Documents', {
            'fields': ('pan_card', 'adhar_card', 'document1', 'document2'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_bills_badge',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def gst_no_formatted(self, obj):
        if obj.gst_no:
            return format_html(
                '<code style="background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-family: monospace;">{}</code>',
                obj.gst_no
            )
        return "No GST"
    gst_no_formatted.short_description = 'GST Number'
    
    def mobile_display(self, obj):
        if obj.mobile:
            return format_html(
                '<span style="font-family: monospace;">{}</span>',
                obj.mobile
            )
        return "No Mobile"
    mobile_display.short_description = 'Mobile'
    
    def photo_preview(self, obj):
        if obj.party_photo:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius: 50%; border: 2px solid #ddd;" />',
                obj.party_photo.url
            )
        return format_html(
            '<div style="width: 60px; height: 60px; border-radius: 50%; background: #f8f9fa; border: 2px dashed #dee2e6; display: flex; align-items: center; justify-content: center; color: #6c757d;">No Photo</div>'
        )
    photo_preview.short_description = 'Photo'
    
    def total_bills_badge(self, obj):
        count = obj.total_bills
        color = 'success' if count > 0 else 'secondary'
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            f"{count} Bill{'s' if count != 1 else ''}"
        )
    total_bills_badge.short_description = 'Total Bills'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('business')

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = PartyForm
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # Pass request to form
        return form
    


    

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        mobile = cleaned_data.get('mobile')
        alternate_mobile = cleaned_data.get('alternate_mobile')
        business = cleaned_data.get('business')
        
        # If business not in form data, get from request
        if not business and hasattr(self, 'request') and self.request.user.business:
            business = self.request.user.business
            cleaned_data['business'] = business
        
        # Validate mobile uniqueness
        if mobile and business:
            queryset = Driver.objects.filter(business=business, mobile=mobile)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                self.add_error('mobile', 
                    f'Driver with mobile {mobile} already exists in your business.')
 
        return cleaned_data
    

@admin.register(Driver)
class DriverAdmin(ExportMixin, BusinessAwareAdmin):
    resource_class = DriverResource
    formats = [base_formats.XLSX, base_formats.CSV]
    
    list_display = (
        'driver_name', 
        'mobile_display', 
        'alternate_mobile_display', 
        'photo_preview', 
        'total_bills_badge',
        'created_at'
    )
    # list_filter = ('created_at', 'updated_at')
    search_fields = ('driver_name', 'mobile', 'alternate_mobile', 'business__business_name')
    readonly_fields = ('photo_preview', 'total_bills_badge', 'created_at', 'updated_at')
    list_select_related = ('business',)
    date_hierarchy = 'created_at'
    
    # Override changelist to add custom export buttons
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_buttons'] = [
            {
                'label': '📤 Export Excel',
                'url': f'{request.path}export/?format=xlsx',
                'class': 'export-link',
            },
            {
                'label': '📤 Export CSV', 
                'url': f'{request.path}export/?format=csv',
                'class': 'export-link',
            },
        ]
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ('Driver Information', {
            'fields': (
                'driver_name', 
                'mobile', 
                'alternate_mobile', 
                'profile_photo', 
                'photo_preview',
                'driver_photo1',
                'driver_photo2'
            )
        }),
        ('Documents', {
            'fields': ('licence', 'adhar_card', 'document1', 'document2'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_bills_badge',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def mobile_display(self, obj):
        if obj.mobile:
            return format_html(
                '<span style="font-family: monospace; font-weight: 500;">{}</span>',
                obj.mobile
            )
        return "No Mobile"
    mobile_display.short_description = 'Mobile'
    
    def alternate_mobile_display(self, obj):
        if obj.alternate_mobile:
            return format_html(
                '<span style="font-family: monospace; color: #6c757d;">{}</span>',
                obj.alternate_mobile
            )
        return "-"
    alternate_mobile_display.short_description = 'Alt Mobile'
    
    def photo_preview(self, obj):
        if obj.profile_photo:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius: 50%; border: 2px solid #ddd;" />',
                obj.profile_photo.url
            )
        return format_html(
            '<div style="width: 60px; height: 60px; border-radius: 50%; background: #f8f9fa; border: 2px dashed #dee2e6; display: flex; align-items: center; justify-content: center; color: #6c757d;">No Photo</div>'
        )
    photo_preview.short_description = 'Profile Photo'
    
    def total_bills_badge(self, obj):
        count = obj.total_bills
        color = 'success' if count > 0 else 'secondary'
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            f"{count} Bill{'s' if count != 1 else ''}"
        )
    total_bills_badge.short_description = 'Total Bills'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('business') 
    
    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = DriverForm
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # Pass request to form
        return form







class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = '__all__'

    _print = forms.BooleanField(
        required=False,
        initial=True,
        label='🖨️ Print after save',
        help_text='Open print preview after saving'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        pending_amount = cleaned_data.get('pending_amount')
        rent_amount = cleaned_data.get('rent_amount')
        advance_amount = cleaned_data.get('advance_amount')
        commission = cleaned_data.get('commission')
        commission_charge = cleaned_data.get('commission_charge')
        commission_pending = cleaned_data.get('commission_pending')
        commission_received = cleaned_data.get('commission_received')
        commission_received_date = cleaned_data.get('commission_received_date')
        business_id = cleaned_data.get('business_id')
        vehicle_id = cleaned_data.get('vehicle_id')

          
        # Validate amounts

        if advance_amount >rent_amount:
            raise ValidationError({'advance_amount': 'Advance amount cannot exceed rent amount.'})
        
        if commission_received > commission_charge:
            raise ValidationError({'commission_received': 'Commission received cannot exceed commission charge.'})
         

        # Validate commission received date
        if commission_received_date and not commission_received:
            raise ValidationError({
                'commission_received_date': 'Commission received date cannot be set without commission received amount.'
            })
        
        # Add any business-specific validations using business_id
        if vehicle_id and business_id:
            # Example: Validate vehicle belongs to the same business
            from .models import Vehicle
            try:
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                if vehicle.business_id != business_id:
                    raise ValidationError({
                        'vehicle': 'Selected vehicle does not belong to your business.'
                    })
            except Vehicle.DoesNotExist:
                pass

        return cleaned_data
    


@admin.register(Bill)
class BillAdmin(ExportMixin, BusinessAwareAdmin):
    resource_class = BillResource
    formats = [base_formats.XLSX, base_formats.CSV]
    
    # Custom filter classes
    class PaymentStatusListFilter(admin.SimpleListFilter):
        title = 'Payment Status'
        parameter_name = 'payment_status'
        
        def lookups(self, request, model_admin):
            return [
                ('paid', 'Paid'),
                ('pending', 'Pending'),
                ('partial', 'Partially Paid'),
            ]
        
        def queryset(self, request, queryset):
            if self.value() == 'paid':
                return queryset.filter(pending_amount=0)
            elif self.value() == 'pending':
                return queryset.filter(advance_amount=0)
            elif self.value() == 'partial':
                return queryset.filter(advance_amount__gt=0, pending_amount__gt=0)
            return queryset
    
    class CommissionStatusListFilter(admin.SimpleListFilter):
        title = 'Commission Status'
        parameter_name = 'commission_status'
        
        def lookups(self, request, model_admin):
            return [
                ('paid', 'Commission Paid'),
                ('pending', 'Commission Pending'),
                ('partial', 'Commission Partial'),
                ('none', 'No Commission'),
            ]
        
        def queryset(self, request, queryset):
            if self.value() == 'paid':
                return queryset.filter(commission_pending=0, commission_charge__gt=0)
            elif self.value() == 'pending':
                return queryset.filter(commission_received=0, commission_charge__gt=0)
            elif self.value() == 'partial':
                return queryset.filter(commission_received__gt=0, commission_pending__gt=0)
            elif self.value() == 'none':
                return queryset.filter(commission_charge=0)
            return queryset
    
    class DateRangeFilter(admin.SimpleListFilter):
        title = 'Bill Date Range'
        parameter_name = 'bill_date_range'
        
        def lookups(self, request, model_admin):
            return [
                ('today', '📅 Today'),
                ('yesterday', '📅 Yesterday'),
                ('this_week', '📅 This Week'),
                ('last_week', '📅 Last Week'),
                ('this_month', '📅 This Month'),
                ('last_month', '📅 Last Month'),
                ('this_year', '📅 This Year'),
                ('last_7_days', '📅 Last 7 Days'),
                ('last_30_days', '📅 Last 30 Days'),
                ('last_90_days', '📅 Last 90 Days'),
            ]
        
        def queryset(self, request, queryset):
            from django.utils import timezone
            from datetime import timedelta
            
            today = timezone.now().date()
            
            if self.value() == 'today':
                return queryset.filter(bill_date=today)
            elif self.value() == 'yesterday':
                yesterday = today - timedelta(days=1)
                return queryset.filter(bill_date=yesterday)
            elif self.value() == 'this_week':
                start_of_week = today - timedelta(days=today.weekday())
                return queryset.filter(bill_date__gte=start_of_week)
            elif self.value() == 'last_week':
                start_of_last_week = today - timedelta(days=today.weekday() + 7)
                end_of_last_week = start_of_last_week + timedelta(days=6)
                return queryset.filter(bill_date__range=[start_of_last_week, end_of_last_week])
            elif self.value() == 'this_month':
                start_of_month = today.replace(day=1)
                return queryset.filter(bill_date__gte=start_of_month)
            elif self.value() == 'last_month':
                first_day_of_this_month = today.replace(day=1)
                last_day_of_last_month = first_day_of_this_month - timedelta(days=1)
                first_day_of_last_month = last_day_of_last_month.replace(day=1)
                return queryset.filter(bill_date__range=[first_day_of_last_month, last_day_of_last_month])
            elif self.value() == 'this_year':
                start_of_year = today.replace(month=1, day=1)
                return queryset.filter(bill_date__gte=start_of_year)
            elif self.value() == 'last_7_days':
                start_date = today - timedelta(days=7)
                return queryset.filter(bill_date__gte=start_date)
            elif self.value() == 'last_30_days':
                start_date = today - timedelta(days=30)
                return queryset.filter(bill_date__gte=start_date)
            elif self.value() == 'last_90_days':
                start_date = today - timedelta(days=90)
                return queryset.filter(bill_date__gte=start_date)
            return queryset
        
        def choices(self, changelist):
            from django.utils.encoding import force_str
            yield {
                'selected': self.value() is None,
                'query_string': changelist.get_query_string({}, [self.parameter_name]),
                'display': '📅 All Dates',
            }
            for lookup, title in self.lookup_choices:
                yield {
                    'selected': self.value() == force_str(lookup),
                    'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                    'display': title,
                }

    list_display = (
        'bill_number',
        'party_name',
        'vehicle_display',
        'driver_name',
        'trip_route_display',
        'commission_amount_display',
        'commission_status_badge',
        'payment_status_badge',
        'bill_date_formatted',
        'print_button',
    )
    
    list_filter = (
        DateRangeFilter,
        'bill_date',
        'business',
        'driver',
        'vehicle',
        'party',
        PaymentStatusListFilter,
        CommissionStatusListFilter,
    )
    
    search_fields = (
        'bill_number',
        'party__name',
        'vehicle__vehicle_number',
        'driver__driver_name',
        'from_location',
        'to_location',
        'material_type'
    )
    
    readonly_fields = (
        'bill_number',
        'pending_amount_display',
        'commission_pending_display',
        'payment_status_badge',
        'commission_status_badge',
        'trip_route_display',
        'photo_preview',
        'created_at_display',
        'updated_at_display'
    )

    fieldsets = (
        ('Bill Information', {
            'fields': (
                'bill_number',
                'bill_date',
                'party',
                'driver',
                'vehicle',
                'reference'
            )
        }),
        ('Trip Details', {
            'fields': (
                'from_location',
                'to_location',
                'trip_route_display',
                'material_type'
            )
        }),
        ('Financial Details', {
            'fields': (
                'rent_amount',
                'advance_amount',
                'pending_amount_display',
                'payment_status_badge'
            )
        }),
        ('Commission Details', {
            'fields': (
                'commission',
                'commission_charge',
                'commission_received',
                'commission_pending_display',
                'commission_status_badge',
                'commission_received_date'
            )
        }),
        ('Media & Notes', {
            'fields': (
                'loading_photo',
                'unloading_photo',
                'document_photo',
                'photo_preview',
                'notes'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at_display', 'updated_at_display'),
            'classes': ('collapse',)
        }),
    )

    list_select_related = ('party', 'vehicle', 'driver', 'reference', 'business')
    date_hierarchy = 'bill_date'
    ordering = ('-bill_date',)
    
    actions = ['mark_as_paid', 'mark_commission_received']
    
    def print_button(self, obj):
        """Print button for individual bill"""
        from django.urls import reverse
        print_url = reverse('bill_print', args=[obj.id])
        
        return format_html(
            '''
            <a href="{}" 
            class="print-btn" 
            target="_blank"
            title="Print Bill #{}"
            onclick="event.stopPropagation();">
                🖨️ Print
            </a>
            ''',
            print_url, obj.bill_number
        )
    print_button.short_description = 'Print'

    def response_add(self, request, obj, post_url_continue=None):
        """Auto-print after creating a new bill"""
        response = super().response_add(request, obj, post_url_continue)
        
        # Check if user wants auto-print
        if '_print' in request.POST:
            # Redirect back to changelist with print parameter
            from django.urls import reverse
            changelist_url = reverse('admin:AdminApp_bill_changelist')
            return HttpResponseRedirect(f"{changelist_url}?_print={obj.id}")
        
        return response

    def response_change(self, request, obj):
        """Auto-print after updating a bill"""
        response = super().response_change(request, obj)
        
        if '_print' in request.POST:
            from django.urls import reverse
            changelist_url = reverse('admin:AdminApp_bill_changelist')
            return HttpResponseRedirect(f"{changelist_url}?_print={obj.id}")
        
        return response
    
    # Override changelist to add custom export buttons
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Add export buttons context
        extra_context['export_buttons'] = [
            {
                'label': '📤 Export Excel',
                'url': f'{request.path}export/?format=xlsx',
                'class': 'export-link',
            },
            {
                'label': '📤 Export CSV', 
                'url': f'{request.path}export/?format=csv',
                'class': 'export-link',
            },
        ]
        
        return super().changelist_view(request, extra_context=extra_context)

    # Your existing methods
    def party_name(self, obj):
        if obj.party:
            url = f"/admin/AdminApp/party/{obj.party.id}/change/"
            return format_html(
                '<a href="{}" style="color: #007bff; text-decoration: none; font-weight: 500;">{}</a>',
                url,
                obj.party.name
            )
        return "No Party"
    party_name.short_description = 'Party'
    
    def vehicle_display(self, obj):
        if obj.vehicle:
            url = f"/admin/AdminApp/vehicle/{obj.vehicle.id}/change/"
            return format_html(
                '<a href="{}" style="color: #28a745; text-decoration: none;"><code>{}</code></a>',
                url,
                obj.vehicle.vehicle_number
            )
        return "No Vehicle"
    vehicle_display.short_description = 'Vehicle'
    
    def driver_name(self, obj):
        if obj.driver:
            url = f"/admin/AdminApp/driver/{obj.driver.id}/change/"
            return format_html(
                '<a href="{}" style="color: #6f42c1; text-decoration: none;">{}</a>',
                url,
                obj.driver.driver_name
            )
        return "No Driver"
    driver_name.short_description = 'Driver'
    
    def trip_route_display(self, obj):
        return format_html(
            '<div style="font-size: 12px; color: #495057;">'
            '<span style="color: #dc3545;">{}</span> '
            '<span style="color: #6c757d;">→</span> '
            '<span style="color: #28a745;">{}</span>'
            '</div>',
            obj.from_location,
            obj.to_location
        )
    trip_route_display.short_description = 'Route'
    
    def commission_amount_display(self, obj):
        if obj.commission_charge:
            commission_formatted = f"{obj.commission_charge:,}"
            received_formatted = f"{obj.commission_pending:,}"
            
            return format_html(
                '<div style="text-align: center;">'
                '<div style="font-weight: 600; color: #17a2b8;">₹{}</div>'
                '<div style="font-size: 11px; color: red;">Pending: ₹{}</div>'
                '</div>',
                commission_formatted,
                received_formatted
            )
        return "No Commission"
    commission_amount_display.short_description = 'Commission'

    def pending_amount_display(self, obj):
        pending_formatted = f"{obj.pending_amount:,}"
        color = '#dc3545' if obj.pending_amount > 0 else '#28a745'
        
        return format_html(
            '<span style="font-weight: 600; color: {};">₹{}</span>',
            color,
            pending_formatted
        )
    pending_amount_display.short_description = 'Pending Amount'
    
    def commission_pending_display(self, obj):
        if obj.commission_charge:
            commission_formatted = f"{obj.commission_pending:,}"
            color = '#dc3545' if obj.commission_pending > 0 else '#28a745'
            
            return format_html(
                '<span style="font-weight: 600; color: {};">₹{}</span>',
                color,
                commission_formatted
            )
        return "No Commission"
    commission_pending_display.short_description = 'Commission Pending'
    
    def payment_status_badge(self, obj):
        status = obj.payment_status
        colors = {
            'Paid': 'success',
            'Pending': 'danger',
            'Partially Paid': 'warning'
        }
        color = colors.get(status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            status
        )
    payment_status_badge.short_description = 'Payment Status'
    
    def commission_status_badge(self, obj):
        status = obj.commission_status
        colors = {
            'Commission Paid': 'success',
            'Commission Pending': 'danger',
            'Commission Partially Paid': 'warning',
            'No Commission': 'secondary'
        }
        color = colors.get(status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            status
        )
    commission_status_badge.short_description = 'Commission Status'
    
    def bill_date_formatted(self, obj):
        return obj.bill_date.strftime("%d %b %Y")
    bill_date_formatted.short_description = 'Bill Date'
    
    def photo_preview(self, obj):
        if obj.loading_photo:
            return format_html(
                '<img src="{}" width="80" height="60" style="border-radius: 6px; border: 2px solid #ddd;" />',
                obj.loading_photo.url
            )
        return format_html(
            '<div style="width: 80px; height: 60px; border-radius: 6px; background: #f8f9fa; border: 2px dashed #dee2e6; display: flex; align-items: center; justify-content: center; color: #6c757d; font-size: 12px;">No Photo</div>'
        )
    photo_preview.short_description = 'Loading Photo'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime("%d %b %Y %H:%M:%S")
    created_at_display.short_description = 'Created At'
    
    def updated_at_display(self, obj):
        return obj.updated_at.strftime("%d %b %Y %H:%M:%S")
    updated_at_display.short_description = 'Updated At'
    
    def mark_as_paid(self, request, queryset):
        from django.db.models import F
        updated = queryset.update(
            advance_amount=F('rent_amount'),
            pending_amount=0
        )
        self.message_user(
            request,
            f'Successfully marked {updated} bill(s) as paid.',
            messages.SUCCESS
        )
    mark_as_paid.short_description = "Mark selected bills as paid"
    
    def mark_commission_received(self, request, queryset):
        from django.utils import timezone
        from django.db.models import F
        updated = queryset.update(
            commission_received=F('commission_charge'),
            commission_pending=0,
            commission_received_date=timezone.now().date()
        )
        self.message_user(
            request,
            f'Successfully marked commission as received for {updated} bill(s).',
            messages.SUCCESS
        )
    mark_commission_received.short_description = "Mark commission as received"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('party', 'vehicle', 'driver', 'reference', 'business')
    
    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        if not request.user.is_system_admin:
            list_filter = [f for f in list_filter if f != 'business']
        return list_filter
    
    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = BillForm
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # Pass request to form
        return form

  

