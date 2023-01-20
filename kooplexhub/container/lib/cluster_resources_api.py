from kubernetes import config
from kubernetes.client import CoreV1Api, CustomObjectsApi
import pandas as pd

def UnitConverter(item, tounit=''):
    units = {
        'm':10**-3,
        'K':10**3,
        'M':10**6,
        'G':10**9}
    if tounit:
        return item/units[tounit]
    
    try:
        if item[-1]=='i':
            item=item[:-1]
           
        unit = item[-1]
        if unit in units.keys():
            return float(item[:-1])*units[unit]
        else:
            return float(item)
    except: 
        return float(item)

class Cluster():

    def __init__(self):
        config.load_kube_config()
        self.pod_df = pd.DataFrame(columns=['node', 'namespace', 'pod','container_name','requested_cpu','requested_memory', 'requested_gpu'])
        self.node_df = pd.DataFrame(columns=['node','total_cpu','total_memory', 'total_gpu']) #,'requestedcpu','requestedmemory'] )
        self.summed_df = None
        self.v1 = CoreV1Api()
        
    def _check_if_nodes_exist(self):
        # self.node_list
        pass
    
    def filter_nodes(self, node_list=['k8s-controlplane-fiek-cn1', 'k8s-controlplane-fiek-cn2', 'k8s-controlplane-onco2']):
        self.node_df = self.node_df.drop(labels=node_list)
        self.pod_df = self.pod_df.drop(labels=node_list)
    
    def query_nodes_status(self, node_list=[], label=[], reset=True):
        '''
        Example:
          query_nodes_status(node_list=['atys', 'veo1'], reset=False)
        or
          query_nodes_status(label=['veopods',['true']], reset=False)
        '''
            
        if reset:
            self.node_df = pd.DataFrame(columns=['node','total_cpu','total_memory', 'total_gpu']) #,'requestedcpu','requestedmemory'] )
            
        if label:
            ls = f"{label[0]} in  ({','.join(label[1])})"
            nodes = self.v1.list_node(label_selector=ls)
        elif node_list:
            ls = f"kubernetes.io/hostname in  ({','.join(node_list)})"
            nodes = self.v1.list_node(label_selector=ls)
        else:
            nodes = self.v1.list_node()
            
        for node in nodes.items:
            node_name = node.metadata.name
            nac = node.status.allocatable
            agpu = int(nac.get('nvidia.com/gpu',0))
            self.node_df.loc[len(self.node_df)] = [node_name, UnitConverter(nac['cpu']), UnitConverter(nac['memory']), agpu]
        
    def query_pods_status(self, field=[], label=[] , reset=True):
        '''
        Pod resources by label (node, namespace etc...)
        Selecting nodes: "spec.nodeName=" + node_name
        Select label fields: "user in (" + users + " ) 
        '''
        
        pods=[]

        if reset:
            self.pod_df = pd.DataFrame(columns=['node', 'namespace', 'pod','container_name','requested_cpu','requested_memory', 'requested_gpu'])
        
        if field or label:
            fs = ( "status.phase!=Succeeded,status.phase!=Failed")
            if field:
                fs += f",{field[0]}={field[1]}"    
            if label:
                ls = f"{label[0]} in  ({','.join(label[1])})"
            else:
                ls=""

            pods = self.v1.list_pod_for_all_namespaces(field_selector=fs, label_selector=ls)
        
        if not label and not field:
            pods =  self.v1.list_pod_for_all_namespaces()
            return
        
        for pod in pods.items:
            for container in pod.spec.containers:
                if container.resources.requests:
                    rcpu = UnitConverter(container.resources.requests.get('cpu', 0))
                    rmem = UnitConverter(container.resources.requests.get('memory', 0))
                    rgpu = int(container.resources.requests.get('nvidia.com/gpu', 0))
                    self.pod_df.loc[len(self.pod_df)] = [pod.spec.node_name, pod.metadata.namespace, pod.metadata.name, container.name, rcpu, rmem, rgpu]
        
    def resources_summary(self):
            
        self.pod_df = self.pod_df.set_index(keys='node')
        self.node_df = self.node_df.set_index(keys='node')
        # sum up requested cpu and memory of all pods and subtract it from the total of node cpu/memory
        summed_pod_df = self.pod_df.groupby('node')[['requested_cpu', 'requested_memory', 'requested_gpu']].sum()
        self.summed_df = pd.merge(self.node_df, summed_pod_df, 'inner', on = 'node')
        self.summed_df['avail_cpu'] = self.summed_df.total_cpu - self.summed_df.requested_cpu
        self.summed_df['avail_memory'] = self.summed_df.total_memory - self.summed_df.requested_memory
        self.summed_df['avail_gpu'] = self.summed_df.total_gpu - self.summed_df.requested_gpu
        self.summed_df['avail_cpu_per'] = self.summed_df.avail_cpu / self.summed_df.total_cpu *100
        self.summed_df['avail_memory_per'] = self.summed_df.avail_memory / self.summed_df.total_memory * 100
        self.summed_df['avail_gpu_per'] = self.summed_df.avail_gpu / self.summed_df.total_gpu *100
        
    def get_data(self):
        from numpy import around
        d = self.summed_df
        node_name = list(d.index.values)
        avail_cpu = around(d['avail_cpu'].to_numpy(), decimals=1) 
        total_cpu = d['total_cpu'].to_numpy()
        avail_memory = around(UnitConverter(d['avail_memory'].to_numpy(), tounit='G'), decimals=1) 
        total_memory = around(UnitConverter(d['total_memory'].to_numpy(), tounit='G'), decimals=1)
        avail_gpu = around(d['avail_gpu'].to_numpy(), decimals=1) 
        total_gpu = d['total_gpu'].to_numpy()
        return {'node_name':node_name,
                'avail_cpu':list( avail_cpu),
                'total_cpu':list(total_cpu),
                'avail_memory':list(avail_memory),
                'total_memory': list(total_memory),
                'avail_gpu': [ int(ag) for ag in avail_gpu],
                'total_gpu':[ int(tg) for tg in total_gpu], }
        
