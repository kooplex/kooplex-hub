from django.views import generic
from django.contrib.auth.mixins import AccessMixin
from kooplexhub import settings

# Create dashboard of user's own current resource usage
from django.shortcuts import render
#import plotly.graph_objs as go
import pandas
import plotly.express as px
from container.lib.cluster_resources_api import *

class IndexView(AccessMixin, generic.TemplateView):
    template_name = 'index_unauthorized.html'
    context_object_name = 'indexpage'

    def plot_users_current_usage(self):
    
        user = self.request.user
        usage = pandas.DataFrame(get_pod_usage(user=user))
        usage["pod_names"]=usage["pod_names"].apply(lambda x: x[len(user.username)+1:])
        wh=300 #wdith-height
        g = usage.groupby(['namespaces','pod_names']).sum().reset_index()
        g['center'] = 'Memory [GB]'

        fig = px.sunburst(
            g.drop(columns=['used_gpu', 'used_cpu']),
            path=['center','namespaces','pod_names','used_memory'],
         )
        fig.update_layout(height=wh, width=wh, margin={'l':0, 'r':0, 't':20, 'b':0},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=30),
                title= dict(text=f"Total Memory [GB] = {usage['used_memory'].sum():.1f}", font=dict(size=15, color='lightgray',
#                family='system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", "Liberation Sans", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"'
),
  yref='paper')
                )
        div_mem = fig.to_image(format="svg").decode()

#        div_mem = fig.to_html(full_html=False)
    
        g['center'] = 'CPU'
        fig = px.sunburst(
            g.drop(columns=['used_gpu', 'used_memory']),
            path=['center','namespaces','pod_names','used_cpu'],
        )
        fig.update_layout(height=wh, width=wh, margin={'l':0, 'r':0, 't': 20, 'b':0},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=30),
                title= dict(text=f"Total CPU = {usage['used_cpu'].sum():.1f}", font=dict(size=15, color='lightgray'),  yref='paper')
                )
                
        div_cpu = fig.to_image(format="svg").decode()

        g['center'] = 'GPU'
        fig = px.sunburst(
            g.drop(columns=['used_cpu', 'used_memory']),
            path=['center','namespaces','pod_names','used_gpu'],
#            title= f"Total GPU = {usage['used_gpu'].sum()}",
        )
#        div_gpu = fig.to_html(full_html=False)
        fig.update_layout(height=wh, width=wh, margin={'l':0, 'r':0, 't':20, 'b':0},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=30),
                title= dict(text=f"Total GPU = {usage['used_gpu'].sum()}", font=dict(size=15, color='lightgray'),  yref='paper')
)
                
        div_gpu = fig.to_image(format="svg").decode()

        return '<div class="row m-0 p-0 align-items-center justify-content-center"><div class="col-4 align-items-center">'+div_cpu+'</div><div class="col-4">'+div_mem+'</div><div class="col-4">'+div_gpu+'</div></div>'

    def plot_servers_current_usage(self):
    
        server_df = pd.DataFrame(get_all_node_current_usage())
        c = Cluster()
        c.query_nodes_status()
        c.node_df.total_memory = c.node_df.total_memory/2**30
        
        tot = pd.merge(server_df,c.node_df, left_on='node_name', right_on='node').drop(columns=['node'])
        
        tot['p_cpu']=tot.used_cpu/tot.total_cpu*100
        tot['free_cpu']=tot.total_cpu-tot.used_cpu
        tot['p_gpu']=tot.used_gpu/tot.total_gpu*100
        tot['p_memory']=tot.used_memory/tot.total_memory*100
        tot['free_memory']=tot.total_memory-tot.used_memory
        fig = px.bar(tot, x='node_name', y=['p_cpu', 'p_memory'], barmode='group')
        fig.update_layout(height=500, width=1000, margin={'l':0, 'r':0, 'b':0},
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(title=""),
                yaxis=dict(title="Usage [%]"),
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='lightgray'),
                title= dict(text=f"Cluster usage", 
                    font=dict(size=15, 
                    color='lightgray',),
                    yref='paper')
                )
        div_p = fig.to_image(format="svg").decode()

        fig = px.bar(tot, x='node_name', y=['used_cpu', 'free_cpu'], color_discrete_map={'free_cpu':'lightgreen', 'used_cpu':'red'})
        fig.update_layout(height=500, width=800, margin={'l':0, 'r':0, 'b':0},
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(title=""),
                yaxis=dict(title="Used/Free CPU"),
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='lightgray'),
                legend=dict(x=0.05,y=0.98,
                    bgcolor='rgba(255, 255, 255, 0)',
                    bordercolor='rgba(255, 255, 255, 0)'
                    ),
                title= dict(text=f"CPU", 
                    font=dict(size=15, 
                    color='lightgray',),
                    yref='paper')
                )
        div_cpu = fig.to_image(format="svg").decode()
        fig = px.bar(tot, x='node_name', y=['used_memory', 'free_memory'], color_discrete_map={'free_memory':'lightgreen', 'used_memory':'red'})
        fig.update_layout(height=500, width=800, margin={'l':0, 'r':0, 'b':0},
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(title=""),
                yaxis=dict(title="Used/Free Memory [GB]"),
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='lightgray'),
                legend=dict(x=0.05,y=0.95,
                    bgcolor='rgba(255, 255, 255, 0)',
                    bordercolor='rgba(255, 255, 255, 0)'
                    ),
                title= dict(text=f"Memory", 
                    font=dict(size=15, 
                    color='lightgray',),
                    yref='paper')
                )
        div_mem = fig.to_image(format="svg").decode()
        return '<div class="row m-0 p-0 align-items-center justify-content-center">'+div_p+'</div>'+\
               '<div class="row m-0 p-0 align-items-center justify-content-center"><div class="col-6 align-items-center">'+div_cpu+\
               '</div><div class="col-6 align-items-center">'+div_mem+'</div></div>'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_profile'] = settings.URL_ACCOUNTS_PROFILE
        context['plot_user'] = self.plot_users_current_usage()
        context['plot_server'] = self.plot_servers_current_usage()
        return context

    def setup(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.template_name = 'index.html'
        super().setup(request, *args, **kwargs)

class MonitoringView(AccessMixin, generic.TemplateView):
    template_name = 'monitoring.html'
    context_object_name = 'monitoring'

class MonitoringDashboardView(AccessMixin, generic.TemplateView):
    template_name = 'monitoring_dashboard.html'
    context_object_name = 'monitoring'



#TEST TASK

from django.shortcuts import redirect
import logging
import time
from kooplexhub.tasks import task_do_something
logger = logging.getLogger(__name__)

def task(request, duma):
    logger.info("DEFINE TASK")
    a = task_do_something.delay(duma)
    logger.info(a)
    return redirect('indexpage')

