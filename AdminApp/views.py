from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from .models import Bill

@staff_member_required
def bill_print_view(request, bill_id):
    """Print single bill"""
    print(f"Requested bill ID: {bill_id}")
    print(f"Requested bill ID: {bill_id}")
    print(f"Requested bill ID: {bill_id}")
    print(f"Requested bill ID: {bill_id}")
    print(f"Requested bill ID: {bill_id}")
    print(f"Requested bill ID: {bill_id}")
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check permissions - user can only access bills from their business
    if not request.user.is_system_admin and hasattr(request.user, 'business'):
        if bill.business != request.user.business:
            raise PermissionDenied("You don't have permission to view this bill.")
    
    context = {
        'bill': bill,
        'title': f'Bill #{bill.bill_number}',
    }
    
    return render(request, 'admin/bill_print.html', context)

@staff_member_required
def bills_print_view(request):
    """Print multiple bills"""
    bill_ids = request.GET.get('ids', '')
    
    if bill_ids:
        bill_ids = [int(id) for id in bill_ids.split(',') if id.isdigit()]
        bills = Bill.objects.filter(id__in=bill_ids)
    else:
        bills = Bill.objects.none()
    
    # Filter by business for non-admin users
    if not request.user.is_system_admin and hasattr(request.user, 'business'):
        bills = bills.filter(business=request.user.business)
    
    context = {
        'bills': bills,
        'title': f'Bills Print - {bills.count()} bills',
    }
    
    return render(request, 'admin/bills_print.html', context)