import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Spot, Tag, Ingredient

from traveler.serializers import SpotSerializer, SpotDetailSerializer


SPOTS_URL = reverse('traveler:spot-list')


def image_upload_url(spot_id):
    """Return url for spot image upload"""
    return reverse('traveler:spot-upload-image', args=[spot_id])


def detail_url(spot_id):
    """Return spot detail URL"""
    return reverse('traveler:spot-detail', args=[spot_id])


def sample_tag(user, name='Main course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Cinnamon'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_spot(user, **params):
    """Create and return a sample spot"""
    defaults = {
        'title': 'Sample spot',
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
        spot.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(spot.id)
        res = self.client.get(url)

        serializer = SpotDetailSerializer(spot)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_spot(self):
        """Test creating spot"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 5.00
        }
        res = self.client.post(SPOTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        spot = Spot.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(spot, key))

    def test_create_spot_with_tags(self):
        """Test creating a spot with tags"""
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')
        payload = {
            'title': 'Avocado lime cake',
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

    def test_create_spot_with_ingredients(self):
        """Test creating spot with ingredients"""
        ingredient1 = sample_ingredient(user=self.user, name='Prawns')
        ingredient2 = sample_ingredient(user=self.user, name='Ginger')
        payload = {
            'title': 'Thai prawn red curry',
            'ingredients': [ingredient1.id, ingredient2.id],
            'time_minutes': 20,
            'price': 7.00
        }
        res = self.client.post(SPOTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        spot = Spot.objects.get(id=res.data['id'])
        ingredients = spot.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_spot(self):
        """Test updating a spot with patch"""
        spot = sample_spot(user=self.user)
        spot.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')

        payload = {'title': 'Chicken tikka', 'tags': [new_tag.id]}
        url = detail_url(spot.id)
        self.client.patch(url, payload)

        spot.refresh_from_db()
        self.assertEqual(spot.title, payload['title'])
        tags = spot.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_spot(self):
        """Test updating a spot with put"""
        spot = sample_spot(user=self.user)
        spot.tags.add(sample_tag(user=self.user))
        payload = {
            'title': 'Spaaaa',
            'time_minutes': 25,
            'price': 5.00
        }
        url = detail_url(spot.id)
        self.client.put(url, payload)

        spot.refresh_from_db()
        self.assertEqual(spot.title, payload['title'])
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
        """Test uploading an email to spot"""
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
        spot1 = sample_spot(user=self.user, title='Thai vegtable curry')
        spot2 = sample_spot(user=self.user, title='Aubergine with tahini')
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Vegetarian')
        spot1.tags.add(tag1)
        spot2.tags.add(tag2)
        spot3 = sample_spot(user=self.user, title='Fish and chips')

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

    def test_filter_spots_by_ingredients(self):
        """Test returning spots with specific ingredients"""
        spot1 = sample_spot(user=self.user, title='Posh beans on toast')
        spot2 = sample_spot(user=self.user, title='Chicken')
        ingredient1 = sample_ingredient(user=self.user, name='Feta cheese')
        ingredient2 = sample_ingredient(user=self.user, name='hicken')
        spot1.ingredients.add(ingredient1)
        spot2.ingredients.add(ingredient2)
        spot3 = sample_spot(user=self.user, title='Steak and shrooms')

        res = self.client.get(
            SPOTS_URL,
            {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        )

        serializer1 = SpotSerializer(spot1)
        serializer2 = SpotSerializer(spot2)
        serializer3 = SpotSerializer(spot3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)
