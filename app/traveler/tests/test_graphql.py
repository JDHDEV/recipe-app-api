from graphene_django.utils.testing import GraphQLTestCase
from graphene.test import Client

from app.schema import schema

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from rest_framework import status

from core.models import Spot


def sample_spot(user, **params):
    """Create and return a sample spot"""
    defaults = {
        'title': 'Sample spot',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)

    return Spot.objects.create(user=user, **defaults)


class PublicGraphQLApiTests(GraphQLTestCase):
    """Test unauthenticated graphql API access"""

    GRAPHQL_SCHEMA = schema

    def test_auth_required(self):
        response = self.query(
            '''
            query {
            }
            '''
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class privateGraphQLApiTests(GraphQLTestCase):
    """Test authenticated graphql API access"""

    GRAPHQL_SCHEMA = schema

    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            'test@gmail.com',
            'testpass'
        )

    def test_allspots_graphql(self):
        """Test retrieving spots with graphql"""
        sample_spot(user=self.user)
        sample_spot(user=self.user)

        request = self.factory.get('graphql/')

        # Recall that middleware are not supported. You can simulate a
        # logged-in user by setting request.user manually.
        request.user = self.user

        client = Client(schema)
        executed = client.execute(
            '''{ allSpots { title } } ''', context=request
        )

        self.assertIn('data', executed)
        data = executed.get('data')

        self.assertIn('allSpots', data)
        allSpots = data.get('allSpots')

        self.assertEqual(allSpots[0].get('title'), "Sample spot")
        self.assertEqual(allSpots[1].get('title'), "Sample spot")
