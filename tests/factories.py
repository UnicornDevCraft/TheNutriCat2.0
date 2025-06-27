import factory
from factory.alchemy import SQLAlchemyModelFactory
from nutri_app.models import Recipe
from faker import Faker

fake = Faker()

class RecipeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Recipe
        sqlalchemy_session = None  # Injected via pytest fixture

    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=3))
    servings = factory.Iterator([1, 2, 4])
    prep_time = factory.LazyAttribute(lambda _: fake.random_int(min=5, max=60))
    cook_time = factory.LazyAttribute(lambda _: fake.random_int(min=10, max=120))
    local_image_path = factory.LazyAttribute(lambda _: fake.file_path(extension='jpg'))
    quality_img_URL = factory.LazyAttribute(lambda _: fake.image_url())
    compressed_img_URL = factory.LazyAttribute(lambda _: fake.image_url())
