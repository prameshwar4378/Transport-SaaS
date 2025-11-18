from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from .models import Bill
def index(request):
    return render(request, 'index.html')


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




# from django.shortcuts import render
# from django.contrib.admin.views.decorators import staff_member_required
# from django.utils import timezone
# from django.db.models import Count, Sum, Q, Avg
# from datetime import timedelta
# from .models import *

# @staff_member_required
# def analysis_dashboard(request):
#     """Advanced Analysis Dashboard"""
#     today = timezone.now().date()
#     week_ago = today - timedelta(days=7)
#     month_ago = today - timedelta(days=30)
    
#     # Get user's business
#     business = None
#     if hasattr(request.user, 'business') and request.user.business:
#         business = request.user.business
    
#     # Base querysets
#     if business:
#         bills = Bill.objects.filter(business=business)
#         vehicles = Vehicle.objects.filter(business=business)
#         parties = Party.objects.filter(business=business)
#     else:
#         bills = Bill.objects.all()
#         vehicles = Vehicle.objects.all()
#         parties = Party.objects.all()
    
#     # Time-based analytics
#     today_bills = bills.filter(bill_date=today)
#     week_bills = bills.filter(bill_date__gte=week_ago)
#     month_bills = bills.filter(bill_date__gte=month_ago)
    
#     # Financial Analytics
#     financial_stats = {
#         'today_revenue': today_bills.aggregate(total=Sum('rent_amount'))['total'] or 0,
#         'week_revenue': week_bills.aggregate(total=Sum('rent_amount'))['total'] or 0,
#         'month_revenue': month_bills.aggregate(total=Sum('rent_amount'))['total'] or 0,
#         'total_revenue': bills.aggregate(total=Sum('rent_amount'))['total'] or 0,
#         'pending_amount': bills.aggregate(total=Sum('pending_amount'))['total'] or 0,
#         'avg_bill_amount': bills.aggregate(avg=Avg('rent_amount'))['avg'] or 0,
#     }
    
#     # Performance Metrics
#     performance_metrics = {
#         'total_bills_count': bills.count(),
#         'bills_this_week': week_bills.count(),
#         'bills_this_month': month_bills.count(),
#         'paid_bills': bills.filter(pending_amount=0).count(),
#         'pending_bills': bills.filter(pending_amount__gt=0).count(),
#         'completion_rate': round((bills.filter(pending_amount=0).count() / bills.count() * 100), 2) if bills.count() > 0 else 0,
#     }
    
#     # Vehicle Analytics
#     vehicle_analytics = {
#         'total_vehicles': vehicles.count(),
#         'vehicles_with_bills': vehicles.annotate(bill_count=Count('bills')).filter(bill_count__gt=0).count(),
#         'active_vehicles': vehicles.filter(bills__bill_date__gte=week_ago).distinct().count(),
#         'top_vehicles': vehicles.annotate(
#             bill_count=Count('bills'),
#             total_earning=Sum('bills__rent_amount')
#         ).order_by('-total_earning')[:5],
#     }
    
#     # Party Analytics
#     party_analytics = {
#         'total_parties': parties.count(),
#         'active_parties': parties.filter(bills__bill_date__gte=month_ago).distinct().count(),
#         'top_parties': parties.annotate(
#             bill_count=Count('bills'),
#             total_spent=Sum('bills__rent_amount')
#         ).order_by('-total_spent')[:5],
#     }
    
#     # Commission Analytics
#     commission_stats = {
#         'total_commission_charge': bills.aggregate(total=Sum('commission_charge'))['total'] or 0,
#         'total_commission_received': bills.aggregate(total=Sum('commission_received'))['total'] or 0,
#         'pending_commission': bills.aggregate(total=Sum('commission_pending'))['total'] or 0,
#         'commission_collection_rate': round((bills.aggregate(total=Sum('commission_received'))['total'] or 0) / 
#                                           (bills.aggregate(total=Sum('commission_charge'))['total'] or 1) * 100, 2),
#     }
    
#     # Recent Activity Trends
#     recent_trends = []
#     for i in range(7, 0, -1):
#         date = today - timedelta(days=i)
#         day_bills = bills.filter(bill_date=date)
#         revenue = day_bills.aggregate(total=Sum('rent_amount'))['total'] or 0
#         count = day_bills.count()
        
