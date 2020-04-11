from rest_framework import serializers

from core.models import Tag, Location, Spot


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tag objects"""

    class Meta:
        model = Tag
        fields = ('id', 'name')
        read_only_fields = ('id',)


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for location objects"""

    class Meta:
        model = Location
        fields = ('id', 'name')
        read_only_fields = ('id',)


class SpotSerializer(serializers.ModelSerializer):
    """Serializer a spot"""
    locations = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Location.objects.all()
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )

    class Meta:
        model = Spot
        fields = (
            'id', 'title', 'locations', 'tags', 'time_minutes',
            'price', 'link',
        )
        read_only_fields = ('id',)


class SpotDetailSerializer(SpotSerializer):
    """Serialize a spot detail object"""
    locations = LocationSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)


class SpotImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to spots"""

    class Meta:
        model = Spot
        fields = ('id', 'image')
        read_only_fields = ('id',)
