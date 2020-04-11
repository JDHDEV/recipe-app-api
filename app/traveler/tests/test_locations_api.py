from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Location, Spot

from traveler.serializers import LocationSerializer


LOCATIONS_URL = reverse('traveler:location-list')


class PublicLocationsApiTests(TestCase):
    """Test the publicly available locations API"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required to access the endpoint"""
        res = self.client.get(LOCATIONS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateLocationsApiTests(TestCase):
    """Test the private locations API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@gmail.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_location_list(self):
        """Test retrieving a list of locations"""
        Location.objects.create(user=self.user, name='Kale')
        Location.objects.create(user=self.user, name='Salt')

        res = self.client.get(LOCATIONS_URL)

        locations = Location.objects.all().order_by('-name')
        serializer = LocationSerializer(locations, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_location_limited_to_user(self):
        """Test the locations for the authenticated user are returned"""
        user2 = get_user_model().objects.create_user(
            'test2@gmail.com',
            'testpass'
        )
        Location.objects.create(user=user2, name='Vinegar')

        location = Location.objects.create(user=self.user, name='Tumeric')

        res = self.client.get(LOCATIONS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], location.name)

    def test_create_location_successful(self):
        """Test create a new location"""
        payload = {'name': 'Cabbage'}
        self.client.post(LOCATIONS_URL, payload)

        exists = Location.objects.filter(
            user=self.user,
            name=payload['name'],
        ).exists()
        self.assertTrue(exists)

    def test_create_location_invalid(self):
        """Test creating invalid location fails"""
        payload = {'name': ''}
        res = self.client.post(LOCATIONS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_locations_assigned_to_spots(self):
        """Test filtering locations by those assigned to spots"""
        location1 = Location.objects.create(
            user=self.user, name='Apples'
        )
        location2 = Location.objects.create(
            user=self.user, name='Turkey'
        )
        spot = Spot.objects.create(
            title='Apple crumble',
            time_minutes=5,
            price=10.00,
            user=self.user
        )
        spot.locations.add(location1)

        res = self.client.get(LOCATIONS_URL, {'assigned_only': 1})

        serializer1 = LocationSerializer(location1)
        serializer2 = LocationSerializer(location2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_locations_assigned_unique(self):
        """Test filtering locations by assigned returns unique items"""
        location = Location.objects.create(
            user=self.user, name='Eggs'
        )
        Location.objects.create(
            user=self.user, name='Cheese'
        )
        spot1 = Spot.objects.create(
            title='Eggs scrambled',
            time_minutes=5,
            price=3.00,
            user=self.user
        )
        spot1.locations.add(location)
        spot2 = Spot.objects.create(
            title='Eggs on toast',
            time_minutes=20,
            price=2.00,
            user=self.user
        )
        spot2.locations.add(location)

        res = self.client.get(LOCATIONS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