#         recent_trends.append({
#             'date': date,
#             'revenue': revenue,
#             'bill_count': count,
#             'day_name': date.strftime('%a')
#         })
    
#     context = {
#         'business': business,
#         'today': today,
        
#         # Analytics Data
#         'financial_stats': financial_stats,
#         'performance_metrics': performance_metrics,
#         'vehicle_analytics': vehicle_analytics,
#         'party_analytics': party_analytics,
#         'commission_stats': commission_stats,
#         'recent_trends': recent_trends,
#         # Time ranges
#         'week_ago': week_ago,
#         'month_ago': month_ago,
#     }
#     return render(request, 'admin/index.html', context)

# def report_dashboard(request):
#     return render(request, "admin/report_dashboard.html")

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta, datetime
import json
from .models import Business, Bill, Vehicle, Party, Driver, VehicleOwner
from django.contrib.admin.models import LogEntry

 
@login_required
def report_dashboard(request):
    # Get business context based on user role
    if request.user.is_system_admin:
        businesses = Business.objects.all()
        selected_business = request.GET.get('business')
        if selected_business:
            business = get_object_or_404(Business, pk=selected_business)
        else:
            business = businesses.first() if businesses.exists() else None
    else:
        business = request.user.business
        businesses = Business.objects.filter(pk=business.pk) if business else Business.objects.none()

    if not business:
        return render(request, 'admin/report_dashboard.html', {
            'error': 'No business associated with your account'
        })

    # Date filters
    today = timezone.now().date()
    
    # Get start_date from request or default to 30 days ago
    start_date_str = request.GET.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=30)
    
    # Get end_date from request or default to today
    end_date_str = request.GET.get('end_date')
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today

    # Get filtered bills
    bills = Bill.objects.filter(
        business=business,
        bill_date__range=[start_date, end_date]
    )

    # Key Metrics
    total_bills = bills.count()
    total_revenue = bills.aggregate(Sum('rent_amount'))['rent_amount__sum'] or 0
    total_advance = bills.aggregate(Sum('advance_amount'))['advance_amount__sum'] or 0
    total_pending = bills.aggregate(Sum('pending_amount'))['pending_amount__sum'] or 0
    total_commission = bills.aggregate(Sum('commission_charge'))['commission_charge__sum'] or 0
    total_commission_received = bills.aggregate(Sum('commission_received'))['commission_received__sum'] or 0
    total_commission_pending = bills.aggregate(Sum('commission_pending'))['commission_pending__sum'] or 0

    # Quick Stats
    total_vehicles = Vehicle.objects.filter(business=business).count()
    total_parties = Party.objects.filter(business=business).count()
    total_drivers = Driver.objects.filter(business=business).count()
    total_owners = VehicleOwner.objects.filter(business=business).count()

    # Payment Status Distribution
    payment_status_data = {
        'Paid': bills.filter(pending_amount=0).count(),
        'Partially Paid': bills.filter(advance_amount__gt=0, pending_amount__gt=0).count(),
        'Pending': bills.filter(advance_amount=0, pending_amount__gt=0).count()
    }

    # Recent Activity
    recent_bills = bills.order_by('-bill_date')[:10]

    # Generate Chart Data for Chart.js
    chart_data = {
        'revenue_chart_data': get_revenue_chart_data(bills, start_date, end_date),
        'payment_status_chart_data': get_payment_status_chart_data(payment_status_data),
        'vehicle_performance_data': get_vehicle_performance_data(bills),
        'party_activity_data': get_party_activity_data(bills),
    }
    recent_actions = LogEntry.objects.select_related('content_type', 'user')[:10]

    context = {
        'business': business,
        'businesses': businesses,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        
        # Key Metrics
        'total_bills': total_bills,
        'total_revenue': total_revenue,
        'total_advance': total_advance,
        'total_pending': total_pending,
        'total_commission': total_commission,
        'total_commission_received': total_commission_received,
        'total_commission_pending': total_commission_pending,
        
        # Quick Stats
        'total_vehicles': total_vehicles,
        'total_parties': total_parties,
        'total_drivers': total_drivers,
        'total_owners': total_owners,
        
        # Chart Data
        'chart_data_json': json.dumps(chart_data),
        'recent_actions': recent_actions,
        # Recent Activity
        'recent_bills': recent_bills,
        'payment_status_data': payment_status_data,

    }
    
    return render(request, 'admin/report_dashboard.html', context)

