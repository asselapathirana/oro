# -*- coding: utf-8 -*-
import sys
import dash
import dash_core_components as dcc
from dash import  html
import plotly.graph_objs as go
import math
import json
from dash.exceptions import PreventUpdate


import numpy as np

import metpy.calc as mc
from metpy.units import units, concatenate, check_units

from itertools import cycle

app = dash.Dash('Orographic rainfall demo app')
server = app.server
value_range = [-5, 5]
ANIM_DELTAT = 500
MAXMNHT = 2500
WINDMTRATIO = 2
WINDMTOFFSET = 1000
XPEAK = 100  # x value at which peak occures
SHAPEFA = 20

XMAX = XPEAK * 2  #
XSTEP = 10
# do one number more than XMAX/XSTEP then have inf on each side.
XVALUES = np.append(-99999999, np.arange(0, XMAX + .01, XSTEP), 99999999)
MTNX = np.arange(-XMAX * .01, XMAX * 1.01, 1)

# symbol size and name
sym_nop = (10, 'circle', 'No precip.')
sym_lp = (25, "star", 'Liquid precip.')
sym_ip = (30, 'hexagram', 'Ice precip.')
sym_parcel = (50, 'y-right-open', 'Air parcel')

banner = html.Div([
    html.H2("Orographic rainfall demo"),
    html.Img(src=app.get_asset_url("apLogo2.png")),
], className='banner')

row1 = html.Div([  # row 1 start ([
    html.Div(
        dcc.Graph(
            animate=False,
            id='graph-2',
            config={
                'displayModeBar': False}),
        className="eight columns"),
    html.Div(
        [html.Div(dcc.Graph(animate=False, id='graphRHEl', config={'displayModeBar': False}), className="row"),
         html.Div(
            dcc.Graph(
                animate=False,
                id='graphTEl',
                config={
                    'displayModeBar': False}),
             className="row"),
         html.Div(
            dcc.Interval(
                id='ncounter',
                interval=ANIM_DELTAT,
                n_intervals=0)),
            # no display
            html.Div(
            id='calculations_store', style={
                'display': 'none'})  # no display
         ], className="four columns "),
], className="row")  # row 1 end ])

slider1 = html.Div(
    [
        html.Div('Mountain Height'),
        dcc.Slider(
            id='height',
            min=0,
            max=MAXMNHT,
            step=250,
            value=1500,
            marks={
                i: str(i) for i in range(
                    0,
                    MAXMNHT + 1,
                    1000)}),
    ],
    className="three columns")
slider2 = html.Div(
    [
        html.Div('Humidity of air (%)'),
        dcc.Slider( 
            id='humid',
            min=1,
            max=100,
            step=5,
            value=40,
            marks={
                i: str(i) for i in range(
                    0,
                    100 + 1,
                    20)}),
    ],
    className="three columns")
slider3 = html.Div([html.Div('Temperature of air (°C)'),
                    dcc.Slider(id='temp',
                               min=-20,
                               max=50,
                               step=1,
                               value=30,
                               marks={i: str(i) for i in range(-20,
                                                          50 + 1,
                                                          10)},
                               ),
                    ],
                   className="three columns",
                   )  # style={"margin-top": "25px"}
button = html.Div([html.Button('Re-run', id='button'),
                   ], className="three columns", )

row2 = html.Div([  # begin row 2
    slider1,
    slider2,
    slider3,
    button,
], className="row")  # end row 2

app.layout = html.Div([  # begin container
    banner,
    row1,
    row2,
], className="container",
)  # end container

"""The function that 'disables' the counter. Use together with reset_counter function below"""


@app.callback(dash.dependencies.Output('ncounter', 'interval'),
              [dash.dependencies.Input('ncounter', 'n_intervals'),
               ])
def disable_counter(n_intervals):
    if n_intervals > len(XVALUES):
        return 100 * 60 * 60 * 1000
    return ANIM_DELTAT


