from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from orders.models import Order
from .serializers import DriverOrderSerializer,OrderDetailSerializer

class DriverOrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'driver':
            return Response({'error': 'Only drivers can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)

        orders = Order.objects.filter(driver_assignment__driver=user).order_by('-placed_at')

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

        serializer = OrderDetailSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class MarkOrderDeliveredAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Optional: Restrict to driver assigned to this order
        if request.user.role == 'driver':
            if not hasattr(order, 'driver_assignment') or order.driver_assignment.driver != request.user:
                return Response({'error': 'You are not assigned to this order.'}, status=status.HTTP_403_FORBIDDEN)

        if order.status == 'delivered':
            return Response({'message': 'Order is already marked as delivered.'}, status=status.HTTP_200_OK)

        order.status = 'delivered'
        order.save()

        return Response({'message': f'Order #{order.id} marked as delivered.'}, status=status.HTTP_200_OK)