def get_revenue_chart_data(bills, start_date, end_date):
    """Generate revenue chart data for Chart.js"""
    try:
        # Create date range
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        # Aggregate revenue by date
        daily_data = bills.values('bill_date').annotate(
            daily_revenue=Sum('rent_amount'),
            daily_advance=Sum('advance_amount')
        ).order_by('bill_date')
        
        # Create data arrays
        revenue_data = [0] * len(date_range)
        advance_data = [0] * len(date_range)
        
        for data in daily_data:
            date_str = data['bill_date'].strftime('%Y-%m-%d')
            if date_str in date_range:
                index = date_range.index(date_str)
                revenue_data[index] = float(data['daily_revenue'] or 0)
                advance_data[index] = float(data['daily_advance'] or 0)
        
        return {
            'labels': date_range,
            'datasets': [
                {
                    'label': 'Total Revenue',
                    'data': revenue_data,
                    'borderColor': '#4CAF50',
                    'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                    'borderWidth': 3,
                    'fill': True,
                    'tension': 0.4
                },
                {
                    'label': 'Advance Received',
                    'data': advance_data,
                    'borderColor': '#FF9800',
                    'backgroundColor': 'rgba(255, 152, 0, 0.1)',
                    'borderWidth': 3,
                    'fill': True,
                    'tension': 0.4
                }
            ]
        }
    except Exception as e:
        return {'labels': [], 'datasets': []}

def get_payment_status_chart_data(payment_status_data):
    """Generate payment status chart data for Chart.js"""
    try:
        labels = list(payment_status_data.keys())
        values = list(payment_status_data.values())
        colors = ['#4CAF50', '#FF9800', '#F44336']
        
        return {
            'labels': labels,
            'datasets': [{
                'data': values,
                'backgroundColor': colors,
                'borderColor': colors,
                'borderWidth': 2
            }]
        }
    except Exception as e:
        return {'labels': [], 'datasets': []}

def get_vehicle_performance_data(bills):
    """Generate vehicle performance data for Chart.js"""
    try:
        vehicle_data = bills.values('vehicle__vehicle_number').annotate(
            total_trips=Count('id'),
            total_revenue=Sum('rent_amount')
        ).order_by('-total_revenue')[:10]
        
        if not vehicle_data:
            return {'labels': [], 'datasets': []}
        
        vehicle_numbers = [item['vehicle__vehicle_number'] or 'Unknown' for item in vehicle_data]
        trips = [item['total_trips'] for item in vehicle_data]
        revenue = [float(item['total_revenue'] or 0) for item in vehicle_data]
        
        return {
            'labels': vehicle_numbers,
            'datasets': [
                {
                    'label': 'Total Trips',
                    'data': trips,
                    'backgroundColor': '#2196F3',
                    'borderColor': '#2196F3',
                    'borderWidth': 2
                },
                {
                    'label': 'Total Revenue (₹)',
                    'data': revenue,
                    'backgroundColor': '#4CAF50',
                    'borderColor': '#4CAF50',
                    'borderWidth': 2,
                    'type': 'line',
                    'yAxisID': 'y1'
                }
            ]
        }
    except Exception as e:
        return {'labels': [], 'datasets': []}

def get_party_activity_data(bills):
    """Generate party activity data for Chart.js"""
    try:
        party_data = bills.values('party__name').annotate(
            total_bills=Count('id'),
            total_amount=Sum('rent_amount')
        ).order_by('-total_amount')[:8]
        
        if not party_data:
            return {'labels': [], 'datasets': []}
        
        parties = [item['party__name'] or 'Unknown Party' for item in party_data]
        amounts = [float(item['total_amount'] or 0) for item in party_data]
        
        return {
            'labels': parties,
            'datasets': [{
                'label': 'Revenue (₹)',
                'data': amounts,
                'backgroundColor': '#9C27B0',
                'borderColor': '#9C27B0',
                'borderWidth': 2
            }]
        }
    except Exception as e:
        return {'labels': [], 'datasets': []}