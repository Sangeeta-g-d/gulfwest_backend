from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from orders.models import Order
from firebase_admin import messaging
from .serializers import DriverOrderSerializer,OrderDetailSerializer
from users.models import OrderDriverAssignment
from django.db.models import Sum, Count, Q
from users.models import DeviceToken

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
        print(f"➡️  Request to mark order #{order_id} delivered by user {request.user} (role={request.user.role})")

        # Try to fetch the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            print("❌ Order not found")
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        print(f"✅ Order found. Current status = {order.status}")

        # --- Only allow the driver assigned to this order ---
        if request.user.role == 'driver':
            da = getattr(order, "driver_assignment", None)
            print(f"🔎 Driver assignment = {da} (assigned_driver={getattr(da, 'driver', None)})")

            if not da or da.driver != request.user:
                print("❌ Driver mismatch or no driver assignment")
                return Response({'error': 'You are not assigned to this order.'}, status=status.HTTP_403_FORBIDDEN)

            # Optionally update payment_type if provided
            new_payment_type = request.data.get('payment_type')
            print(f"💳 new_payment_type from request = {new_payment_type}")

            if new_payment_type in dict(Order.PAYMENT_CHOICES):
                order.payment_type = new_payment_type
                print(f"✅ payment_type updated to {new_payment_type}")
            else:
                print("⚠️  invalid payment_type OR no payment_type provided - leaving unchanged")

        # Prevent double updates
        if order.status == 'delivered':
            print("ℹ️  Order already delivered – no update done")
            return Response(
                {'message': 'Order is already marked as delivered.'},
                status=status.HTTP_200_OK
            )

        # --- Perform the update ---
        order.status = 'delivered'
        order.save()
        print(f"✅ Order #{order.id} marked as delivered by driver {request.user.name}")

        # Send FCM notification to customer
        device_tokens = list(DeviceToken.objects.filter(
            user=order.user,
            is_active=True
        ).values_list("token", flat=True))

        if device_tokens:
            notification = messaging.Notification(
                title="🎉 Order Delivered",
                body=f"Your order #{order.id} has been successfully delivered."
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
                            "type": "order_delivered"
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
                    print(f"📨 Sent delivery notification to customer token {token[:10]}...")
                    success_count += 1
                except Exception as e:
                    print(f"❌ Error sending to customer token {token[:10]}...: {str(e)}")

            print(f"📊 Customer notification summary: {success_count}/{len(device_tokens)} succeeded")
        else:
            print("⚠️ No active device tokens found for customer")

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