def get_node_current_usage(node_name):
    '''
    Example:
    
        get_node_current_usage('onco1')
    '''
    from numpy import around
    config.load_kube_config('./config')
    api = CustomObjectsApi()
    nodeinfo = api.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'nodes/'+node_name)
    usage = nodeinfo['usage']
    used_gpu = usage.get('nvidia.com/gpu',0)
    data={'node_name': node_name,
          'used_cpu': around(UnitConverter(usage['cpu']), decimals=1),
          'used_memory': around(UnitConverter(UnitConverter(usage['memory']), tounit='G'), decimals=1),
          'used_gpu': used_gpu}
    return data

def get_all_node_current_usage():
    node_names = []
    cpu = []
    memory = []
    gpu = []

    from numpy import around
    config.load_kube_config('./config')
    api = CustomObjectsApi()
    # filter controlplane
    ls = "node-role.kubernetes.io/control-plane notin ()"
    #nodes = cust.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'nodes')
    nodes = api.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'nodes', label_selector = ls)

    for node in nodes['items']:
        node_names.append(node['metadata']['name'])
        usage = node['usage']
        cpu.append(UnitConverter(usage['cpu']))
        memory.append(UnitConverter(UnitConverter(usage['memory']), tounit='G'))
        gpu.append(usage.get('nvidia.com/gpu',0))

    data={'node_name': node_names,
          'used_cpu': around(cpu),
          'used_memory': around(memory),
         'used_gpu': gpu}
    return data

def get_pod_usage(user='', namespace='', ):
    '''
    Example:
        get_pod_usage(user='visi')
        or
        get_pod_usage(namespace="k8plex-test")
        
    Writing selector (field, label or annotation):
       fs = ( "metadata.name=" + 'hub-0')
       ls = "app in (hub)"
    '''
    from numpy import around
    from kubernetes.client import CustomObjectsApi
    from kubernetes import config
    config.load_kube_config('./config')
    cust=CustomObjectsApi()
    
    fs = ( "metadata.namespace=" + namespace)
    ls = f"user in ({user})"
    if user and namespace:
        pods = cust.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'pods', field_selector=fs, label_selector=ls)
    if namespace:
        pods = cust.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'pods', field_selector=fs)
    if user:
        pods = cust.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'pods', label_selector=ls)

    
    pod_names = []
    cpu = []
    memory = []
    gpu = []
    for p in pods['items']:
        for c in p['containers']:
            pod_names.append(p['metadata']['name'])
            usage = c['usage']
            cpu.append(UnitConverter(usage['cpu']))
            memory.append(UnitConverter(UnitConverter(usage['memory']), tounit='G'))
            gpu.append(usage.get('nvidia.com/gpu',0))

    data={'node_name': pod_names,
              'used_cpu': around(cpu),
              'used_memory': around(memory, decimals=1),
             'used_gpu': gpu}
    return data