"""The function that 'resets' the counter to 0. Use together with disable_counter function above."""


@app.callback(
    dash.dependencies.Output('ncounter', 'n_intervals'),
    [dash.dependencies.Input('height', 'value'),
     dash.dependencies.Input('temp', 'value'),
     dash.dependencies.Input('humid', 'value'),
     dash.dependencies.Input('button', 'n_clicks'),
     ],
)
def reset_counter(height, temp, humid, n_clicks):
    if n_clicks is None:
        # prevent the None callbacks is important with the store component.
        # you don't want to update the store for nothing.
        raise PreventUpdate
    return 0


@app.callback(
    dash.dependencies.Output('calculations_store', 'children'),
    [dash.dependencies.Input('height', 'value'),
     dash.dependencies.Input('temp', 'value'),
     dash.dependencies.Input('humid', 'value'),
     ]
)
def calculate_set(height, temp, humid):
    sc = saveCalc(height, temp, humid)
    st = json.dumps(sc)
    return st


@app.callback(
    dash.dependencies.Output('graphRHEl', 'figure'),
    [dash.dependencies.Input('ncounter', 'n_intervals'),
     ],
    [dash.dependencies.State('calculations_store', 'children'),
     ]
)
def update_RHElGraph(counterval, calculation_store_data):
    windy, windx, mtny, TC, RH, trace, LCL = load_json(calculation_store_data)
    length = min([counterval, len(XVALUES)])

    return {
        'data': [{'x': RH[:length], 'y': windy[:length], 'mode': 'lines+markers', },
                 dict({'x': [0, 100], 'y': [LCL, LCL]}, **trace[7]), ],
        'layout': {'xaxis': {'range': [-5, 105], 'title': 'RH (%)'},
                   'yaxis': {'range': [min(windy) * .95, max(windy) * 1.05], 'title': 'Elevation (m)'},
                   'height': 220,
                   'margin': {
                       'l': 60,
                       'r': 40,
                       'b': 40,
                       't': 10,
                       'pad': 4,
        },
            'showlegend': False,
        },
    }


@app.callback(
    dash.dependencies.Output('graphTEl', 'figure'),
    [dash.dependencies.Input('ncounter', 'n_intervals'),
     ],
    [dash.dependencies.State('calculations_store', 'children'),
     ]
)
def update_TElGraph(counterval, calculation_store_data):
    windy, windx, mtny, TC, RH, trace, LCL = load_json(calculation_store_data)
    length = min([counterval, len(XVALUES)])
    tr = [min(TC) - 2, max(TC) + 2]
    return {
        'data': [{'x': TC[:length], 'y': windy[:length], 'mode': 'lines+markers', },
                 dict({'x': tr, 'y': [LCL, LCL]}, **trace[7]), ],
        'layout': {'xaxis': {'range': tr, 'title': 'T (°C)'},
                   'yaxis': {'range': [min(windy) * .95, max(windy) * 1.05], 'title': 'Elevation (m)'},
                   'height': 220,
                   'margin': {
                       'l': 60,
                       'r': 40,
                       'b': 40,
                       't': 10,
                       'pad': 4
        },
            'showlegend': False
        },
    }


def load_json(calculation_store_data):
    if calculation_store_data:
        return json.loads(calculation_store_data)
    else: 
        raise  PreventUpdate

