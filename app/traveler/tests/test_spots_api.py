import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Spot, Tag, Location

from traveler.serializers import SpotSerializer, SpotDetailSerializer


SPOTS_URL = reverse('traveler:spot-list')


def image_upload_url(spot_id):
    """Return url for spot image upload"""
    return reverse('traveler:spot-upload-image', args=[spot_id])


def detail_url(spot_id):
    """Return spot detail URL"""
    return reverse('traveler:spot-detail', args=[spot_id])


def sample_tag(user, name='Social'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_location(user, name='San Francisco'):
    """Create and return a sample location"""
    return Location.objects.create(user=user, name=name)


def sample_spot(user, **params):
    """Create and return a sample spot"""
    defaults = {
        'name': 'Sample spot',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)

    return Spot.objects.create(user=user, **defaults)


class PublicSpotApiTests(TestCase):
    """Test unauthenticated spot API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(SPOTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class privateSpotApiTests(TestCase):
    """Test authenticated spot API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@gmail.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_spots(self):
        """Test retrieving a list of spots"""
        sample_spot(user=self.user)
        sample_spot(user=self.user)

        res = self.client.get(SPOTS_URL)

        spots = Spot.objects.all().order_by('-id')
        serializer = SpotSerializer(spots, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_spots_limited_to_user(self):
        """Test retrieving spots for user"""
        user2 = get_user_model().objects.create_user(
            'test2@gmail.com',
            'testpass'
        )
        sample_spot(user=user2)
        sample_spot(user=self.user)

        res = self.client.get(SPOTS_URL)

        spots = Spot.objects.filter(user=self.user)
        serializer = SpotSerializer(spots, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_spot_detail(self):
        """Test viewing a spot detail"""
        spot = sample_spot(user=self.user)
        spot.tags.add(sample_tag(user=self.user))
        spot.locations.add(sample_location(user=self.user))

        url = detail_url(spot.id)
        res = self.client.get(url)

        serializer = SpotDetailSerializer(spot)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_spot(self):
        """Test creating spot"""
        payload = {
            'name': 'Small Cafe',
            'time_minutes': 30,
            'price': 10.00
        }
        res = self.client.post(SPOTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        spot = Spot.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(spot, key))

    def test_create_spot_with_tags(self):
        """Test creating a spot with tags"""
        tag1 = sample_tag(user=self.user, name='Surf')
        tag2 = sample_tag(user=self.user, name='Swim')
        payload = {
            'name': 'Stand Up Paddleboarding',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 20.00
        }
        res = self.client.post(SPOTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        spot = Spot.objects.get(id=res.data['id'])
        tags = spot.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_spot_with_locations(self):
        """Test creating spot with locations"""
        location1 = sample_location(user=self.user, name='Columbia')
        location2 = sample_location(user=self.user, name='Medina')
        payload = {
            'name': 'Salsa Dancing',
            'locations': [location1.id, location2.id],
            'time_minutes': 20,
            'price': 10.00
        }
        res = self.client.post(SPOTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        spot = Spot.objects.get(id=res.data['id'])
        locations = spot.locations.all()
        self.assertEqual(locations.count(), 2)
        self.assertIn(location1, locations)
        self.assertIn(location2, locations)

    def test_partial_update_spot(self):
        """Test updating a spot with patch"""
        spot = sample_spot(user=self.user)
        spot.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Music')

        payload = {'name': 'Concert Venue', 'tags': [new_tag.id]}
        url = detail_url(spot.id)
        self.client.patch(url, payload)

        spot.refresh_from_db()
        self.assertEqual(spot.name, payload['name'])
        tags = spot.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_spot(self):
        """Test updating a spot with put"""
        spot = sample_spot(user=self.user)
        spot.tags.add(sample_tag(user=self.user))
        payload = {
            'name': 'Spa',
            'time_minutes': 60,
            'price': 5.00
        }
        url = detail_url(spot.id)
        self.client.put(url, payload)

        spot.refresh_from_db()
        self.assertEqual(spot.name, payload['name'])
        self.assertEqual(spot.time_minutes, payload['time_minutes'])
        self.assertEqual(spot.price, payload['price'])
        tags = spot.tags.all()
        self.assertEqual(len(tags), 0)


class SpotImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@gmail.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)
        self.spot = sample_spot(user=self.user)

    def tearDown(self):
        self.spot.image.delete()

    def test_upload_image_to_spot(self):
        """Test uploading an image to spot"""
        url = image_upload_url(self.spot.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')

        self.spot.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.spot.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.spot.id)
        res = self.client.post(url, {'image': 'notimage'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_spots_by_tags(self):
        """Test returning spots with specific tags"""
        spot1 = sample_spot(user=self.user, name='Dance Club')
        spot2 = sample_spot(user=self.user, name='Concert Hall')
        tag1 = sample_tag(user=self.user, name='Dance')
        tag2 = sample_tag(user=self.user, name='Music')
        spot1.tags.add(tag1)
        spot2.tags.add(tag2)
        spot3 = sample_spot(user=self.user, name='Small Diner')

        res = self.client.get(
            SPOTS_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )

        serializer1 = SpotSerializer(spot1)
        serializer2 = SpotSerializer(spot2)
        serializer3 = SpotSerializer(spot3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_spots_by_locations(self):
        """Test returning spots with specific locations"""
        spot1 = sample_spot(user=self.user, name='Zip Line')
        spot2 = sample_spot(user=self.user, name='Rock Climbing')
        location1 = sample_location(user=self.user, name='Costa Rica')
        location2 = sample_location(user=self.user, name='South America')
        spot1.locations.add(location1)
        spot2.locations.add(location2)
        spot3 = sample_spot(user=self.user, name='Local Bar')

        res = self.client.get(
            SPOTS_URL,
            {'locations': f'{location1.id},{location2.id}'}
        )

        serializer1 = SpotSerializer(spot1)
        serializer2 = SpotSerializer(spot2)
        serializer3 = SpotSerializer(spot3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)
