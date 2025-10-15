from container.models import *

images = Image.objects.all()
for image in images:
    if 'jupyter' in image.name:
        pr = Proxy.objects.filter(name='jupyter').first()
        pib, created = ProxyImageBinding.objects.get_or_create(image=image, proxy=pr)
        pib.save()
        print(f"Created ProxyImageBinding for Image ID {image.id}")
    elif 'rstudio' in image.name:
        pr = Proxy.objects.filter(name='rstudio').first()
        pib, created = ProxyImageBinding.objects.get_or_create(image=image, proxy=pr)
        pib.save()
        print(f"Created ProxyImageBinding for Image ID {image.id}")
    else:
        print(f"ProxyImageBinding already exists for Image ID {image.id}")