@app.callback(
    dash.dependencies.Output('graph-2', 'figure'),
    [dash.dependencies.Input('ncounter', 'n_intervals')
     ],
    [dash.dependencies.State('calculations_store', 'children'),
     ]
)
def update_mainGraph(counterval, calculation_store_data):
    windy, windx, mtny, TC, RH, trace, LCL = load_json(calculation_store_data)
    length = min([counterval, len(XVALUES)])
    x = [windx[length - 1]]
    y = [windy[length - 1]]

    return {
        'data': [dict({'x': windx[:length], 'y': windy[:length]}, **trace[1]), # all points travelled by air parcel. 
                 dict({'x': x, 'y': y}, **trace[0]), # air parcel 
                 dict({'x': MTNX, 'y': mtny}, **trace[2]), # mountain 
                 dict({'x': ['null'], 'y': ['null']}, **trace[3]), # legend (fake data)
                 dict({'x': ['null'], 'y': ['null']}, **trace[4]), # legend (fake data)
                 dict({'x': ['null'], 'y': ['null']}, **trace[5]), # legend (fake data)
                 dict({'x': ['null'], 'y': ['null']}, **trace[6]), # legend (fake data)
                 dict({'x': [0, XMAX / 3., XMAX * 2. / 3., XMAX], 'y': [LCL, LCL, LCL, LCL]}, **trace[7]), # lcl 
                 ],
        'layout': {
            'xaxis': {'range': [0, XMAX * 1.05], 'title': 'Distance (km)'},
            'yaxis': {'range': [0, 1.1 * windh(0, MAXMNHT, xoffset=0)], 'title': 'Elevation (m)'},
            'margin': {
                'l': 60,
                'r': 40,
                'b': 40,
                't': 10,
                'pad': 4
            },
            'legend': {'x': .01, 'y': 1.},
        }
    }


def saveCalc(height, temp, humid):
    windx, mtny, windy, lcl_, LCL, TC, RH = atmCalc(height, temp, humid)
    # now remove the first item from all (first x value is far away in negative!)
    windx=windx[1:]
    windy=windy[1:]
    TC=TC[1:] 
    RH=RH[1:]
    
    txt = ["{:.1f} °C/ {:.0f} %".format(t, rh * 100.)
           for t, rh in zip(TC.magnitude, RH.magnitude)]

    colorscale = 'Viridis'

    size, symbol, name = zip(*
                             [sym_nop if v *
                              units.meters < LCL or x > XPEAK else sym_lp if t > 0 *
                              units.degC else sym_ip for x, v, t in zip(windx, windy, TC)])

    trace1 = {'mode': 'markers',
              'marker': {
                  'size': sym_parcel[0],
                  'color': 'black',
                  'symbol': sym_parcel[1], },
              'showlegend': False,
              'hoverinfo': 'none',
              }
    trace2 = {'mode': 'markers',
              'marker': {
                  'symbol': symbol,
                  'size': size,
                  'opacity': 1.0,
                  'color': (RH.magnitude * 100.).tolist(),  # no numpy
                  'colorscale': colorscale,
                  'cmin': 0,
                  'cmax': 100.,
                  'reversescale': True,
                  'colorbar': {'title': 'RH (%)'},
                  #   'line': {
                  #       'width': 0.5,
                  #       'color': 'black'
                  #   }
              },
              'text': txt,
              'hoverinfo': 'text',
              'showlegend': False,

              }
    trace3 = {
        'fill': 'tozeroy',
        'hoverinfo': 'none',
        'showlegend': False,

    }

    tr = [{'mode': 'markers',  # to create the legend.
           'marker': {
               'symbol': x[1],
               'size': 15,
               'color': 'black',
           },
           'line': {
               'color': 'rgb(231, 99, 250)',
               'width': 2
           },
           'name': x[2],
           'showlegend': True,
           }
          for x in [sym_parcel, sym_nop, sym_lp, sym_ip]
          ]

    trlcl = [
        dict(
            mode='lines+text',
            name='Lines and Text',
            text=['Lifting Condensation Level'],
            line=dict(
                color='rgb(55, 206, 204)',
                width=2),
            textposition='bottom right',
            hoverinfo='text',
            showlegend=False,
        )]

    trace = [trace1, trace2, trace3] + tr + trlcl
    RH = RH * 100.
    return windy.tolist(), windx.tolist(), mtny.tolist(), TC.magnitude.tolist(
    ), RH.magnitude.tolist(), trace, LCL.to("meters").magnitude  # no numpy


