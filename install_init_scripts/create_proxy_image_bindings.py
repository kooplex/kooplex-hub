from containers import *

images = Images.objects.all()
for image in images:
    if 'jupyter' in image.name:
        pr = Proxy.objects.filter(name='jupyter').first()
        ProxyImageBinding(image=image, proxy=pr).get_or_create()
        print(f"Created ProxyImageBinding for Image ID {image.id}")
    else:
        print(f"ProxyImageBinding already exists for Image ID {image.id}")