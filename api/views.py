# views.py
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from .serializers import *
from orders.models import *
import random
from django.db.models import Q
from users.models import CustomUser
from .utils.otp import generate_otp, send_otp
from twilio.base.exceptions import TwilioRestException
import traceback
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from . models import * 
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from rest_framework.generics import ListAPIView
from rest_framework.generics import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


@method_decorator(csrf_exempt, name='dispatch')
class SendOTPView(APIView):
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            mode = request.query_params.get('mode')  # 'login' or 'register'

            if mode == 'login' and not CustomUser.objects.filter(phone_number=phone).exists():
                return Response({'error': 'User does not exist. Please register.'}, status=status.HTTP_404_NOT_FOUND)

            if mode == 'register' and CustomUser.objects.filter(phone_number=phone).exists():
                return Response({'error': 'User already exists. Please login.'}, status=status.HTTP_400_BAD_REQUEST)

            otp = generate_otp()
            print(f"Phone received: {phone}")
            print(f"Mode: {mode}")
            print(f"Generated OTP: {otp}")
            print("Attempting to send OTP...")

            # ✅ Save OTP first
            PhoneOTP.objects.update_or_create(
                phone_number=phone,
                defaults={'otp': otp, 'created_at': timezone.now()}
            )

            try:
                send_otp(phone, otp)
            except TwilioRestException as e:
                print("Twilio Error:")
                print(str(e))
                traceback.print_exc()
                return Response({
                    'message': 'OTP could not be sent via SMS, but you can still use the master OTP (for dev/testing).',
                    'twilio_error': str(e),
                    'dev_note': 'Use master OTP: 999999 if configured.'
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({'message': 'OTP sent successfully.'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            otp_input = serializer.validated_data['otp']
            mode = request.query_params.get('mode')  # 'register' or 'login'
            master_otp = '999999'
            try:
                phone_otp = PhoneOTP.objects.get(phone_number=phone)
            except PhoneOTP.DoesNotExist:
                return Response({'error': 'No OTP request found for this phone number.'}, status=status.HTTP_404_NOT_FOUND)

            if phone_otp.is_expired():
                return Response({'error': 'OTP has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

            if otp_input != phone_otp.otp and otp_input != master_otp:
                return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

            # OTP is valid; delete it
            phone_otp.delete()

            # Register or login based on the mode
            if mode == 'register':
                if CustomUser.objects.filter(phone_number=phone).exists():
                    return Response({'error': 'User already exists. Please login.'}, status=status.HTTP_400_BAD_REQUEST)
                # Create user without requiring email
                user = CustomUser.objects.create_user(phone_number=phone, email=None)
            elif mode == 'login':
                try:
                    user = CustomUser.objects.get(phone_number=phone)
                except CustomUser.DoesNotExist:
                    return Response({'error': 'User not found. Please register.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': 'Invalid mode. Must be "register" or "login".'}, status=status.HTTP_400_BAD_REQUEST)

            # Generate JWT token
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': f'User {mode}ed and authenticated successfully.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_id': user.id,
                'phone_number': user.phone_number
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CompleteUserRegistrationView(APIView):
    def post(self, request):
        serializer = CompleteUserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(id=serializer.validated_data['user_id'])
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

            try:
                serializer.update(user, serializer.validated_data)
            except IntegrityError as e:
                if 'email' in str(e):
                    return Response({'error': 'Email already exists.'}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'error': 'Integrity error occurred.'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'message': 'User registration completed successfully.'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class PhoneLoginView(APIView):
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_id': user.id,
                'phone_number': user.phone_number,
                'name': user.name,
                'email': user.email
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UpdateZoneAreaView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        serializer = UpdateZoneAreaSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Zone and Area updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CategoryListAPIView(ListAPIView):
    queryset = Categories.objects.all()
    serializer_class = CategorySerializer


class ProductListWithSingleVariantAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        products = Product.objects.filter(is_active=True, deleted=False).prefetch_related('variants', 'flash_sales','images')
        serializer = ProductWithFirstVariantSerializer(products, many=True,context={'request': request})
        return Response(serializer.data)
    
class ProductDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id, is_active=True, deleted=False)
        
        # Main product details
        serializer = ProductDetailSerializer(product, context={'request': request})

        # Similar products
        similar_products = Product.objects.filter(
            category=product.category,
            is_active=True,
            deleted=False
        ).exclude(id=product.id).order_by('?')[:4]

        similar_serializer = ProductSimpleSerializer(similar_products, many=True, context={'request': request})

        # Recent 6 ratings
        recent_ratings = product.ratings.select_related('user').order_by('-created_at')[:6]
        rating_serializer = RecentProductRatingSerializer(recent_ratings, many=True)

        return Response({
            "product_detail": serializer.data,
            "similar_products": similar_serializer.data,
            "recent_ratings": rating_serializer.data
        })

    
class ProductsByCategoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, category_id):
        try:
            category = Categories.objects.get(id=category_id)
        except Categories.DoesNotExist:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

        products = Product.objects.filter(category=category, is_active=True, deleted=False).prefetch_related('variants', 'images')

        serializer = ProductWithFirstVariantSerializer(products, many=True, context={'request': request})
        return Response({
            "category": category.category_name,
            "products": serializer.data
        }, status=status.HTTP_200_OK)
    
class FavoriteProductListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get product instances from user's favorites
        favorite_products = Product.objects.filter(
            favorited_by__user=user,
            is_active=True,
            deleted=False
        ).prefetch_related('variants', 'flash_sales', 'images')

        serializer = ProductWithFirstVariantSerializer(
            favorite_products,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    

class BestSellingProductsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Aggregate total quantity sold per variant (only for delivered orders)
        top_variant_data = (
            OrderItem.objects
            .filter(order__status='delivered', variant__isnull=False)
            .values('variant__product')  # group by product
            .annotate(total_quantity_sold=Sum('quantity'))
            .order_by('-total_quantity_sold')[:10]
        )

        product_ids = [entry['variant__product'] for entry in top_variant_data]
        products = Product.objects.filter(id__in=product_ids)

        # Preserve order according to quantity sold
        ordered_products = sorted(products, key=lambda p: product_ids.index(p.id))

        serializer = ProductWithFirstVariantSerializer(ordered_products, many=True, context={'request': request})

        return Response({
            "success": True,
            "top_products": serializer.data
        })
    
class AddOrUpdateProductRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProductRatingSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.validated_data['product']
            rating = serializer.validated_data['rating']

            # Update or create rating without review
            rating_obj, created = ProductRating.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating': rating
                }
            )
            return Response({
                "message": "Rating submitted successfully." if created else "Rating updated successfully."
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductSearchAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.GET.get('q', '')

        products = Product.objects.filter(
            Q(display_name__icontains=query) |
            Q(brand_name__icontains=query) |
            Q(SAP_code__icontains=query),
            is_active=True,
            deleted=False
        )

        serializer = ProductDetailSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
    

class OnboardingImageListAPIView(APIView):
    def get(self, request):
        images = OnboardingImage.objects.all().order_by('-uploaded_at')
        serializer = OnboardingImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)