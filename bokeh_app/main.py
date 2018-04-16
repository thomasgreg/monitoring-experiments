import logging
import sys
from pathlib import Path
from time import sleep

import bokeh.models as bm
import bokeh.plotting as bp
import pandas as pd
import simplejson as json
from bokeh.core.properties import Instance, Dict, String
from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.models import LayoutDOM, ColumnDataSource, DataTable, TableColumn

logger = logging.getLogger(__name__)

logger.info('Arguments passed: {}'.format(sys.argv))

if len(sys.argv) == 1:
    log_path = Path(__file__).parent / 'test-runs/scoring.log'
else:
    log_path = sys.argv[1]

LOG_COLUMNS = [
    'asctime', 'data_id', 'filename', 'funcName', 'hostname', 'levelname', 'lineno',
    'message', 'module', 'name', 'params', 'processName', 'score', 'split_num',
    'threadName', 'timestamp', 'tstamp'
]


class ParallelCoords(LayoutDOM):
    __javascript__ = "https://d3js.org/d3.v3.min.js"
    __implementation__ = "static/parallel_coords.ts"

    data_source = Instance(ColumnDataSource)
    dtypes = Dict(String, String)


def main(log_path):
    log_path = Path(log_path)

    # wait for the path to exist if it does not already
    while not log_path.exists():
        sleep(1.)

    with open(log_path, 'r') as f:
        lines = f.readlines()

    json_lines = [json.loads(l) for l in lines]

    # filter out those lines that don't contain the 'params' entry
    new_lines = pd.DataFrame([l for l in json_lines if 'params' in l])
    df = new_lines
    new_records = pd.concat([
        df.params.apply(pd.Series).pipe(
            lambda _: _.rename(columns={c: 'param_' + c for c in _.columns})),
        df[['mean_train_score', 'mean_test_score', 'tstamp']]],
        1).sort_values('tstamp')

    # todo: do this setup from within the search code
    source = ColumnDataSource(new_records.iloc[:0].assign(
        cummax_mean_test_score=[]
    ))
    parcoords = ParallelCoords(
        data_source=source,
        dtypes={k: str(v.dtype) for k, v in source.data.items() if
                k not in ['index', 'tstamp']},
        id='parcoords-1'
    )
    columns = [
        TableColumn(field=c, title=c) for c in source.column_names
        if c not in ['index', 'tstamp']
    ]
    columns += [
        TableColumn(
            field='tstamp',
            title='tstamp',
            formatter=bm.DateFormatter(format="%Y-%m-%d %T")
        )
    ]
    table = DataTable(source=source, columns=columns, width=900)

    def cv_curve(source, ordinal=True):
        hover = bm.HoverTool()
        hover.tooltips = [("parameters", "@params")]

        fig = bp.figure(
            plot_width=900, plot_height=200,
            x_axis_type='linear' if ordinal else 'datetime',
            x_axis_label='iteration' if ordinal else 'time',
            y_axis_label='mean cv score', tools="pan,wheel_zoom,box_select,reset",
            logo=None
        )

        fig.grid.visible = False
        x_val = 'index' if ordinal else 'tstamp'

        fig.line(x_val, 'mean_test_score', source=source,  # color='red',
                 line_width=1.5, line_join='round', alpha=1)
        fig.scatter(x_val, 'mean_test_score', source=source, size=3, alpha=1)
        fig.line(x_val, 'cummax_mean_test_score', source=source, line_width=1.5,
                 line_join='round', color='orange', alpha=0.5)

        return fig

    layout = column(
        [parcoords, cv_curve(source, ordinal=True), table],
        id='column-layout-1')

    return source, layout


source, layout = main(log_path=log_path)
doc = curdoc()
doc.add_root(layout)

outstanding_list = []

f = open(log_path, 'r')


def update():
    lines = f.readlines()

    json_lines = [json.loads(l) for l in lines]

    # filter out those lines that don't contain the 'params' entry
    # (incase we any other kind of logging)
    new_lines = pd.DataFrame([l for l in json_lines if 'params' in l])

    if len(new_lines) > 0:
        df = new_lines
        new_records = pd.concat([df.params.apply(pd.Series).pipe(lambda _: _.rename(
                columns={c: 'param_' + c for c in _.columns})
        ), df[['mean_train_score', 'mean_test_score', 'tstamp']]], 1).sort_values(
            'tstamp')
        if len(new_records):
            new_records['cummax_mean_test_score'] = new_records['mean_test_score']
            if len(source.data['cummax_mean_test_score']) > 0:
                new_records['cummax_mean_test_score'].iloc[0] = \
                source.data['cummax_mean_test_score'][-1]
            new_records['cummax_mean_test_score'] = new_records[
                'cummax_mean_test_score'].cummax()
            new_records['tstamp'] = new_records.tstamp * 1000
            new_records = new_records.reset_index(drop=True)
            new_records = new_records.set_index(
                new_records.index + len(source.data['index'])).reset_index()
            source.stream({
                k: v.values.tolist()
                for k, v in new_records.items()
            })


doc.add_periodic_callback(update, 1000)
