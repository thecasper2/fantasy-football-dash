from dash import Dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import pandas as pd
import plotly.graph_objs as go
from sqlalchemy import create_engine


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)
database = "fantasy_football"

con = create_engine("mysql+mysqldb://root:@localhost/{database}".format(database=database))

# Queries
query_player_summary = "SELECT * FROM player_summary"
query_player_history = """
SELECT * 
FROM fantasy_football.player_history a
JOIN (SELECT MAX(timestamp) AS timestamp FROM fantasy_football.player_history) b
ON a.timestamp = b.timestamp
"""

# Player summary
player_summary = pd.read_sql_query(query_player_summary, con)
player_summary["full_name"] = player_summary.first_name + " " + player_summary.second_name
player_summary_numeric_columns = \
    pd.Series(
        player_summary.select_dtypes(include=['int16', 'int32', 'int64', 'float16', 'float32', 'float64']).columns
    )

# Player history
player_history = pd.read_sql_query(query_player_history, con)
player_history_numeric_columns = \
    pd.Series(
        player_history.select_dtypes(include=['int16', 'int32', 'int64', 'float16', 'float32', 'float64']).columns
    )

app.layout = html.Div([
    html.H1("Fantasy Football Analyser"),
    html.Div("Analyse the shit out of your fantasy football team"),
    html.Div([
        html.Div([dcc.Graph(id="summary-plot")], className="eight columns"),
        html.Div([
            "Metrics",
            dcc.Dropdown(
                id="metric-list-1x",
                options=(
                    pd.DataFrame(dict(label=player_summary_numeric_columns, value=player_summary_numeric_columns))
                    .to_dict("records")
                ),
                value="minutes",
                clearable=False
            ),
            dcc.Dropdown(
                id="metric-list-1y",
                options=(
                    pd.DataFrame(dict(label=player_summary_numeric_columns, value=player_summary_numeric_columns))
                    .to_dict("records")
                ),
                value="goals_conceded",
                clearable=False
            ),
            "Selected players",
            dt.DataTable(
                id="player-table",
                columns=[{"name": i, "id": i} for i in ["full_name", "now_cost"]],
                pagination_settings={"page_size": 8, "current_page": 0}
            )
        ], className="three columns")
    ], className="five rows"),
    html.Div([
        html.Div([dcc.Graph(id="player-history-plot")], className="eight columns"),
        html.Div([
            "Player",
            dcc.Dropdown(
                id="player-list",
                options=(
                    player_summary[["full_name", "id"]]
                    .rename(columns={"full_name": "label", "id": "value"})
                    .to_dict("records")
                ),
                value=player_summary["id"][0],
                clearable=False,
                multi=True
            ),
            "Metric",
            dcc.Dropdown(
                id="metric-list-2",
                options=(
                    pd.DataFrame(dict(label=player_history_numeric_columns, value=player_history_numeric_columns))
                    .to_dict("records")
                ),
                value="goals_conceded",
                clearable=False
            ),
            "Style",
            dcc.Dropdown(
                id="style-list",
                options=(
                    [
                        {"label": "lines", "value": "lines"},
                        {"label": "markers", "value": "markers"},
                        {"label": "lines and markers", "value": "lines+markers"},
                    ]
                ),
                value="lines+markers",
                clearable=False
            ),
        ], className="three columns")
    ], className="five rows"),
    # html.Div([
    #     html.Div([dcc.Graph(id="player-development")], className="twelve columns")
    # ], className="five rows"),
    # html.Div([
    #     html.Div([
    #         dcc.Slider(
    #             id="player-development-slider",
    #             min=1,
    #             max=38,
    #             marks={i: str(i) for i in range(1, 39)},
    #             value=1
    #         )
    #     ], className="eleven columns")
    # ], className="two rows")
])


@app.callback(
    Output('player-table', 'data'),
    [Input('summary-plot', 'selectedData')])
def display_selected_data(selected_data):
    if selected_data is None:
        return player_summary.to_dict("rows")
    indices = [p["pointIndex"] for p in selected_data["points"]]
    return player_summary.iloc[indices].to_dict("rows")


@app.callback(
    Output("player-history-plot", "figure"),
    [
        Input("player-list", "value"),
        Input("metric-list-2", "value"),
        Input("style-list", "value")
    ]
)
def update_player_history_plot(player, metric, style):
    if isinstance(player, list):
        data = [
            go.Scatter(
                x=player_history[player_history.element == p]["round"],
                y=player_history[player_history.element == p][metric],
                mode=style,
                name=player_summary[player_summary["id"] == p]["full_name"].to_list()[0]
            )
            for p in player
        ]
    else:
        data = [
            go.Scatter(
                x=player_history[player_history.element == player]["round"],
                y=player_history[player_history.element == player][metric],
                mode=style,
                name=player_summary[player_summary["id"] == player]["full_name"].to_list()[0]
            )
        ]

    return go.Figure(
        data=data,
        layout=go.Layout(
            xaxis=dict(title="Round"),
            yaxis=dict(title=metric),
            hovermode="closest"
        )
    )


@app.callback(
    Output("summary-plot", "figure"),
    [
        Input("metric-list-1x", "value"),
        Input("metric-list-1y", "value")
    ]
)
def update_summary_plot(x, y):
    elements = ["GK", "DF", "MF", "FW"]
    return go.Figure(
        data=[
            go.Scatter(
                x=player_summary[player_summary.element_type == element_type][x],
                y=player_summary[player_summary.element_type == element_type][y],
                text=player_summary[player_summary.element_type == element_type].full_name,
                mode="markers",
                name=elements[element_type-1]
            ) for element_type in [1, 2, 3, 4]
        ],
        layout=go.Layout(
            xaxis=dict(title=x),
            yaxis=dict(title=y),
            hovermode="closest"
        ),
    )


# @app.callback(
#     Output("player-development", "figure"),
#     [
#         Input("player-development-slider", "value")
#     ]
# )
# def update_player_development(value):
#     query = "round <= {round} and element == 23".format(round=value)
#     return go.Figure(
#         data=[
#             go.Scatter(
#                 x=player_history.query(query).total_points,
#                 y=player_history.query(query).attempted_passes,
#                 mode="lines+markers",
#                 line=dict(color='#00CED1', width=3)
#             )
#         ],
#         layout=go.Layout(
#             xaxis=dict(title="Total points", range=[-1, 20]),
#             yaxis=dict(title="Attempted passes", range=[0, 100]),
#             hovermode="closest"
#         )
#     )


if __name__ == '__main__':
    app.run_server(debug=True)
    # app.run_server(debug=False, port=8080, host="0.0.0.0")
