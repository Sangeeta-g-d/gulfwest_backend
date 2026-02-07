from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.urls import resolve
from django.core.paginator import Paginator
from PIL import Image
from firebase_admin.exceptions import FirebaseError
from .utils import login_required_nocache 
from django.http import HttpResponse
from openpyxl import Workbook
from django.contrib.auth.decorators import login_required
from . models import *
from django.db.models import Sum, Count
from django.utils.timezone import make_aware
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import logging
import os
from jwt import PyJWTError
from . models import Categories
from orders.models import *
from django.db.models import Q
from firebase_admin import messaging
from django.urls import reverse
from decimal import Decimal
from django.core.files.storage import FileSystemStorage
import pandas as pd
from orders.models import Order
from pytz import timezone as pytz_timezone
from decimal import Decimal, InvalidOperation
# Create your views here.
import pandas as pd
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.utils import timezone
import pytz
from datetime import datetime
from django.views.decorators.http import require_http_methods
from io import BytesIO
import base64
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use Agg backend for non-GUI rendering
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, messaging
from .utils import  initialize_firebase
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction
from .services import anonymize_user
User = get_user_model()

initialize_firebase()




@require_http_methods(["GET", "POST"])
def anonymize_account_view(request):
    """
    Public/self-service endpoint:
    - User enters phone + password.
    - If correct, anonymize account.
    """
    error_msg = None
    success_msg = None

    if request.method == "POST":
        phone = (request.POST.get("phone") or "").strip()
        password = request.POST.get("password") or ""

        try:
            user = User.objects.get(phone_number=phone, is_active=True)
        except User.DoesNotExist:
            error_msg = "Invalid phone or password."
        else:
            if not user.check_password(password):
                error_msg = "Invalid phone or password."
            else:
                # Optional: only allow customers to self-delete
                # if user.role != "customer":
                #     error_msg = "Only customer accounts can be anonymized via this page."

                if not error_msg:
                    with transaction.atomic():
                        anonymize_user(user)

                    # If the same user is logged in, log them out
                    if request.user.is_authenticated and request.user.pk == user.pk:
                        logout(request)

                    success_msg = "Your account has been anonymized successfully."
                    return render(request, "deleted.html", {"success_msg": success_msg})

    return render(request, "anonymize_account.html", {"error_msg": error_msg})


def upload_bulk_products(request, id):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        saved_file_path = fs.location + '/' + filename  # Full path

        try:
            # Get category by ID from URL
            try:
                category = Categories.objects.get(id=id)
            except Categories.DoesNotExist:
                print(f"Category with ID {id} not found.")
                return redirect('/products/?status=invalid_category')

            # Read Excel or CSV
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                data = pd.read_excel(saved_file_path)
            elif filename.endswith('.csv'):
                data = pd.read_csv(saved_file_path)
            else:
                raise ValueError("Unsupported file type. Upload Excel or CSV.")

            print("DataFrame loaded:")
            print(data)

            for index, row in data.iterrows():
                try:
                    display_name = row['display_name']
                    SAP_code = row['SAP_code']  # required
                    description = row['description']  # required
                    brand_name = row.get('brand_name', '')
                    calories = row.get('calories', '')
                    water = row.get('water', '')
                    carbs = row.get('carbs', '')

                    Product.objects.create(
                        category=category,
                        display_name=display_name,
                        SAP_code=SAP_code,
                        brand_name=brand_name,
                        description=description,
                        calories=calories,
                        water=water,
                        carbs=carbs,
                        is_active=True
                    )
                    print(f"Product '{display_name}' added successfully.")

                except Exception as row_err:
                    print(f"Error in row {index}: {row_err}")

            return redirect('/products/?status=success')

        except Exception as e:
            print(f"Exception: {str(e)}")
            return redirect('/products/?status=failure')

    else:
        print("Invalid request or no file uploaded.")
        return redirect('/products/?status=nofile')



def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('/admin_dashboard/')
        if request.user.role == 'staff':
            return redirect('/staff_dashboard')
        else:
            return redirect('/')
    error_msg = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            request.session.set_expiry(3 * 24 * 60 * 60)
            if user.is_superuser:
                return redirect('/admin_dashboard/')
            if user.role == 'staff':
                return redirect('/staff_dashboard')
            else:
                error_msg = "You are not authorized to access this page."
        else:
            error_msg = "Invalid username or password."
    return render(request,'login.html', {'error_msg': error_msg})

def forgot_password_view(request):
    error_msg = None
    success_msg = None

    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            print(user)
            # ✅ allow only admin or staff
            if not (user.is_superuser or user.role == "staff"):
                raise User.DoesNotExist

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_link = request.build_absolute_uri(
                reverse("reset_password", kwargs={"uidb64": uid, "token": token})
            )

            # Send Email
            subject = "Password Reset Request"
            message = f"Hi {user.name or 'User'},\n\nClick below to reset your password:\n{reset_link}\n\nIf you didn’t request this, ignore this email."
            send_mail(subject, message, None, [user.email])

            success_msg = "Password reset link has been sent to your email."
        except User.DoesNotExist:
            error_msg = "No admin/staff user found with this email."

    return render(request, "forgot_password.html", {"error_msg": error_msg, "success_msg": success_msg})

