import json
from django.http import JsonResponse
from django.templatetags.static import static

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Product
from .models import Order
from .models import OrderItem


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


class RegisterOrderView(APIView):
    def post(self, request):
        try:
            order_payload = request.data

            order = Order.objects.create(
                firstname=order_payload['firstname'],
                lastname=order_payload['lastname'],
                phonenumber=order_payload['phonenumber'],
                address=order_payload['address']
            )

            for item in order_payload['products']:
                product = Product.objects.get(id=item['product'])
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity']
                )

            return Response({'status': 'ok', 'order_id': order.id}, status=status.HTTP_201_CREATED)
        except Exception as error:           
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        