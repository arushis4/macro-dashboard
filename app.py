#!/usr/bin/env python
# coding: utf-8

import pandas as pd
from fredapi import Fred
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objs as go
from datetime import datetime

# Initialize Fred API with your key
fred = Fred(api_key='f51eb3a1cdbac7e83b7cc82e96f3fb86')

# Define the indicators to fetch
indicators = {
    '10Y Treasury': 'GS10',
    '2Y Treasury': 'GS2',
    'CPI (Inflation)': 'CPIAUCSL',
    'PPI': 'PPIACO',
    'Unemployment Rate': 'UNRATE',
    'New Orders Index': 'AMTMNO',
    'Fed Funds Rate': 'FEDFUNDS'
}

# Hard-coded list of key economic events
key_events = [
    {"date": "2008-09-15", "label": "Lehman Brothers Collapse"},
    {"date": "2020-03-16", "label": "COVID-19 Market Crash"},
    {"date": "2022-03-16", "label": "First Fed Rate Hike (Post-COVID)"},
    {"date": "2023-06-14", "label": "Fed Pauses Rate Hikes"}
]

# Fetch and prepare data
def get_data():
    data = {}
    for name, sid in indicators.items():
        s = fred.get_series(sid).resample('D').last()
        data[name] = s
    
    # Calculate the Yield Spread
    data['Yield Spread'] = data['10Y Treasury'] - data['2Y Treasury']
    
    # Fetch and calculate YoY GDP Growth
    gdp = fred.get_series('GDP').resample('Q').last()
    gdp_yoy = gdp.pct_change(4) * 100
    gdp_yoy = gdp_yoy.resample('D').ffill()
    data['GDP YoY Growth (%)'] = gdp_yoy
    
    # Combine all series into a single DataFrame
    df = pd.concat(data, axis=1)
    df = df.loc['2010-01-01':]
    return df

df = get_data()

# Generate AI summary with event mentions
def generate_ai_summary(series):
    if len(series) < 2:
        return "Not enough data to summarize."
    
    pct_change = ((series.iloc[-1] - series.iloc[0]) / series.iloc[0]) * 100
    max_val = series.max()
    min_val = series.min()
    trend = "increased" if pct_change > 0 else "decreased"

    summary = (
        f"From {series.index[0].date()} to {series.index[-1].date()}, "
        f"the value has {trend} by {abs(pct_change):.2f}%. "
        f"The peak value was {max_val:.2f}, and the lowest was {min_val:.2f}."
    )
    
    return summary

# Initialize Dash app
app = Dash(__name__)

# App layout
app.layout = html.Div(
    style={'backgroundColor': '#000000', 'color': '#FFFFFF', 'font-family': 'Arial, sans-serif', 'padding': '40px'},
    children=[
        html.H1("Macroeconomic Indicators Dashboard", style={'fontSize': '40px', 'textAlign': 'center', 'color': '#39FF14'}),

        html.Div([
            html.Label("Choose Indicator:", style={'fontSize': '18px'}),
            dcc.Dropdown(
                id='indicator-dropdown',
                options=[{'label': c, 'value': c} for c in df.columns],
                value='Yield Spread',
                style={'color': '#000000', 'width': '100%'}
            )
        ], style={'marginBottom': '20px', 'width': '350px', 'margin': '0 auto 20px auto'}),

        html.Div([
            html.Label("Select Date Range:", style={'fontSize': '18px', 'display': 'block', 'marginBottom': '5px'}),
            dcc.DatePickerRange(
                id='date-picker',
                min_date_allowed=df.index.min().date(),
                max_date_allowed=df.index.max().date(),
                start_date=df.index.min().date(),
                end_date=df.index.max().date(),
                display_format='YYYY-MM-DD',
                style={'color': '#000000'}
            )
        ], style={'width': '300px', 'margin': '0 auto 20px auto', 'textAlign': 'center'}),

        dcc.Graph(id='indicator-graph'),

        html.Div(id='ai-summary', style={
            'marginTop': '30px',
            'backgroundColor': '#1e1e1e',
            'padding': '20px',
            'borderRadius': '10px',
            'width': '80%',
            'margin': 'auto',
            'color': '#DDDDDD',
            'fontSize': '16px'
        }),

        html.Div(id='last-updated', style={
            'marginTop': '30px',
            'textAlign': 'center',
            'color': '#AAAAAA',
            'fontSize': '12px'
        }),

        html.Div("Source: Federal Reserve Economic Data - Federal Reserve Bank of St. Louis", style={
            'marginTop': '5px',
            'fontSize': '12px',
            'textAlign': 'center',
            'color': '#AAAAAA',
            'fontStyle': 'italic'
        })
    ]
)

# Callback to update chart and summary
@app.callback(
    [Output('indicator-graph', 'figure'),
     Output('ai-summary', 'children'),
     Output('last-updated', 'children')],
    [Input('indicator-dropdown', 'value'),
     Input('date-picker', 'start_date'),
     Input('date-picker', 'end_date')]
)
def update_chart(indicator, start_date, end_date):
    mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
    filtered_series = df.loc[mask, indicator].dropna()

    trace = go.Scatter(
        x=filtered_series.index,
        y=filtered_series.values,
        mode='lines',
        line=dict(color='#39FF14', width=2),
        name=indicator
    )

    # Add economic event flags
    event_shapes = []
    event_annotations = []
    for event in key_events:
        event_date = pd.to_datetime(event["date"])
        if pd.to_datetime(start_date) <= event_date <= pd.to_datetime(end_date):
            event_shapes.append({
                "type": "line",
                "x0": event_date,
                "x1": event_date,
                "y0": 0,
                "y1": 1,
                "xref": "x",
                "yref": "paper",
                "line": {"color": "red", "width": 1, "dash": "dot"}
            })
            event_annotations.append({
                "x": event_date,
                "y": 1.02,
                "xref": "x",
                "yref": "paper",
                "text": event["label"],
                "showarrow": False,
                "font": {"color": "red", "size": 10, style: "bold"},
                "align": "center"
            })

    fig = go.Figure(data=[trace])
    fig.update_layout(
        title=f"{indicator} Over Time",
        xaxis_title='Date',
        yaxis_title=indicator,
        plot_bgcolor='#000000',
        paper_bgcolor='#000000',
        font_color='#FFFFFF',
        title_font_color='#FFFFFF',
        xaxis=dict(gridcolor='#2a2a2a'),
        yaxis=dict(gridcolor='#2a2a2a'),
        margin=dict(l=40, r=40, t=60, b=60),
        hovermode='x unified',
        shapes=event_shapes,
        annotations=event_annotations
    )

    summary_text = generate_ai_summary(filtered_series)
    last_updated_text = f"Last updated: {df.index[-1].strftime('%Y-%m-%d')}"

    return fig, summary_text, last_updated_text

# Run the server
if __name__ == '__main__':
    app.run_server(debug=False, host="0.0.0.0", port=8080)

# Expose server for deployment
server = app.server
