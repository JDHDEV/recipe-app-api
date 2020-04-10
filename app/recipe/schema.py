import graphene

from graphene_django.types import DjangoObjectType
from core.models import Recipe, Ingredient

class RecipeType(DjangoObjectType):
    class Meta:
        model = Recipe

    price_rating = graphene.String()

    def resolve_price_rating(self, info):
        return "Reasonable" if self.price < 20 else "Expensive"

class IngredientType(DjangoObjectType):
    class Meta:
        model = Ingredient

class Query(graphene.ObjectType):
    all_recipes = graphene.List(RecipeType)
    recipe = graphene.Field(RecipeType, id=graphene.Int(),
             title=graphene.String())

    def resolve_all_recipes(self, info, **kwargs):
        user = info.context.user
        #if not user.is_authenticated:
            #raise Exception('Auth Fail')
            
        #"""Return objects for the current authenticated user only"""
        #assigned_only = bool(
        #    int(self.request.query_params.get('assigned_only', 0))
        #)
        #queryset = self.queryset
        #if assigned_only:
        #    queryset = queryset.filter(recipe__isnull=False)

        return Recipe.objects.all()

    def resolve_recipe(self, info, **kwargs):
        id = kwargs.get('id')

        if id is not None:
            return Recipe.objects.get(pk=id)

        title = kwargs.get('title')

        if title is not None:
            return Recipe.objects.get(title=title)

        return None
