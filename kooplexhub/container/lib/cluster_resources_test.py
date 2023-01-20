#!/usr/bin/env python

from cluster_resources import  *

# ## Node query allocatable resources

# ### For a given node

C = Cluster()
# Example:
#           query_nodes_status(node_list=['atys', 'veo1'], reset=False)
#         or
#           query_nodes_status(label=['veopods',['true']], reset=False)
C.query_nodes_status(node_list=['atys', 'veo1'], reset=True)
C.node_df


C = Cluster()
# Example:
#           query_nodes_status(node_list=['atys', 'veo1'], reset=False)
#         or
#           query_nodes_status(label=['veopods',['true']], reset=False)
C.query_nodes_status()
C.node_df


# ## Pod query for a node or user

# ### Test for field_selector

# Pod resources by label (node, namespace etc...)
#         Selecting nodes: "spec.nodeName=" + node_name
#         Select label fields: "user in (" + users + " ) 
fs=["spec.nodeName=",'future1']
C.query_pods_status(field=fs)
C.pod_df.head(3)


# ### Test for label_selector

ls = ['user',['visi']]
C.query_pods_status(label=ls)
C.pod_df


# ### Test for field_selector and label_selector

fs=["spec.nodeName=",'future1']
ls = ['user',['visi']]
C.query_pods_status(field=fs, label=ls)
C.pod_df.head(3)


# ### Available resources on a node

C = Cluster()

C.query_nodes_status(node_list=['future1'], reset=True)
fs=["spec.nodeName=",'future1']
C.query_pods_status(field=fs)
C.resources_summary()
C.get_data()


# ### Available resources on multiple nodes
C = Cluster()

node_list=['future1', 'veo1', 'veo2']
C.query_nodes_status(node_list=node_list, reset=False)
for node in node_list:
    fs=["spec.nodeName=",node]
    C.query_pods_status(field=fs, reset=False)

C.resources_summary()
C.get_data()


# ## Allocated resources for a user

# Sort it by node, namespace/platform, notebook and job?
ls = ['user',['visi']]
C.query_pods_status(label=ls)
# Groupby job is missing yet
C.pod_df.drop(columns=['pod']).groupby(['node', 'namespace']).sum()


# # Current usage

# ## Get node usage

# ### One at a time

get_node_current_usage('onco1')


# ### All

get_all_node_current_usage()

# ## Get pods current usage

# ### of a user

#get_pod_usage(user='visi') #, namespace="k8plex-test")
get_pod_usage(namespace="k8plex-test")



