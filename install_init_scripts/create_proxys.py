from container.models import *

ps = [{'name': 'jupyter', 'port': 8000, 'basepath': 'notebook/{container.label}', 'svc_proto': 'http', 'svc_hostname': '{container.label}', 'register': True},
      {'name': 'rstudio', 'port': 8000, 'basepath': 'notebook/{container.label}', 'svc_proto': 'http', 'svc_hostname': '{container.label}', 'register': True},
      {'name': 'shiny', 'port': 9000, 'basepath': 'notebook/report/{container.label}', 'svc_proto': 'http', 'svc_hostname': '{container.label}'},
      {'name': 'testurl', 'port': 9000, 'basepath': 'notebook/report/{container.label}', 'svc_proto': 'http', 'svc_hostname': '{container.label}'},]

for p in ps:
      try:
            p, created = Proxy.objects.get_or_create(name=p['name'], 
            basepath=p['basepath'], 
            svc_port=p['port'], 
            svc_proto=p['svc_proto'])
            p.save()
            if created:
                  print(f"Created Proxy was already present {p.name}")
            else:
                  print(f"Created new Proxy {p.name}")
      except Exception as e:
            print(f"Could not create Proxy {p['name']} because {e}")
            continue