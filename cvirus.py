#!/usr/bin/env python
# coding: utf-8

# In[1]:


# get corona virus data from worldometers

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
from bs4 import BeautifulSoup
import requests
import pandas as pd
import plotly.graph_objs as go
import random2
from collections import deque
import io
from flask_caching import Cache

app = dash.Dash(__name__)
server = app.server

cache = Cache(app.server, config={
    # try 'filesystem' if you don't want to setup redis
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})
app.config.suppress_callback_exceptions = True

timeout = 5

def get_corona_data():
    url = 'https://www.worldometers.info/coronavirus/'
    # Make a GET request to fetch the raw HTML content
    html_content = requests.get(url).text
    # Parse html content
    soup = BeautifulSoup(html_content, "html.parser")
    gdp_table = soup.find('table', id="main_table_countries_today")
    gdp_table_data = gdp_table.tbody.find_all('tr')
    gdp_table_header = gdp_table.thead.find_all('th')

    # Getting all column names
    live_data_column = []
    for i in range(len(gdp_table_header)):
        live_data_column.append(gdp_table_header[i].text)

    # Getting all country names and values
    dicts = {}
    for i in range(len(gdp_table_data)):
        # print(i, gdp_table_data[i])
        try:
            key = (gdp_table_data[i].find_all('td')[0].string)
        except:
            print('Error/Empty')
        value = [j.string for j in gdp_table_data[i].find_all('td')]
        dicts[key] = value
    live_data = pd.DataFrame(dicts).T
    live_data.columns = live_data_column
    live_data.drop(live_data.columns[0], axis=1, inplace=True)
    live_data.iloc[:, :5].to_csv('base_data.csv')
    return live_data


X = deque(maxlen=20)
Y = deque(maxlen=20)
X.append(1)
Y.append(1)


app.layout = html.Div([
    html.Div([html.H1('COVID-19 Live Statistics', style={'textAlign': 'center', 'border': 'solid'})]),
    html.Div([dcc.Graph(id='time-series-graph', animate=False),
              dcc.Interval(id='time-series-update', interval=60*1000, n_intervals=1),

              dcc.Graph(id='total-cases-vs-total-deaths', animate=True),
              dcc.Interval(id='scatter-update',
                           interval=60*100,
                           n_intervals=0)
              ], style={'columnCount': 2}),

    html.Div([dcc.Graph(id='live-table'),
              dcc.Interval(id='table-update',
                           interval=60*100,
                           n_intervals=0),

              dcc.Graph(id='growth-graph', animate=True),
              dcc.Interval(id='growth-update', interval=60*1000, n_intervals=0),
                        # figure={'data': [{'x': [1, 2, 4, 5], 'y': [6, 9, 10], 'type': 'line', 'name': 'boats'},
                        #                  {'x': [1, 2, 4, 5], 'y': [6, 4, 8], 'type': 'bar', 'name': 'cars'}
                        #                  ]})
              ], style={'columnCount': 2}),


    html.Div([html.P(id='csv-create'),
              dcc.Interval(id='csv-update',
                           interval=30 * 100,
                           n_intervals=0)]),

], style={'backgroundColor': 'white', 'padding': 30})


# @app.callback(Output('csv-create', 'children'), [Input('csv-update', 'n_intervals')])
# def update_cv(n):
#     return None #get_corona_data()

@app.callback(Output('total-cases-vs-total-deaths', 'figure'), [Input('scatter-update', 'n_intervals')])
@cache.memoize(timeout=timeout)  # in seconds
def update_scatter_plot(n):
    get_corona_data()
    base_data_df = pd.read_csv('base_data.csv')
    base_data_df.columns = map(str.lower, base_data_df.columns)
    # base_data_df.rename(columns={'Unnamed: 0': 'country'}, inplace=True)

    trace = []
    for country, cases in base_data_df.groupby('unnamed: 0'):
        trace.append(go.Scattergl(x=cases.totalcases,
                                  y=cases.totaldeaths,
                                  name=country,
                                  text=country,
                                  mode='markers'
                                  )
                     )

    layout = dict(xaxis={'title': 'Confirmed Cases'},
                  yaxis={'title': 'Total Deaths'},
                  title={'text': 'Total Deaths vs Total Confirmed Cases'},
                  markers={'size': 50, 'line': {'color': 'white'}},
                  opacity=0.7,
                  hovermode='closest'
                  )
    # scatter_fig = go.Figure(data=trace)
    return {'data': trace, 'layout': layout}


