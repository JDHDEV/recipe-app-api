from graphene_django.utils.testing import GraphQLTestCase
from graphene.test import Client

from app.schema import schema

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from rest_framework import status

from core.models import Recipe


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


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

    def test_allrecipes_graphql(self):
        """Test retrieving recipes with graphql"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        request = self.factory.get('graphql/')

        # Recall that middleware are not supported. You can simulate a
        # logged-in user by setting request.user manually.
        request.user = self.user

        client = Client(schema)
        executed = client.execute(
            '''{ allRecipes { title } } ''', context=request
        )

        self.assertIn('data', executed)
        data = executed.get('data')

        self.assertIn('allRecipes', data)
        allRecipes = data.get('allRecipes')

        self.assertEqual(allRecipes[0].get('title'), "Sample recipe")
        self.assertEqual(allRecipes[1].get('title'), "Sample recipe")
