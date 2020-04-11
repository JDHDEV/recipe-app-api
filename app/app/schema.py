import graphene
import traveler.schema


class Query(traveler.schema.Query, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
