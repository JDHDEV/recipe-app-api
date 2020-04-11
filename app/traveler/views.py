from graphene_django.views import GraphQLView
from rest_framework.decorators import action, authentication_classes, \
    permission_classes, api_view
from rest_framework.response import Response
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Tag, Location, Spot

from traveler import serializers


class DRFAuthenticatedGraphQLView(GraphQLView):
    # custom view for using DRF TokenAuthentication with graphene
    # GraphQL.as_view() all requests to Graphql endpoint will require token
    # for auth, obtained from DRF endpoint
    # https://github.com/graphql-python/graphene/issues/249
    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super(DRFAuthenticatedGraphQLView, cls).as_view(*args, **kwargs)
        view = permission_classes((IsAuthenticated,))(view)
        view = authentication_classes((TokenAuthentication,))(view)
        view = api_view(['POST'])(view)
        return view


class BaseSpotAttrViewSet(viewsets.GenericViewSet,
                          mixins.ListModelMixin,
                          mixins.CreateModelMixin):
    """Base viewset for user owner spot attributes"""
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """Return objects for the current authenticated user only"""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0))
        )
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(spot__isnull=False)

        return queryset.filter(
            user=self.request.user
        ).order_by('-name').distinct()

    def perform_create(self, serializer):
        """Create a new Spot Attr"""
        serializer.save(user=self.request.user)


class TagViewSet(BaseSpotAttrViewSet):
    """Manage tags in the database"""
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer


class LocationViewSet(BaseSpotAttrViewSet):
    """Manage locations in the database"""
    queryset = Location.objects.all()
    serializer_class = serializers.LocationSerializer


class SpotViewSet(viewsets.ModelViewSet):
    """Manage Spots in the database"""
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = Spot.objects.all()
    serializer_class = serializers.SpotSerializer

    def _params_to_ints(self, qs):
        """Convert a  list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(',')]

    def get_queryset(self):
        """Retrieve the spots for the authenticated user"""
        tags = self.request.query_params.get('tags')
        locations = self.request.query_params.get('locations')
        queryset = self.queryset
        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_ids)
        if locations:
            location_ids = self._params_to_ints(locations)
            queryset = queryset.filter(locations__id__in=location_ids)

        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'retrieve':
            return serializers.SpotDetailSerializer
        elif self.action == 'upload_image':
            return serializers.SpotImageSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        """Create a new spot"""
        serializer.save(user=self.request.user)

    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload an image to a spot"""
        spot = self.get_object()
        serializer = self.get_serializer(
            spot,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
