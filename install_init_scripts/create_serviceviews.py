from containers import *

# Upload Thumbnails
ths_list = [{'button_jupyter': 'images/t_jupyter.png'}, {'button_rstudio': 'images/t_rstudio.png'}, {'button_plotly': 'images/t_plotly.png'}, {'button_shiny': 'images/t_shiny.png'}]
while ths_list:
    ths = ths_list.pop(0)
    name = ths.keys()[0]
    Thumbnails(imagecode=ths[name], name=name).get_or_create()
    print(f"Created Thumbnail {name}")

svs = [{'name': 'jupyter', 'proxy': 'jupyter', 'suffix': 'tree', 'openable': True, 'pass_token': True, 'icon': 'button_jupyter'},
    {'name': 'rstudio', 'proxy': 'rstudio', 'suffix': 'auth-sign-in', 'openable': True, 'pass_token': False, 'icon': 'button_rstudio'},
    {'name': 'testurl', 'proxy': 'testurl', 'suffix': '', 'openable': False, 'pass_token': False, 'icon': 'button_plotly'},
    {'name': 'shiny', 'proxy': 'shiny', 'suffix': '', 'openable': False, 'pass_token': False, 'icon': 'button_shiny'},
]

for sv in svs:
    svc = ServiceView(name=sv['name'], proxy=Proxy.objects.filter(name=sv['proxy']).first(), suffix=sv['suffix'], openable=sv['openable'], pass_token=sv['pass_token'], icon=sv['icon'])
    svc.get_or_create()
    print(f"Created ServiceView {svc.name}")