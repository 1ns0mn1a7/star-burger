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
        order_payload = request.data

        try:
            products = self._validate_products(order_payload.get('products'))
        except ValueError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.create(
                firstname=order_payload['firstname'],
                lastname=order_payload['lastname'],
                phonenumber=order_payload['phonenumber'],
                address=order_payload['address']
            )
        except KeyError as error:
            return Response(
                {'error': f'Отсутствует обязательное поле: {error.args[0]}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        self._add_order_items(order, products)
        return Response({'status': 'ok', 'order_id': order.id}, status=status.HTTP_201_CREATED)

    def _validate_products(self, products):
        if products is None:
            raise ValueError('products: Обязательное поле.')
        if not isinstance(products, list):
            raise ValueError(f'products: Ожидался list со значениями, но был получен "{type(products).__name__}".')
        if not products:
            raise ValueError('products: Список не должен быть пустым.')

        validated = []
        for index, item in enumerate(products, start=1):
            try:
                product_id = int(item['product'])
                quantity = int(item['quantity'])
            except (KeyError, ValueError):
                raise ValueError(f'Неверные данные в товаре №{index}.')

            if quantity <= 0:
                raise ValueError(f'Количество товара №{index} должно быть больше 0.')
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                raise ValueError(f'Товар с id={product_id} не найден.')

            validated.append((product, quantity))
        return validated

    def _add_order_items(self, order, products):
        for product, quantity in products:
            OrderItem.objects.create(order=order, product=product, quantity=quantity)
