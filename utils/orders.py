from places.models import Place
from utils.geocoder import get_coordinates


def enrich_orders_with_restaurants(orders, menu_items, restaurant_objects):
    if not orders:
        return

    order_addresses = {order.address for order in orders}
    restaurant_addresses = {restaurant.address for restaurant in restaurant_objects.values() if getattr(restaurant, 'address', None)}
    all_addresses = order_addresses | restaurant_addresses

    existing_places = Place.objects.filter(address__in=all_addresses)
    address_to_coordinates = {place.address: place.coordinates for place in existing_places}

    new_places_to_create = []
    for address in all_addresses:
        if address not in address_to_coordinates:
            coordinates = get_coordinates(address)
            if coordinates:
                address_to_coordinates[address] = coordinates
                new_places_to_create.append(Place(address=address, coordinates=coordinates))

    if new_places_to_create:
        Place.objects.bulk_create(new_places_to_create, ignore_conflicts=True)

    for restaurant in restaurant_objects.values():
        if restaurant.address:
            restaurant.coordinates = restaurant.coordinates or address_to_coordinates.get(restaurant.address)

    for order in orders:
        order_coordinates = address_to_coordinates.get(order.address)
        order.possible_restaurants = order.get_possible_restaurants(
            menu_items, restaurant_objects, order_coordinates
        )
