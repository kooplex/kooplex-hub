from container.models import *
from hub.models import Thumbnail

# Upload Thumbnails
ths_list = [{'button_jupyter': 'images/t_jupyter.png'}, {'button_rstudio': 'images/t_rstudio.png'}, 
{'button_plotly': 'images/t_plotly.png'}, {'button_shiny': 'images/t_shiny.png'},
    {'button_test': 'images/t_test.png'}]


while ths_list:
    try:
        ths = ths_list.pop(0)
        name = list(ths.keys())[0]
        t, created = Thumbnail.objects.get_or_create(imagecode=open(f"../install_init_scripts/{ths[name]}", 'rb').read(), name=name)
        print(f"Created Thumbnail {name}")
    except Exception as e:
        print(f"Error creating Thumbnail {name}: {e}")
        continue

svs = [{'name': 'jupyter', 'proxy': 'jupyter', 'suffix': 'tree', 'openable': True, 'pass_token': True, 'icon': 'button_jupyter'},
    {'name': 'rstudio', 'proxy': 'rstudio', 'suffix': 'auth-sign-in', 'openable': True, 'pass_token': False, 'icon': 'button_rstudio'},
    {'name': 'testurl', 'proxy': 'testurl', 'suffix': '', 'openable': False, 'pass_token': False, 'icon': 'button_test'},
    {'name': 'shiny', 'proxy': 'shiny', 'suffix': '', 'openable': False, 'pass_token': False, 'icon': 'button_shiny'},
]

for sv in svs:
    try:
        svc, created = ServiceView.objects.get_or_create(name=sv['name'], 
            proxy=Proxy.objects.filter(name=sv['proxy']).first(), 
            suffix=sv['suffix'], openable=sv['openable'], 
            pass_token=sv['pass_token'], icon=Thumbnail.objects.filter(name=sv['icon']).first())
        print(f"Created ServiceView {sv['name']}")
    except Exception as e:
        print(f"Error creating ServiceView {sv['name']}: {e}")
        continue