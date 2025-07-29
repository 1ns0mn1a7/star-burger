import time
import requests
from django.conf import settings
from places.models import Place


YANDEX_API_URL = "https://geocode-maps.yandex.ru/1.x/"


def get_coordinates(address: str, retries: int = 3, delay: float = 0.5):
    if not address:
        return None

    place, created = Place.objects.get_or_create(address=address)
    if place.coordinates:
        return tuple(place.coordinates)

    params = {
        "apikey": settings.YANDEX_GEOCODER_API_KEY,
        "geocode": address,
        "format": "json",
    }
    for attempt in range(retries):
        try:
            response = requests.get(YANDEX_API_URL, params=params, timeout=5)
            response.raise_for_status()
            response_json = response.json()

            point = response_json["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
            longitude, latitude = map(float, point.split())
            coordinates = [latitude, longitude]

            place.coordinates = coordinates
            place.save(update_fields=['coordinates'])
            return tuple(coordinates)

        except (IndexError, KeyError):
            return None
        except requests.exceptions.RequestException:
            time.sleep(delay)
    return None
