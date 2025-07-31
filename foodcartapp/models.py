from django.db import models
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField

from django.db.models import Sum, F
from collections import Counter
from geopy.distance import geodesic


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )
    coordinates = models.JSONField(
        'координаты',
        null=True,
        blank=True,
        help_text='Широта и долгота в формате [lat, lon]'
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def with_total_price(self):
        return self.annotate(
            total_price=Sum(
                F('items__quantity') * F('items__product__price')
            )
        )


class Order(models.Model):
    CASH = 'cash'
    ELECTRONIC = 'electronic'
    PAYMENT_METHOD_CHOICES = [
        (CASH, 'Наличные'),
        (ELECTRONIC, 'Картой'),
    ]

    STATUS_UNPROCESSED = 'unprocessed'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_PREPARING = 'preparing'
    STATUS_DELIVERING = 'delivering'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_UNPROCESSED, 'Необработанный'),
        (STATUS_CONFIRMED, 'Подтвержден'),
        (STATUS_PREPARING, 'Готовится'),
        (STATUS_DELIVERING, 'Доставляется'),
        (STATUS_COMPLETED, 'Завершен'),
    ]

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UNPROCESSED,
        db_index=True
    )
    payment_method = models.CharField(
        'Способ оплаты',
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=CASH,
    )
    cooking_restaurant = models.ForeignKey(
        'Restaurant',
        verbose_name='Готовит ресторан',
        related_name='orders',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    firstname = models.CharField('Имя', max_length=20, db_index=True)
    lastname = models.CharField('Фамилия', max_length=30, db_index=True)
    phonenumber = PhoneNumberField('Телефон', db_index=True)
    address = models.CharField('Адрес', max_length=200)
    created_at = models.DateTimeField('Создан', auto_now_add=True, db_index=True)
    called_at = models.DateTimeField('Дата звонка', null=True, blank=True)
    delivered_at = models.DateTimeField('Дата доставки', null=True, blank=True)
    comment = models.TextField('Комментарий', blank=True)

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        ordering = ['-created_at']

    def get_possible_restaurants(self, restaurant_menu_items, restaurants, coordinates=None):
        order_product_ids = {item.product_id for item in self.items.all()}

        restaurant_product_counts = Counter(
            menu_item['restaurant_id']
            for menu_item in restaurant_menu_items
            if menu_item['product_id'] in order_product_ids
        )

        full_restaurant_ids = [
            restaurant_id
            for restaurant_id, count in restaurant_product_counts.items()
            if count == len(order_product_ids)
        ]

        possible_restaurants = []
        for restaurant_id in full_restaurant_ids:
            restaurant = restaurants.get(restaurant_id)
            restaurant_name = getattr(restaurant, 'name', 'Неизвестный ресторан')
            restaurant_coordinates = getattr(restaurant, 'coordinates', None)

            distance_km = None
            if coordinates and restaurant_coordinates:
                try:
                    client_coords = tuple(map(float, coordinates))
                    rest_coords = tuple(map(float, restaurant_coordinates))
                    distance_km = round(geodesic(client_coords, rest_coords).kilometers, 2)
                except Exception as error:
                    print(f"Ошибка расчёта расстояния для заказа {self.id}: {error}")

            possible_restaurants.append({
                'id': restaurant_id,
                'name': restaurant_name,
                'distance': distance_km
            })

        possible_restaurants.sort(key=lambda x: x['distance'] if x['distance'] is not None else 999999)
        return possible_restaurants

    def save(self, *args, **kwargs):
        if self.cooking_restaurant and self.status == self.STATUS_UNPROCESSED:
            self.status = self.STATUS_PREPARING
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Заказ {self.id} от {self.firstname} {self.lastname} ({self.created_at})"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        verbose_name='заказ',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        related_name='order_items',
        verbose_name='товар',
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField('количество', validators=[MinValueValidator(1)])
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'позиция заказа'
        verbose_name_plural = 'позиция заказа'

    def save(self, *args, **kwargs):
        if self._state.adding and self.price in (None, 0):
            self.price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"