def atmCalc(height, temp, humid):
    print("ATMCALC", height, temp, humid, file=sys.stderr)
    mtny = windh(MTNX, height, ratio=1,
                 yoffset=0)

    windx = XVALUES
    windy = windh(windx, height)

    temp_ = temp * units.degC
    initp = mc.height_to_pressure_std(windy[0] * units.meters)
    dewpt = mc.dewpoint_from_relative_humidity(temp_, humid / 100.)
    lcl_ = mc.lcl(initp, temp_, dewpt, max_iters=50, eps=1e-5)
    LCL = mc.pressure_to_height_std(lcl_[0])

    if (lcl_[0] > mc.height_to_pressure_std(max(windy) * units.meters)
            and LCL > windy[0] * units.meters * 1.000009):
        # add LCL to x
        xlcl = windh(LCL.to('meters').magnitude, height, inv=True)
        windx = np.sort(np.append(windx, xlcl))
        windy = windh(windx, height)

    pressures = mc.height_to_pressure_std(windy * units.meters)

    wvmr0 = mc.mixing_ratio_from_relative_humidity(initp , temp_, humid / 100.)

    # now calculate the air parcel temperatures and RH at each position
    if (lcl_[0] <= min(pressures)):
        T = mc.dry_lapse(pressures, temp_)
        RH = [
            mc.relative_humidity_from_mixing_ratio(
                p, t, wvmr0) for t, p in zip(
                T, pressures)]
    else:
        mini = np.argmin(pressures)
        p1 = pressures[:mini + 1]
        p2 = pressures[mini:]  # with an overlap
        p11 = p1[p1 >= lcl_[0] * .9999999]  # lower (with tol) with lcl
        p12 = p1[p1 < lcl_[0] * 1.000009]  # upper (with tol) with lcl
        T11 = mc.dry_lapse(p11, temp_)
        T12 = mc.moist_lapse(p12, lcl_[1])
        T1 = concatenate((T11[:-1], T12))
        T2 = mc.dry_lapse(p2, T1[-1])
        T = concatenate((T1, T2[1:]))
        wvmrtop = mc.saturation_mixing_ratio(pressures[mini], T[mini])

        RH = [mc.relative_humidity_from_mixing_ratio(*tp, wvmr0) if tp[0] > lcl_[
            0] and i <= mini else 1.0 if i < mini else
            mc.relative_humidity_from_mixing_ratio(*tp, wvmrtop)
            for i, tp in enumerate(zip( pressures, T))]

    RH = concatenate(RH)
    return windx, mtny, windy, lcl_, LCL, T.to("degC"), RH


def windh(
        val,
        maxht,
        xoffset=XPEAK,
        div=SHAPEFA,
        ratio=WINDMTRATIO,
        yoffset=WINDMTOFFSET,
        inv=False):
    if inv:
        f = div * math.sqrt(maxht * ratio / (val - yoffset) - 1)
        return xoffset - f, xoffset + f
    return maxht * ratio / (1 + ((val - xoffset) / div) ** 2.) + yoffset


# load the styles
external_css = [
    "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
    "/static/boxed.css",
    "https://fonts.googleapis.com/css?family=Raleway:400,400i,700,700i",
    "https://fonts.googleapis.com/css?family=Product+Sans:400,400i,700,700i"]
for css in external_css:
    app.css.append_css({"external_url": css})

if __name__ == '__main__':
    app.run_server(debug=False)
    #, use_debugger=False, use_reloader=False)
    # d=calculate_set(3.897692586860594*1000, 25, 20)
    # d=calculate_set(1500, 25, 50)
    # d=calculate_set(1500, 30, 40)
    # d=calculate_set(1500,30,20)
    # d=calculate_set(1500,30,20)
    # calculate_set(1500, 20, 30)
    # update_mainGraph(150,d)
    # d=calculate_set(1500, 30, 100)
