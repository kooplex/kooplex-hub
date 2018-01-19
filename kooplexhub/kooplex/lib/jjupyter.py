#Not used
#def jupyter_startsession(container):
#    """
#    Jupyter notebook api client.
#    based on: https://gist.github.com/blink1073/ecae5130dfe138ea2aff
#    """
#    info = { 'containername': container.name }
#    kw = {
#        'url': os.path.join(get_settings('spawner', 'pattern_jupyterapi') % info, 'sessions'), 
#        'headers': {'Authorization': 'token %s' % container.user.token, },
#        'data': json.dumps({'notebook': {'path': container.url }, 'kernel': { 'name': 'python3' }}),
#    }
#    return _keeptrying(requests.post, 50, **kw)
 
