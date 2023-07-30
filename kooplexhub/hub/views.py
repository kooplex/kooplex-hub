from django.views import generic
from django.contrib.auth.mixins import AccessMixin
from kooplexhub import settings

# Create dashboard of user's own current resource usage
from django.shortcuts import render
import pandas
from numpy import arange
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from container.lib.cluster_resources_api import *
#import plotly

class IndexView(AccessMixin, generic.TemplateView):
    template_name = 'index_unauthorized.html'
    context_object_name = 'indexpage'

    def plot_users_current_usage(self):
    
        user = self.request.user
        usage = pandas.DataFrame(get_pod_usage(user=user))
        usage["pod_names"]=usage["pod_names"].apply(lambda x: x[len(user.username)+1:])
        max_cpu = max(4, usage['used_cpu'].max())
        max_memory = max(12, usage['used_memory'].max())
        max_gpu = 3
        try: 
            wh = 50 * usage.shape[0]
        except:
            wh = 50 * 4
        # Bar chart
        # Create figure
        fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.35, shared_yaxes=True)
        
        fig.add_bar(alignmentgroup=0,
                    x=-usage['used_cpu'],
                    y=usage['pod_names'],
                    orientation='h',
                    row=1,
                    col=1,
                    #     hovertemplate="%{y}: %{customdata:.1f}%<extra></extra>",
                   )
        
        fig.add_bar(alignmentgroup=1,
                    x=usage['used_memory'],
                    y=usage['pod_names'],
                    orientation='h',
                    row=1,
                    col=2,
                   )
        
        fig.update_layout(
            dict(
                #xaxis=dict(title="Number of currently used CPUs"),
                #xaxis=dict(title=""),
                #yaxis=dict(title="Container names"),
                paper_bgcolor='rgba(50,50,50,.1)',
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                font = dict(size=15, color='lightgray'),
                #title= dict(text=f"Your current CPU usage = {usage['used_cpu'].sum():.1f}\t\t---\t\tMemory usage = {usage['used_memory'].sum():.1f}GB ", font=dict(size=15, color='lightgray'),  yref='paper')
                title= dict(text=f"Environment labels", font=dict(size=22, color='lightgray'),  yref='paper', xanchor="right", x=0.65, xref="paper")
            ),
            font=dict(size=16,color='lightgray'),
            legend_x=0,
            legend_y=1,
            #hovermode="x",
            margin=dict(b=0,t=40,l=0,r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(x=0.05,y=0.95,
                        bgcolor='rgba(255, 255, 255, 0.75)',
                        bordercolor='rgba(255, 255, 255, 0)',
                        font=dict(color='black'),
                       ),
            width=600,
            height=200,
            yaxis_visible=False,
            yaxis_fixedrange=True,
            # xaxis
            xaxis_tick0=0,
            xaxis_dtick=20,
            xaxis_ticktext=list(map(lambda x: f"{x:.1f}", -1*arange(-max_cpu,0.001,max_cpu/6))),
            xaxis_tickvals=list(map(lambda x: f"{x:.1f}", arange(-max_cpu,0.001,max_cpu/6))),
            xaxis_title=f"<b>Total CPU {usage['used_cpu'].sum():.1f}</b>",
            #xaxis_fixedrange=True,
            # xaxis2
            xaxis2_title=f"<b>Total Memory {usage['used_memory'].sum():.1f} [GB]</b>",
            showlegend=False,
            xaxis2_ticktext=list(map(lambda x: f"{x:.1f}", arange(0,max_memory,max_memory/10))),
            xaxis2_tickvals=list(map(lambda x: f"{x:.1f}", arange(0,max_memory,max_memory/10))),
            #xaxis2_fixedrange=True,
            bargap = 0.10,
        )
        
        for i, label in enumerate(usage["pod_names"]):
            fig.add_annotation(
                text=label,
                x=0.5,
                xanchor="center", xref="paper", ax=0,
                y=i, yref="y", ay=0,
                showarrow=False,
            )
        
        div_cpumem = fig.to_image(format="svg").decode()
        div_gpu = '<br/> <h2 style="font-family: \'Open Sans\', verdana, arial, sans-serif; font-size: 19px; text-align: center; margin: 20px; color: rgb(211, 211, 211); opacity: 1; font-weight: normal; white-space: pre;">Currently using <strong>%s GPUs</strong></h2>'%usage["used_gpu"].sum()

        return '<div class="m-0 p-0 align-items-center justify-content-center" style="text-align: center;">'+div_cpumem+div_gpu+'</div>'

    def plot_servers_current_usage(self):
    
        c = Cluster()
        c.query_pods_status(reset=True)
        c.pod_df = c.pod_df.set_index(keys='node')
        summed_pod_df = c.pod_df.groupby('node')[['requested_cpu', 'requested_memory', 'requested_gpu']].sum()

        server_df = pd.DataFrame(get_all_node_current_usage())
        c.query_nodes_status(reset=True)
        c.node_df = c.node_df.set_index(keys='node')
        c.summed_df = pd.merge(c.node_df, summed_pod_df, 'inner', on = 'node')
        c.summed_df['avail_cpu'] = c.summed_df.total_cpu - c.summed_df.requested_cpu
        c.summed_df.total_memory = c.summed_df.total_memory/2**30
        c.summed_df.requested_memory = c.summed_df.requested_memory/2**30
        tot = pd.merge(server_df,c.summed_df.reset_index(), left_on='node_name', right_on='node').drop(columns=['node'])
        tot['free_cpu']=tot.total_cpu-tot.used_cpu
        tot['free_memory']=tot.total_memory-tot.used_memory
        
        tot.sort_values(by="free_cpu", inplace=True)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.update_layout(
                height=600,
                width=1000,
                barmode="relative",
                font=dict(size=16,color='lightgray'),
                legend_x=0,
                legend_y=1,
                hovermode="x",
                margin=dict(b=0,t=40,l=0,r=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                 legend=dict(x=0.05,y=0.95,
                   bgcolor='rgba(255, 255, 255, 0.75)',
                   bordercolor='rgba(255, 255, 255, 0)',
                   font=dict(color='black'),
                   ),
                title= dict(text=f"Memory and CPU usage", 
                    font=dict(size=24, 
                    color='lightgray',),
                    yref='paper')
            )
        
        fig.add_bar(
            x=tot['node_name'], y=tot.apply(lambda x: x.total_cpu - max(x.requested_cpu,x.used_cpu), axis=1),
            marker_color='rgb(90,255, 70)', 
            name="Free CPU",
            offsetgroup=1,
            offset=1/4+0.01,
            width=1/4,
            yaxis=f"y2",
            secondary_y=True,
        )
        fig.add_bar(
            x=tot['node_name'], y=tot.apply(lambda x: max(x.requested_cpu-x.used_cpu,0), axis=1),
            marker_color='rgb(255,195,0)',
            name="Allocated CPU above used",
            offsetgroup=2,
            offset=1/4+0.01,
            width=1/4,
            yaxis=f"y2",
            secondary_y=True,
        )
        fig.add_bar(
            x=tot['node_name'], y=tot['used_cpu'],
            marker_color='rgb(220,30,0)',
            name="Used CPU",
            offsetgroup=1,
            offset=1/4+0.01,
            width=1/4,
            yaxis=f"y2",
            secondary_y=True,
        )

        fig.add_bar(
            x=tot['node_name'], y=tot.apply(lambda x: x.total_memory-max(x.requested_memory,x.used_memory), axis=1),
            marker_color='rgb(80,255, 80)',
            marker_pattern_shape="x",
            name="Free Memory",
            width=1/4,
            offset=0,
            offsetgroup=0,
            yaxis=f"y",
            secondary_y=False,
        )
        fig.add_bar(
            x=tot['node_name'], y=tot.apply(lambda x: max(x.requested_memory-x.used_memory,0), axis=1),
            marker_color='rgb(255,135,0)',
            marker_pattern_shape="x",
            name="Allocated Memory above used",
            offsetgroup=2,
            offset=0,
            width=1/4,
            yaxis=f"y",
            secondary_y=False,
        )
        fig.add_bar(
            x=tot['node_name'], y=tot['used_memory'],
            marker_color='rgb(220,0,0)',
            marker_pattern_shape="x",
            name="Used Memory",
            offsetgroup=0,
            offset=0,
            width=1/4,
            yaxis=f"y",
            secondary_y=False,
        )
        fig.update_yaxes(title_text="<b>Memory usage [GB]", secondary_y=False)
        fig.update_yaxes(title_text="<b>CPU usage [core]", secondary_y=True)
        div = fig.to_image(format="svg").decode()
        
        return '<div class="row m-0 p-0 align-items-center justify-content-center">'+div+'</div>'

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

