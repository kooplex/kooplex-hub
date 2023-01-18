from kubernetes import client, config
from kubernetes.client import *
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
    pod_df = None 
    node_df = None 
    summed_df = None
    node_list = []
    v1 = None
    
    def __init__(self, nodes=[]):
        #config.load_kube_config('./config')
        config.load_kube_config()
        self.pod_df = pd.DataFrame(columns=['node', 'namespace', 'pod','container_name','requested_cpu','requested_memory'])
        self.node_df = pd.DataFrame(columns=['node','total_cpu','total_memory']) #,'requestedcpu','requestedmemory'] )
        self.summed_df = None
        self.v1 = client.CoreV1Api()
        self.node_list = nodes
        
    def _check_if_nodes_exist(self):
        # self.node_list
        pass
    
    def filter_nodes(self, node_list=['k8s-controlplane-fiek-cn1', 'k8s-controlplane-fiek-cn2', 'k8s-controlplane-onco2']):
        self.node_df = self.node_df.drop(labels=node_list)
        self.pod_df = self.pod_df.drop(labels=node_list)
    
    def nodes_status(self, label_selector='', reset=True):
        # self.node_list
        if reset:
            self.node_df = pd.DataFrame(columns=['node','total_cpu','total_memory']) #,'requestedcpu','requestedmemory'] )
        if label_selector:
            nodes = self.v1.list_node(label_selector=label_selector)
        else:
            nodes = self.v1.list_node()

        node_df = pd.DataFrame(columns=['node','total_cpu','total_memory']) #,'requestedcpu','requestedmemory'] )
        for node in self.v1.list_node().items:
            node_name = node.metadata.name
            nac = node.status.allocatable
            self.node_df.loc[len(self.node_df)] = [node_name, UnitConverter(nac['cpu']), UnitConverter(nac['memory'])] #, 0, 0]
    
    def pods_status_all_node(self):
        '''
        Pod resources of all the nodes
        '''
        self.pod_df = pd.DataFrame(columns=['node', 'namespace', 'pod','container_name','requested_cpu','requested_memory'])
        for node in self.v1.list_node().items:
            self.pods_status_on_node(node_name=node.metadata.name, reset=False)
    
    def pods_status_on_node(self, node_name = '', reset=True):
        '''
        Pod resources of only one node
        '''
        
        if reset:
            self.pod_df = pd.DataFrame(columns=['node', 'namespace', 'pod','container_name','requested_cpu','requested_memory'])
        fs = ( "status.phase!=Succeeded,status.phase!=Failed,"+"spec.nodeName=" + node_name)
        pods = self.v1.list_pod_for_all_namespaces(field_selector=fs)
        #pods = v1.list_pod_for_all_namespaces()  
        #pods = v1.list_namespaced_pod('k8plex-test')  
        for pod in pods.items:
            for container in pod.spec.containers:
                if container.resources.requests:
                    rcpu = UnitConverter(container.resources.requests.get('cpu', 0))
                    rmem = UnitConverter(container.resources.requests.get('memory', 0))
            
                    self.pod_df.loc[len(self.pod_df)] = [node_name, pod.metadata.namespace, pod.metadata.name, container.name, rcpu, rmem]
        
    def resources_summary(self):
        if self.node_list:
            # check node
            self.pods_status_on_node(node_name=self.node_list)
            self.nodes_status()
            # self.filter_nodes
        else:
            self.pods_status_all_node()
            self.nodes_status()
            
        self.pod_df = self.pod_df.set_index(keys='node')
        self.node_df = self.node_df.set_index(keys='node')
        # sum up requested cpu and memory of all pods and subtract it from the total of node cpu/memory
        summed_pod_df = self.pod_df.groupby('node')[['requested_cpu', 'requested_memory']].sum()
        self.summed_df = pd.merge(self.node_df, summed_pod_df, 'inner', on = 'node')
        self.summed_df['avail_cpu'] = self.summed_df.total_cpu - self.summed_df.requested_cpu
        self.summed_df['avail_memory'] = self.summed_df.total_memory - self.summed_df.requested_memory
        self.summed_df['avail_cpu_per'] = self.summed_df.avail_cpu / self.summed_df.total_cpu *100
        self.summed_df['avail_memory_per'] = self.summed_df.avail_memory / self.summed_df.total_memory * 100
        
        
    def printit(self):
        node_name, avail_cpu, total_cpu, avail_memory, total_memory = self.get_data()
        #d = self.summed_df
        #print(f"Available CPU and memory on node {d.index[0]}")
        print(f"Available CPU and memory on node {node_name}")
        #print(f"{d['avail_cpu'][0]:.1f}/{d['totalcpu'][0]} and {UnitConverter(d['avail_memory'][0], tounit='G'):.1f}GB/{UnitConverter(d['totalmemory'][0], tounit='G'):.1f}GB")
        print(f"{avail_cpu}/{total_cpu} -  {avail_memory}GB/{total_memory}GB")
        
    def get_data(self):
        from numpy import around
        d = self.summed_df
        node_name = d.index[0]
        avail_cpu = around(d['avail_cpu'][0], decimals=1) 
        total_cpu = d['total_cpu'][0] 
        avail_memory = around(UnitConverter(d['avail_memory'][0], tounit='G'), decimals=1) 
        total_memory = around(UnitConverter(d['total_memory'][0], tounit='G'), decimals=1)
        return {'node_name':node_name, 
                'avail_cpu':avail_cpu, 
                'total_cpu':total_cpu, 
                'avail_memory':avail_memory, 
                'total_memory': total_memory}
        
#     def get_node_current_usage(self, node_name):
#         api = client.CustomObjectsApi()
#         nodeinfo = api.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'nodes/'+nodename)
#         return nodeinfo.usage

#def get_node_current_usage(node_name):
