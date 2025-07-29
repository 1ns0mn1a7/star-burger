from places.models import Place
from utils.geocoder import get_coordinates


def enrich_orders_with_restaurants(orders, menu_items, restaurants):
    if not orders:
        return

    order_addresses = {o.address for o in orders}
    restaurant_addresses = {r.address for r in restaurants.values() if getattr(r, 'address', None)}
    all_addresses = order_addresses | restaurant_addresses

    places = Place.objects.filter(address__in=all_addresses)
    places_dict = {p.address: p.coordinates for p in places}

    new_places = []
    for address in all_addresses:
        if address not in places_dict:
            coords = get_coordinates(address)
            if coords:
                places_dict[address] = coords
                new_places.append(Place(address=address, coordinates=coords))

    if new_places:
        Place.objects.bulk_create(new_places, ignore_conflicts=True)

    for r in restaurants.values():
        if r.address:
            r.coordinates = r.coordinates or places_dict.get(r.address)

    for order in orders:
        coordinates = places_dict.get(order.address)
        order.possible_restaurants = order.get_possible_restaurants(
            menu_items, restaurants, coordinates
        )
