import graphene

from graphene_django.types import DjangoObjectType
from core.models import Spot, Location


class SpotType(DjangoObjectType):
    class Meta:
        model = Spot

    price_rating = graphene.String()

    def resolve_price_rating(self, info):
        return "Reasonable" if self.price < 20 else "Expensive"


class LocationType(DjangoObjectType):
    class Meta:
        model = Location


class Query(graphene.ObjectType):
    all_spots = graphene.List(SpotType)
    spot = graphene.Field(SpotType, id=graphene.Int(),
                          name=graphene.String())

    def resolve_all_spots(self, info, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception('Auth Fail')

        #"""Return objects for the current authenticated user only"""
        #assigned_only = bool(
        #    int(self.request.query_params.get('assigned_only', 0))
        #)
        #queryset = self.queryset
        #if assigned_only:
        #    queryset = queryset.filter(spot__isnull=False)

        return Spot.objects.all()

    def resolve_spot(self, info, **kwargs):
        id = kwargs.get('id')

        if id is not None:
            return Spot.objects.get(pk=id)

        name = kwargs.get('name')

        if name is not None:
            return Spot.objects.get(name=name)

        return None
