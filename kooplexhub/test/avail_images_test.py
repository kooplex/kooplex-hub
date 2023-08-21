from container.models import Container, Image
from hub.models import User
from time import sleep

# Get a test user
username = "wfct0p"
u = User.objects.get( username=username)

# Get all used images 
allc = Container.objects.all()

list_images = []
for c in allc:
    list_images.append(c.image)

# and/or enabled images
list_images.extend(Image.objects.filter(present=True))

set_images = set(list_images)

print("Create and launch itest containers %d"%len(set_images))
list_new_containers = []
# Create test environments wtih the filtered imagetypes
for image in set_images:
    cname = "test-"+username+"-"+image.name[-20:]
    new_c = Container(name=cname, user = u, image=image)
    list_new_containers.append(new_c)
    new_c.start()
    sleep(5)

print("Waiting for containers to start")
sleep(20)
for c in list_new_containers:
    print(c.check_state())
    

sleep(20)

print("Check test container state:")
for c in list_new_containers:
    istherelog = c.check_state(retrieve_log=True)['podlog'].find("KooplexUs") > -1
    print(c.image.present, c.name, istherelog)

print("Stop test containers")
for c in list_new_containers:
    c.stop()
    sleep(2)

print("Delete test containers")
for c in list_new_containers:
    c.delete()
    sleep(2)


