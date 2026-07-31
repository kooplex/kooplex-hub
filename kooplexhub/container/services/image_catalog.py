from ..models import Image

class ImageCatalogService:
    @staticmethod
    def available_for_user(user):
        return (
            Image.objects
            .filter(
                imagetype=Image.ImageType.PROJECT,
                present=True,
            )
            .order_by("name")
        )