# Reset Password View
def reset_password_view(request, uidb64, token):
    error_msg = None
    success_msg = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")

            if password1 and password1 == password2:
                user.set_password(password1)
                user.save()
                success_msg = "Password reset successful. You can now login."
                return redirect("login")  # redirect to login
            else:
                error_msg = "Passwords do not match."

        return render(request, "reset_password.html", {"error_msg": error_msg, "success_msg": success_msg})
    else:
        error_msg = "Invalid or expired reset link."
        return render(request, "reset_password.html", {"error_msg": error_msg})

def logout_view(request):
    logout(request)
    return redirect('/')

@login_required_nocache
def admin_dashboard(request):
    if not request.user.is_superuser and hasattr(request.user, 'staff_profile'):
        return redirect('staff_dashboard')
    
    now = timezone.now()
    today = now.date()

    # Get selected date from GET request or default to today
    selected_date_str = request.GET.get('selected_date')
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date() if selected_date_str else today
    except ValueError:
        selected_date = today

    # Count orders on selected date
    orders_on_date = Order.objects.filter(placed_at__date=selected_date)
    orders_count = orders_on_date.count()

    # Dashboard metrics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum('final_total'))['total'] or Decimal('0.00')
    total_customers = CustomUser.objects.filter(role='customer').count()
    total_products = Product.objects.filter(is_active=True, deleted=False).count()

    top_products = (
        OrderItem.objects
        .values('variant__product__display_name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )

    active_promos = PromoCode.objects.filter(is_active=True, start_time__lte=now, end_time__gte=now)
    flash_sales = FlashSale.objects.filter(is_active=True, start_time__lte=now, end_time__gte=now).prefetch_related('products')[:5]

    current_url_name = resolve(request.path_info).url_name

    # Chart: Order status distribution
    order_status_counts = dict(
        Order.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
    )
    fig1, ax1 = plt.subplots()
    light_colors = ['#AEDFF7', '#B8EAD9', '#FFF2A6', '#FFD6A5', '#E6CCF5']
    ax1.pie(order_status_counts.values(), labels=order_status_counts.keys(), autopct='%1.1f%%',
            startangle=140, colors=light_colors[:len(order_status_counts)], textprops={'fontsize': 10})
    ax1.axis('equal')
    buf1 = BytesIO()
    plt.savefig(buf1, format='png', bbox_inches='tight')
    buf1.seek(0)
    order_status_chart = base64.b64encode(buf1.read()).decode('utf-8')
    plt.close(fig1)
    vat = VAT.objects.first()
    banner = DashboardBanner.objects.first()
    context = {
        'current_url_name': current_url_name,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'total_products': total_products,
        'top_products': top_products,
        'flash_sales': flash_sales,
        'order_status_chart': order_status_chart,
        'active_promos': active_promos,
        'orders_count': orders_count,
        'selected_date': selected_date,
        'today': today,
        "vat_value": vat.value if vat else None,
        "banner": banner,
    }

    return render(request, 'admin_dashboard.html', context)


@login_required_nocache
def customers(request):
    current_url_name = resolve(request.path_info).url_name
    details = CustomUser.objects.filter(role='customer').exclude(is_superuser=True).order_by('-id')
    context = {
        'details': details,
        'current_url_name': current_url_name,
    }
    return render(request,'customers.html',context)

@login_required_nocache
def toggle_approval(request, id):
    user = get_object_or_404(CustomUser, id=id, role='customer')
    print(user)
    user.flag = not user.flag  # Toggle True/False
    user.save()
    return redirect('customers')

@login_required_nocache
def delete_user(request, user_id):
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        user.delete()
        return redirect('/customers/?status=deleted')
    except:
        return redirect('/customers/?status=delete_failed')


@login_required_nocache
def add_category(request):
    if request.method == "POST":
        category_name = request.POST.get('category')
        background_img = request.FILES.get('background_img')

        if not category_name:
            return JsonResponse({'status': 'error', 'message': 'Category name cannot be empty'})

        if not background_img:
            return JsonResponse({'status': 'error', 'message': 'Please upload an image.'})

        # Validate image dimensions
        try:
            img = Image.open(background_img)
            width, height = img.size
            if width != 463 or height != 563:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Image must be exactly 463px by 563px.'
                })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid image file.'
            })

        # Save category if all checks pass
        Categories.objects.create(category_name=category_name, background_img=background_img)
        return JsonResponse({'status': 'success', 'message': 'Category added successfully'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def toggle_category_status(request, category_id):
    if request.method == "POST":
        category = get_object_or_404(Categories, id=category_id)
        category.is_enabled = not category.is_enabled
        category.save()
        return JsonResponse({"status": "success", "enabled": category.is_enabled})
    return JsonResponse({"status": "error"}, status=400)


@login_required_nocache
def category_list(request):
    categories = Categories.objects.order_by('-id')
    context = {
        'current_url_name':'category',
        'categories':categories
    }
    return render(request,'category_list.html',context)

@login_required_nocache
def edit_category(request, category_id):
    category = get_object_or_404(Categories, id=category_id)
    if request.method == 'POST':
        category.category_name = request.POST.get('category_name')
        if request.FILES.get('background_img'):
            category.background_img = request.FILES['background_img']
        category.save()
        return redirect('/category_list')  # replace with your actual category list URL name
    return redirect('/category_list')

@login_required_nocache
def add_unit(request):
    if request.method == "POST":
        name = request.POST.get('name')
        abbreviation = request.POST.get('abbreviation')
        conversion_factor = request.POST.get('conversion_factor')

        if name and abbreviation and conversion_factor:
            try:
                conversion_factor = float(conversion_factor)
                Unit.objects.create(
                    name=name,
                    abbreviation=abbreviation,
                    conversion_factor_to_base=conversion_factor
                )
                return JsonResponse({'status': 'success', 'message': 'Unit added successfully'})
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid conversion factor'})
        else:
            return JsonResponse({'status': 'error', 'message': 'All fields are required'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required_nocache
def staff_details(request):
    staff_list = Staff.objects.select_related('user').all()  # Efficiently fetch related user
    context = {
        'current_url_name': "staff",
        'details': staff_list
    }
    return render(request, 'staff_details.html', context)

@login_required_nocache
def add_staff(request):
    roles = Role.objects.all()

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        city = request.POST.get('city')
        designation = request.POST.get('designation')
        selected_role_ids = request.POST.getlist('roles')

        # Check for email OR phone number duplicates
        if CustomUser.objects.filter(email=email).exists():
            return redirect('/add_staff/?status=email_exists')

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            return redirect('/add_staff/?status=phone_exists')

        # Safe to create user
        user = CustomUser.objects.create(
            email=email,
            phone_number=phone_number,
            city=city,
            role='staff',
            is_active=True,
            is_staff=True,
        )
        user.set_password(phone_number)
        user.save()

        staff = Staff.objects.create(
            user=user,
            full_name=full_name,
            designation=designation,
            city=city,
            phone_number=phone_number
        )

        if selected_role_ids:
            staff.roles.set(selected_role_ids)

        messages.success(request, 'Staff member added successfully.')
        return redirect('/staff_details/?status=true')

    return render(request, 'add_staff.html', {'roles': roles, 'current_url_name': 'staff'})

@login_required_nocache
def edit_staff_details(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    user = staff.user
    roles = Role.objects.all()

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        city = request.POST.get('city')
        designation = request.POST.get('designation')
        selected_roles = request.POST.getlist('roles')

        # ✅ Check for duplicate email
        if CustomUser.objects.exclude(id=user.id).filter(email=email).exists():
            return render(request, 'edit_staff_details.html', {
                'staff': staff,
                'roles': roles,
                'error': "This email is already used by another user."
            })

        # ✅ Check for duplicate phone
        if phone_number and CustomUser.objects.exclude(id=user.id).filter(phone_number=phone_number).exists():
            return render(request, 'edit_staff_details.html', {
                'staff': staff,
                'roles': roles,
                'error': "This phone number is already used by another user."
            })

        # Update user fields
        user.email = email
        user.phone_number = phone_number
        user.city = city
        if phone_number:
            user.set_password(phone_number)
        user.save()

        # Update staff fields
        staff.full_name = full_name
        staff.designation = designation
        staff.save()

        # Update staff roles
        staff.roles.set(selected_roles)

        return redirect('/staff_details/?status=updated')

    return render(request, 'edit_staff_details.html', {
        'staff': staff,
        'roles': roles
    })

@login_required_nocache
def delete_staff(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    user = staff.user
    staff.delete()
    user.delete()  # Optional: remove the associated user too
    return redirect('/staff_details/?status=deleted')

@login_required_nocache
def products(request):
    categories = Categories.objects.all()
    print(categories)
    context = {
        'current_url_name': "excel",
        'categories': categories,
    }
    return render(request,'products.html',context)


@login_required_nocache
def delete_category(request, category_id):
    category = get_object_or_404(Categories, id=category_id)
    category.delete()
    return redirect('/category_list/?status=deleted')

@login_required_nocache
def add_product_and_variant(request):
    status = request.GET.get('status', '')
    categories = Categories.objects.all()
    units = Unit.objects.all()
    products = Product.objects.filter(deleted=False, is_active=True)

    if request.method == 'POST' and 'display_name' in request.POST:
        form_data = {
            'display_name': request.POST.get('display_name'),
            'category': request.POST.get('category'),
            'description': request.POST.get('description'),
            'SAP_code': request.POST.get('SAP_code'),
            'brand_name': request.POST.get('brand_name') or '',
            'calories': request.POST.get('calories') or '',
            'water': request.POST.get('water') or '',
            'carbs': request.POST.get('carbs') or '',
            'is_active': True
        }

        # Check for duplicate SAP code
        if Product.objects.filter(SAP_code=form_data['SAP_code']).exists():
            # Render form with error status and existing data
            return render(request, 'add_product.html', {
                'categories': categories,
                'units': units,
                'products': products,
                'form_data': form_data,
                'status': 'SAP_exists',
                'current_url_name': "products"
            })

        try:
            product = Product.objects.create(
                category_id=form_data['category'],
                display_name=form_data['display_name'],
                description=form_data['description'],
                SAP_code=form_data['SAP_code'],
                brand_name=form_data['brand_name'] or None,
                calories=form_data['calories'] or None,
                water=form_data['water'] or None,
                carbs=form_data['carbs'] or None,
                is_active=form_data['is_active']
            )
        except Exception as e:
            # Something went wrong, render with fail status and existing data
            return render(request, 'add_product.html', {
                'categories': categories,
                'units': units,
                'products': products,
                'form_data': form_data,
                'status': 'fail',
                'current_url_name': "products"
            })

        # Handle images
        images = request.FILES.getlist('product_images')
        for image in images:
            ProductImage.objects.create(product=product, image=image)

        # Success redirect
        return redirect('/add_product/?status=true')

    if request.method == 'POST' and 'product' in request.POST:
        # Handle variant form as you had it, keep redirect on success
        product_id = request.POST.get('product')
        product = get_object_or_404(Product, id=product_id)

        ProductVariant.objects.create(
            product=product,
            price=request.POST.get('price'),
            discount_price=request.POST.get('discount_price') or None,
            selling_quantity=request.POST.get('selling_quantity'),
            selling_unit_id=request.POST.get('selling_unit'),
            )
        return redirect('/add_product/?status=variant_added')

    # Default GET rendering
    return render(request, 'add_product.html', {
        'categories': categories,
        'units': units,
        'products': products,
        'current_url_name': "add-products",
        'status': status,
    })

@login_required_nocache
def add_images(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        images = request.FILES.getlist('images')  # get multiple images
        for image in images:
            ProductImage.objects.create(product=product, image=image)
        return redirect('/view_products/?added=true')  # replace with where you want to redirect after uploading

    return render(request, 'add_images.html', {'product': product})

@login_required_nocache
def view_products(request):
      # Latest first
    search_query = request.GET.get('search', '')  # Get search text
    status_filter = request.GET.get('status', '')
    active_status = request.GET.get('active_status', '')
    products = Product.objects.filter(deleted = False).order_by('-id')
    if search_query:
        if search_query:
            products = products.filter(
            Q(display_name__icontains=search_query) |
            Q(SAP_code__icontains=search_query) |
            Q(brand_name__icontains=search_query)
        )
    if status_filter:
        products = products.filter(category__id=status_filter)
    if active_status:
        if active_status == 'active':
            products = products.filter(is_active=True)
        elif active_status == 'inactive':
            products = products.filter(is_active=False)
        
    paginator = Paginator(products,15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Categories.objects.all()
    context = {
        'current_url_name':'products',
        'products': products,
        'search_query':search_query,
        'status_filter':status_filter,
        'active_status':active_status,
        'page_obj':page_obj,
        'categories':categories
    }
    return render(request, 'view_products.html', context)


@login_required_nocache
def export_products_excel(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    products = Product.objects.filter(deleted=False).order_by('-id')

    if search_query:
        products = products.filter(
            Q(display_name__icontains=search_query) |
            Q(SAP_code__icontains=search_query) |
            Q(brand_name__icontains=search_query)
        )

    if status_filter:
        products = products.filter(category__id=status_filter)

    wb = Workbook()
    ws = wb.active
    ws.title = "Products"

    # Header row
    headers = [
        "ID",
        "Display Name",
        "Brand Name",
        "SAP Code",
        "Category",
        "Status",
        "Created At"
    ]
    ws.append(headers)

    for product in products:
        first_variant = product.variants.first()
        status = "Active" if first_variant and first_variant.available else "Inactive"

        ws.append([
            product.id,
            product.display_name,
            product.brand_name or "",
            product.SAP_code or "",
            product.category.category_name,
            status,
            product.created_at.strftime("%Y-%m-%d"),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=products.xlsx'

    wb.save(response)
    return response

@login_required_nocache
def product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    images = ProductImage.objects.filter(product=product)

    variants = product.variants.all()
    for variant in variants:
        if variant.price and variant.discount_price and variant.price > 0:
            variant.discount_percentage = round((variant.price - variant.discount_price) / variant.price * 100)
        else:
            variant.discount_percentage = None

    context = {
        'product': product,
        'images': images,
        'variants': variants,
        'current_url_name': "products",
    }
    return render(request, 'product_details.html', context)

@login_required_nocache
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    images = ProductImage.objects.filter(product=product)
    variants = ProductVariant.objects.filter(product=product)

    if request.method == 'POST':
        # Handle add variant modal form
        if request.POST.get('add_variant') == '1':
            selling_quantity = request.POST.get('selling_quantity')
            selling_unit_id = request.POST.get('selling_unit')
            price = request.POST.get('price')
            discount_price = request.POST.get('discount_price') or None
            available = request.POST.get('available') == 'on'
            ProductVariant.objects.create(
                product=product,
                selling_quantity=selling_quantity,
                selling_unit_id=selling_unit_id,
                price=price,
                discount_price=discount_price,
                available=available
            )
            return redirect(f'/edit_product/{product_id}/?status=variant_added')

        # Otherwise, update product fields
        product.display_name = request.POST.get('display_name')
        product.brand_name = request.POST.get('brand_name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price') or 0
        product.discount_price = request.POST.get('discount_price') or 0
        product.selling_quantity = request.POST.get('selling_quantity') or 0
        product.calories = request.POST.get('calories') or 0
        product.water = request.POST.get('water') or 0
        product.carbs = request.POST.get('carbs') or 0

        # Optional related fields
        category_id = request.POST.get('category')
        selling_unit_id = request.POST.get('selling_unit')

        if category_id:
            product.category_id = category_id
        if selling_unit_id:
            product.selling_unit_id = selling_unit_id

        product.save()
        return redirect('/view_products/?edited=true')

    # GET request
    print("Rendering edit product page (GET request)")
    categories = Categories.objects.all()
    units = Unit.objects.all()

    return render(request, 'edit_product.html', {
        'product': product,
        'images': images,
        'categories': categories,
        'units': units,
        'variants': variants,  # <--- added this
        'current_url_name': "products"
    })
    
@login_required_nocache
def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if request.method == "POST":
        try:
            variant.selling_quantity = Decimal(request.POST.get('selling_quantity'))
            variant.selling_unit_id = request.POST.get('selling_unit')
            variant.price = Decimal(request.POST.get('price'))
            discount_price = request.POST.get('discount_price')
            variant.discount_price = Decimal(discount_price) if discount_price else None
            variant.available = request.POST.get('available') == 'on'
            variant.save()
        except (InvalidOperation, TypeError):
            # Optional: log error or add message
            pass

        return redirect(f'/edit_product/{variant.product.id}/?status=v_edited')

    return redirect(f'/edit_product/{variant.product.id}/?status=v_edited')

@login_required_nocache
def edit_product_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    if request.method == 'POST':
        if 'image' in request.FILES:
            image.image = request.FILES['image']
            image.save()
            # Redirect with query param edited=true
            return redirect(f'/edit_product/{image.product.id}/?status=I_edit')
    return render(request, 'edit_product_image.html', {'image': image}) 

@login_required_nocache
def add_role(request):
    if request.method == 'POST':
        role_name = request.POST.get('name')
        if role_name:
            Role.objects.get_or_create(name=role_name)
            # Redirect to add_staff page with status=true
            return redirect(f"{reverse('add_staff')}?status=true")

    # Fallback redirect with status=false (optional)
    return redirect(f"{reverse('add_staff')}?status=false")

@login_required_nocache
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id
    variant.delete()
    return redirect(f'/edit_product/{product_id}/?status=v_deleted')

@login_required_nocache
def delete_product_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    product_id = image.product.id
    image.delete()
    return redirect(f'/edit_product/{product_id}/?status=I_delete')
   
@login_required_nocache
def upload_product_image(request, product_id):
    if request.method == 'POST' and request.FILES.get('image'):
        product = get_object_or_404(Product, id=product_id)
        ProductImage.objects.create(product=product, image=request.FILES['image'])
        return redirect('edit_product', product_id=product_id)
    
@login_required_nocache
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('/view_products/?deleted=true')

@login_required_nocache
def add_flash_sale(request):
    categories = Categories.objects.all()
    products = Product.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        discount_percentage = request.POST.get("discount_percentage")
        start_time_str = request.POST.get("start_time")  # e.g. '2025-06-09T12:10'
        end_time_str = request.POST.get("end_time")      # e.g. '2025-06-11T11:12'
        apply_type = request.POST.get("apply_type")
        tagline = request.POST.get('tagline')
        background_image = request.FILES.get('background_image')

        # Define IST timezone
        ist = pytz.timezone('Asia/Riyadh')

        # Parse datetime string with 'T' separator from input
        start_time_naive = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        end_time_naive = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')

        # Localize naive datetime to IST
        start_time_ist = ist.localize(start_time_naive)
        end_time_ist = ist.localize(end_time_naive)

        # Convert IST to UTC for DB storage (Django stores in UTC)
        start_time_utc = start_time_ist.astimezone(pytz.UTC)
        end_time_utc = end_time_ist.astimezone(pytz.UTC)

        # Create FlashSale object
        flash_sale = FlashSale.objects.create(
            name=name,
            discount_percentage=discount_percentage,
            start_time=start_time_utc,
            end_time=end_time_utc,
            tagline=tagline,
            background_image=background_image
        )

        # Assign to selected categories or products
        if apply_type == "category":
            selected_categories = request.POST.getlist("categories")
            flash_sale.categories.set(selected_categories)
        elif apply_type == "product":
            selected_products = request.POST.getlist("products")
            flash_sale.products.set(selected_products)

        flash_sale.save()
        return redirect("/flash_sale/?status=true")  # or your flash sale list page

    return render(request, 'add_flash_sale.html', {
        "categories": categories,
        "products": products,
    })


@login_required_nocache
def flash_sale(request):
    flash_sales = FlashSale.objects.all().order_by('-start_time')
    return render(request, 'flash_sale.html', {
        'flash_sales': flash_sales,'current_url_name':"flash_sale"
    })

@login_required_nocache
def edit_flash_sale(request, sale_id):
    sale = get_object_or_404(FlashSale, id=sale_id)
    ist = pytz.timezone('Asia/Riyadh')

    if request.method == 'POST':
        sale.name = request.POST.get('name')
        sale.tagline = request.POST.get('tagline')
        sale.discount_percentage = request.POST.get('discount_percentage')

        # Parse and convert start_time and end_time from IST to UTC
        start_time_str = request.POST.get('start_time')  # e.g. '2025-06-24T06:04'
        end_time_str = request.POST.get('end_time')      # e.g. '2025-06-26T11:12'

        # Parse using datetime-local format
        start_time_naive = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        end_time_naive = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')

        # Localize to IST
        start_time_ist = ist.localize(start_time_naive)
        end_time_ist = ist.localize(end_time_naive)

        # Convert to UTC
        sale.start_time = start_time_ist.astimezone(pytz.UTC)
        sale.end_time = end_time_ist.astimezone(pytz.UTC)

        # Handle optional image upload
        if 'background_image' in request.FILES:
            sale.background_image = request.FILES['background_image']

        # Save sale info
        sale.save()

        # Update many-to-many fields
        apply_type = request.POST.get("apply_type")
        if apply_type == "category":
            selected_category_ids = request.POST.getlist('categories')
            sale.categories.set(selected_category_ids)
            sale.products.clear()
        elif apply_type == "product":
            selected_product_ids = request.POST.getlist('products')
            sale.products.set(selected_product_ids)
            sale.categories.clear()

        return redirect('flash_sale')

    categories = Categories.objects.all()
    products = Product.objects.all()

    # Format datetime values for datetime-local input
    start_time_local = sale.start_time.astimezone(ist).strftime('%Y-%m-%dT%H:%M')
    end_time_local = sale.end_time.astimezone(ist).strftime('%Y-%m-%dT%H:%M')

    return render(request, 'edit_flash_sale.html', {
        'sale': sale,
        'categories': categories,
        'products': products,
        'start_time_local': start_time_local,
        'end_time_local': end_time_local,
        'current_url_name': "flash_sale"
    })


@login_required_nocache
def delete_flash_sale(request, sale_id):
    sale = get_object_or_404(FlashSale, id=sale_id)
    sale.delete()
    return redirect('/flash_sale')


@login_required_nocache
def driver(request):
    driver_users = CustomUser.objects.filter(role='driver')  # Filter only drivers

    context = {
        'details': driver_users,
        'current_url_name': "driver"
    }
    return render(request, 'driver.html', context)

@login_required_nocache
def add_driver(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        country_code = request.POST.get('country_code')
        phone = request.POST.get('phone_number')
        profile = request.FILES.get('profile')
        province = request.POST.get('province')  # NEW

        phone_number = f"{country_code}{phone}".replace(" ", "").replace("-", "")

        if CustomUser.objects.filter(email=email).exists():
            return redirect('/add_driver/?status=email_exists')

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            return redirect('/add_driver/?status=phone_exists')

        user = CustomUser.objects.create(
            name=full_name,
            email=email,
            phone_number=phone_number,
            profile=profile,
            role='driver',
            province=province,   # NEW
            is_active=True,
            is_staff=False,
        )
        user.set_password(phone_number)
        user.save()

        return redirect('/driver/?status=added')

    return render(request, 'add_driver.html', {'current_url_name': "driver"})

@login_required_nocache
def edit_driver(request, driver_id):
    driver = get_object_or_404(CustomUser, id=driver_id, role='driver')

    if request.method == 'POST':
        driver.name = request.POST.get('full_name')
        driver.email = request.POST.get('email')
        driver.phone_number = request.POST.get('phone_number')
        driver.city = request.POST.get('city')
        driver.province = request.POST.get('province')  # NEW

        if request.FILES.get('profile'):
            driver.profile = request.FILES.get('profile')

        driver.save()
        return redirect('/driver/?status=updated')

    context = {
        'driver': driver,
        'current_url_name': "driver"
    }
    return render(request, 'edit_driver.html', context)

@login_required_nocache
def delete_driver(request, driver_id):
    driver = get_object_or_404(CustomUser, id=driver_id, role='driver')
    driver.delete()
    return redirect('/driver/?status=deleted')

@login_required_nocache
def orders(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    page_number = request.GET.get('page', 1)

    # Base queryset
    orders_qs = Order.objects.select_related('user', 'address', 'promo_code') \
        .prefetch_related('items__variant__product', 'items__variant__selling_unit', 'driver_assignment__driver') \
        .order_by('-id')

    # Apply search filter
    if search_query:
        orders_qs = orders_qs.filter(
            Q(user__name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)
        )

    # Apply status filter
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)

    # Paginate
    paginator = Paginator(orders_qs, 10)
    page_obj = paginator.get_page(page_number)

    # Compute pricing safely
    for order in page_obj:
        total_original = 0
        total_effective = 0
        for item in order.items.all():
            if item.variant:
                original_unit_price = float(item.variant.price)
                effective_unit_price = float(item.price)
            else:
                # Variant deleted — fallback to stored price
                original_unit_price = float(item.price)
                effective_unit_price = float(item.price)

            total_original += original_unit_price * item.quantity
            total_effective += effective_unit_price * item.quantity

        order.total_original_price = round(total_original, 2)
        order.total_effective_price = round(total_effective, 2)
        order.product_discount_total = round(total_original - total_effective, 2)

    # Get active drivers
    drivers = CustomUser.objects.filter(role='driver', is_active=True)

    context = {
        'orders': page_obj,
        'drivers': drivers,
        'current_url_name': "orders",
        'search_query': search_query,
        'status_filter': status_filter,
        'page_obj': page_obj,
    }
    return render(request, 'orders.html', context)



@require_POST
def change_order_status(request, order_id):
    print("➡️ Entered change_order_status view")

    # Get order and validate status
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status', '').lower()
    print(f"➡️ Order ID: {order.id}, New Status: {new_status}")

    valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        print(f"⚠️ Invalid status attempted: {new_status}")
        return redirect('orders')

    # Update order status
    order.status = new_status
    order.save()
    print(f"✅ Order updated to {order.status}")

    # Get active device tokens
    try:
        device_tokens = list(DeviceToken.objects.filter(
            user=order.user,
            is_active=True
        ).values_list("token", flat=True))
        print(f"➡️ Found {len(device_tokens)} active tokens")
    except Exception as e:
        print(f"⚠️ Error fetching tokens: {str(e)}")
        return redirect('orders')

    if not device_tokens:
        print("⚠️ No active device tokens found for this user.")
        return redirect('orders')

    # Prepare notification
    notification = messaging.Notification(
        title="Order Status Update",
        body=f"Your order #{order.id} is now {new_status.capitalize()}."
    )

    success_count = 0
    for token in device_tokens:
        try:
            message = messaging.Message(
                token=token,
                notification=notification,
                data={
                    "order_id": str(order.id),
                    "status": new_status,
                    "type": "order_update"
                },
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        channel_id="order_updates",
                        click_action="FLUTTER_NOTIFICATION_CLICK"
                    )
                ),
                apns=messaging.APNSConfig(
                    headers={"apns-priority": "10"},
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            content_available=True,
                            badge=1
                        )
                    )
                )
            )

            response = messaging.send(message)
            print(f"📨 Successfully sent to token {token[:10]}...")
            success_count += 1

        except Exception as e:
            print(f"❌ Error with token {token[:10]}...: {str(e)}")

    print(f"📊 Notification summary: {success_count}/{len(device_tokens)} succeeded")
    return redirect('orders')

@login_required_nocache
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    return redirect('/orders/?status=deleted')

@login_required
def assign_driver_to_order(request, order_id):
    if request.method == 'POST':
        driver_id = request.POST.get('driver_id')
        driver = get_object_or_404(CustomUser, id=driver_id, role='driver')
        order = get_object_or_404(Order, id=order_id)

        # Assign driver
        assignment, created = OrderDriverAssignment.objects.update_or_create(
            order=order,
            defaults={'driver': driver}
        )

        # Update status to 'shipped'
        order.status = 'shipped'

        order.save()

        print(f"✅ Driver {driver.name} assigned to Order {order.id}")

        # 🔔 Send push notification to driver
        device_tokens = list(DeviceToken.objects.filter(
            user=driver,
            is_active=True
        ).values_list("token", flat=True))

        if device_tokens:
            notification = messaging.Notification(
                title="📦 New Order Assigned",
                body=f"Order #{order.id} has been assigned to you. Please check your dashboard."
            )

            success_count = 0
            for token in device_tokens:
                try:
                    message = messaging.Message(
                        token=token,
                        notification=notification,
                        data={
                            "order_id": str(order.id),
                            "status": order.status,
                            "type": "driver_assignment"
                        },
                        android=messaging.AndroidConfig(
                            priority="high",
                            notification=messaging.AndroidNotification(
                                sound="default",
                                channel_id="driver_assignments",
                                click_action="FLUTTER_NOTIFICATION_CLICK"
                            )
                        ),
                        apns=messaging.APNSConfig(
                            headers={"apns-priority": "10"},
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    sound="default",
                                    content_available=True,
                                    badge=1
                                )
                            )
                        )
                    )
                    response = messaging.send(message)
                    print(f"📨 Sent assignment notification to driver token {token[:10]}...")
                    success_count += 1
                except Exception as e:
                    print(f"❌ Error sending to driver token {token[:10]}...: {str(e)}")

            print(f"📊 Driver notification summary: {success_count}/{len(device_tokens)} succeeded")
        else:
            print("⚠️ No active device tokens found for driver")

    # Redirect back to orders page
    return redirect('/orders/')


@login_required_nocache
def promo_code(request):
    promos = PromoCode.objects.all().order_by('-created_at')
    context = {
        "current_url_name":"promo_code",
        'promos': promos
    }
    return render(request, 'promo_code.html',context)

@login_required_nocache
def add_promo_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        discount_type = request.POST.get('discount_type')
        discount_value = request.POST.get('discount_value')
        minimum_order_amount = request.POST.get('minimum_order_amount') or 0
        usage_limit = request.POST.get('usage_limit') or None
        per_user_limit = request.POST.get('per_user_limit') or None
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_active = request.POST.get('is_active') == 'on'

        try:
            # Convert datetime-local to timezone-aware datetime
            ist = pytz_timezone("Asia/Riyadh")
            input_start = ist.localize(datetime.strptime(start_time, "%Y-%m-%dT%H:%M"))
            input_end = ist.localize(datetime.strptime(end_time, "%Y-%m-%dT%H:%M"))

            start_time_utc = input_start.astimezone(pytz.UTC)
            end_time_utc = input_end.astimezone(pytz.UTC)

            promo = PromoCode.objects.create(
                code=code,
                description=description,
                discount_type=discount_type,
                discount_value=discount_value,
                minimum_order_amount=minimum_order_amount,
                usage_limit=usage_limit if usage_limit else None,
                per_user_limit=per_user_limit if per_user_limit else None,
                start_time=start_time_utc,
                end_time=end_time_utc,
                is_active=is_active,
            )
            messages.success(request, f"Promo code '{promo.code}' created successfully.")
            return redirect('promo_code')  # Update to your actual promo list view name
        except Exception as e:
            messages.error(request, f"Error creating promo code: {e}")
            return render(request, 'add_promo_code.html')

    return render(request, 'add_promo_code.html',{"current_url_name":"promo_code"})

@login_required_nocache
def edit_promo_code(request, promo_id):
    promo = get_object_or_404(PromoCode, id=promo_id)

    if request.method == 'POST':
        ist = pytz.timezone("Asia/Riyadh")

        promo.code = request.POST.get('code')
        promo.discount_type = request.POST.get('discount_type')
        promo.discount_value = request.POST.get('discount_value') or 0
        promo.minimum_order_amount = request.POST.get('minimum_order_amount') or 0
        promo.usage_limit = request.POST.get('usage_limit') or None
        promo.per_user_limit = request.POST.get('per_user_limit') or None

        # Convert form datetime to aware datetime in IST
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')

        if start_time_str:
            start_time = make_aware(datetime.fromisoformat(start_time_str), timezone=ist)
            promo.start_time = start_time

        if end_time_str:
            end_time = make_aware(datetime.fromisoformat(end_time_str), timezone=ist)
            promo.end_time = end_time

        promo.description = request.POST.get('description')
        promo.is_active = 'is_active' in request.POST

        promo.save()
        messages.success(request, "Promo code updated successfully.")
        return redirect('promo_code')

    return render(request, 'edit_promo_code.html', {'promo': promo})


@login_required_nocache
def delete_promo_code(request, promo_id):
    code = get_object_or_404(PromoCode, id=promo_id)
    code.delete()
    return redirect('/promo_code/?status=deleted')


def promo_usage_chart(request):
    promo_codes = PromoCode.objects.all()

    labels = []
    data = []

    for promo in promo_codes:
        labels.append(promo.code)
        data.append(promo.usages.count())

    context = {
        'labels': labels,
        'data': data,
        'current_url_name': 'promo_usage_chart',
    }
    return render(request, 'promo_usage_chart.html', context)



# staff related code
@login_required_nocache
def staff_dashboard(request):
    total_orders = Order.objects.count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    pending_orders = Order.objects.filter(status='pending').count()
    total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('final_total'))['total'] or 0

    top_product_data = (
        OrderItem.objects
        .filter(order__status='delivered')
        .values('variant__product__display_name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')
        .first()
    )
    top_product = top_product_data['variant__product__display_name'] if top_product_data else 'N/A'

    total_products = Product.objects.count()
    total_customers = CustomUser.objects.filter(role='customer').count()

    context = {
        'total_orders': total_orders,
        'delivered_orders': delivered_orders,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue,
        'top_product': top_product,
        'total_products': total_products,
        'total_customers': total_customers,
        "current_url_name":"staff_dashboard",
    }
    return render(request, 'staff_dashboard.html', context)

@login_required_nocache
def onboarding_images(request):
    if request.method == 'POST' and request.FILES.get('image'):
        title = request.POST.get('title', '')
        sub_title = request.POST.get('sub_title', '')
        OnboardingImage.objects.create(
            image=request.FILES['image'],
            title=title,
            sub_title=sub_title
        )
        return redirect('/onboarding-images/?status=success')

    images = OnboardingImage.objects.all()
    context = {
        "current_url_name": "onboarding_images",
        "images": images
    }
    return render(request, 'onboarding_images.html', context)


@login_required_nocache
def delete_onboarding_image(request, pk):
    image = get_object_or_404(OnboardingImage, pk=pk)
    image.image.delete()  # delete file from storage
    image.delete()        # delete database entry
    return redirect('/onboarding-images/?status=deleted')


def privacy(request):
    return render(request,'privacy.html')


def terms(request):
    return render(request,'terms.html')

def manage_banner(request):
    banner = DashboardBanner.objects.first()

    if request.method == "POST":
        image = request.FILES.get("banner_image")
        display = request.POST.get("display") == "on"

        if not image and not banner:
            return JsonResponse(
                {"message": "Please select an image."},
                status=400
            )

        try:
            if banner:
                if image:
                    banner.image = image
                banner.display = display
                banner.save()
                message = "Banner image updated successfully!"
            else:
                DashboardBanner.objects.create(
                    image=image,
                    display=display
                )
                message = "Banner image added successfully!"
        except Exception as e:
            return JsonResponse(
                {"message": f"Error: {str(e)}"},
                status=500
            )

        return JsonResponse({"message": message})

    return render(request, "admin_dashboard.html", {"banner": banner})

# ✅ Manage VAT
def manage_vat(request):
    vat = VAT.objects.first()

    if request.method == "POST":
        value = request.POST.get("vat_value")

        if not value:
            return JsonResponse({"message": "Please enter a valid VAT value."}, status=400)

        if vat:
            vat.value = value
            vat.save()
            message = "VAT updated successfully."
        else:
            VAT.objects.create(value=value)
            message = "VAT added successfully."

        return JsonResponse({"message": message})

    # GET request
    return JsonResponse({"message": "Invalid request"}, status=400)