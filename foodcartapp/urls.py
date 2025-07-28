from django.urls import path

from .views import product_list_api, banners_list_api, RegisterOrderView


app_name = "foodcartapp"

urlpatterns = [
    path('products/', product_list_api),
    path('banners/', banners_list_api),
    path('order/', RegisterOrderView.as_view()),
]
