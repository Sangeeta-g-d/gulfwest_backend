from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from orders.models import Order
from .serializers import DriverOrderSerializer,OrderDetailSerializer
from users.models import OrderDriverAssignment
from django.db.models import Sum, Count, Q

class DriverOrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'driver':
            return Response({'error': 'Only drivers can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)

        # Only get shipped orders assigned to this driver
        orders = Order.objects.filter(
            driver_assignment__driver=user,
            status='shipped'
        ).order_by('-placed_at')

        serializer = DriverOrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'driver':
            if not hasattr(order, 'driver_assignment') or order.driver_assignment.driver != request.user:
                return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        serializer = OrderDetailSerializer(order, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)
    

class MarkOrderDeliveredAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Only allow assigned driver to update
        if request.user.role == 'driver':
            if not hasattr(order, 'driver_assignment') or order.driver_assignment.driver != request.user:
                return Response({'error': 'You are not assigned to this order.'}, status=status.HTTP_403_FORBIDDEN)

            # ✅ Optionally update payment_type if provided
            new_payment_type = request.data.get('payment_type')
            if new_payment_type in dict(Order.PAYMENT_CHOICES):
                order.payment_type = new_payment_type

        if order.status == 'delivered':
            return Response({'message': 'Order is already marked as delivered.'}, status=status.HTTP_200_OK)

        order.status = 'delivered'
        order.save()

        return Response({
            'message': f'Order #{order.id} marked as delivered.',
            'payment_type': order.payment_type
        }, status=status.HTTP_200_OK)

class DriverOrderHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'driver':
            return Response({'error': 'Only drivers can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)

        # Get delivered orders assigned to this driver
        delivered_orders = Order.objects.filter(
            driver_assignment__driver=user,
            status='delivered'
        ).order_by('-placed_at')

        serializer = DriverOrderSerializer(delivered_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class DriverStatisticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'driver':
            return Response({'error': 'Only drivers can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)

        orders = Order.objects.filter(driver_assignment__driver=user)

        total_assigned = orders.count()
        delivered_count = orders.filter(status='delivered').count()
        pending_count = orders.filter(status__in=['pending', 'confirmed', 'shipped']).count()

        return Response({
            'total_assigned_orders': total_assigned,
            'delivered_orders': delivered_count,
            'pending_orders': pending_count,
        })
    

class DriverProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'driver':
            return Response({'error': 'Access denied. Only drivers can access this info.'}, status=403)

        data = {
            'email': user.email,
            'phone_number': user.phone_number,
            'name': user.name,
        }

        return Response(data, status=200)