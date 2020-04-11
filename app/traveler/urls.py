from django.urls import path, include
from rest_framework.routers import DefaultRouter

from traveler import views


router = DefaultRouter()
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngredientViewSet)
router.register('spots', views.SpotViewSet)

app_name = 'traveler'

urlpatterns = [
    path('', include(router.urls))
]