@app.callback(Output('live-table', 'figure'), [Input('table-update', 'n_intervals')])
def update_table(n):
    df = pd.read_csv('base_data.csv')
    df.rename(columns={'Unnamed: 0': 'Country'}, inplace=True)
    data = go.Table(header=dict(values=list(df.columns)), cells=dict(values=list(df.T.values)))
    layout = go.Layout(title='Confirmed Cases, Deaths & Recovery by Country')
    return {'data': [data], 'layout': layout}


url = 'https://raw.githubusercontent.com/datasets/covid-19/master/data/worldwide-aggregated.csv'
content = requests.get(url).content
confirmed_global = pd.read_csv(io.StringIO(content.decode('utf-8')), parse_dates=['Date'])
# confirmed_global['Last_Update'] = confirmed_global['Last_Update'].values.astype('<M8[D]')

confirmed = confirmed_global.groupby('Date')['Confirmed'].sum().reset_index()
confirmed_growth = confirmed['Confirmed'].pct_change()
confirmed['Growth_Rate'] = confirmed_growth
confirmed_growth_change = confirmed['Growth_Rate'].pct_change()
confirmed['Change_Growth_Rate'] = confirmed_growth_change
deaths = confirmed_global.groupby('Date')['Deaths'].sum().reset_index()
# recovered = confirmed_global.groupby('Date')['Recovered'].sum().reset_index()


@app.callback(Output('time-series-graph', 'figure'), [Input('time-series-update', 'n_intervals')])
def update_graph(n):
    # global X
    # global Y
    # X.append(X[-1] + 1)
    # Y.append(Y[-1] + Y[-1] * random2.uniform(-0.1, 0.1))
    # data = go.Scatter(x=list(X),
    #                   y=list(Y),
    #                   name='Scatter',
    #                   mode='lines+markers')
    # return {'data': [data], 'layout': go.Layout(xaxis=dict(range=[min(X), max(X)]), yaxis=dict(range=[min(Y), max(Y)])


    trace_1 = go.Scatter(x=confirmed['Date'],
                         y=confirmed['Confirmed'],
                         name='Confirmed',
                         mode='lines+markers',
                         marker_color='blue'
                         )

    trace_2 = go.Scatter(x=deaths['Date'],
                         y=deaths['Deaths'],
                         name='Deaths',
                         mode='lines+markers',
                         marker_color='red'
                         )

    return {'data': [trace_1, trace_2], 'layout': go.Layout(title={'text': 'Timeline of Confirmed Cases, Deaths & Recovery Worldwide'},
                                                                     showlegend=True, xaxis_rangeslider_visible=True)}


@app.callback(Output('growth-graph', 'figure'), [Input('growth-update', 'n_intervals')])
def update_growth(n):
    trace_1 = go.Scatter(x=confirmed['Date'],
                         y=confirmed['Growth_Rate'],
                         name='Growth_Rate',
                         text='Date, Rate %',
                         mode='lines+markers',
                         marker_color='green'
                         )

    # trace_2 = go.Scatter(x=confirmed['Date'],
    #                      y=confirmed['Change_Growth_Rate'],
    #                      name='Change Growth_Rate',
    #                      mode='lines+markers',
    #                      marker_color='blue'
    #                      )

    layout = dict(title={'text': 'Growth Rate of Confirmed Cases Worldwide'},
                  yaxis={'title': 'Daily Growth (in %)'},
                  markers={'size': 50, 'line': {'color': 'white'}},
                  opacity=0.7,
                  hovermode='closest'
                  )
    return {'data': [trace_1], 'layout': layout}


if __name__ == '__main__':
    app.run_server(debug=True)