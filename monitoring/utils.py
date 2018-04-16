import bokeh.models as bm
import bokeh.plotting as bp
import bokeh.layouts as bl
import numpy as np
import pandas as pd


def fit_and_score(est, X_train, y_train, X_valid, y_valid, params):
    est.set_params(**params)
    est.fit(X_train, y_train)
    train_score = est.score(X_train, y_train)
    test_score = est.score(X_valid, y_valid)
    return train_score, test_score


def _mean_for_scores(train_test_scores):
    train_score, test_score = map(np.mean, zip(*train_test_scores))
    return train_score, test_score


def evaluate(est, X, y, params, cv, client):
    scores = []
    for train_inds, test_inds in cv.split(
        X, y
    ):
        X_train, y_train, X_valid, y_valid = (
            X[train_inds],
            y[train_inds],
            X[test_inds],
            y[test_inds]
        )
        train_test_scores = client.submit(
            fit_and_score, est, X_train, y_train, X_valid, y_valid, params)
        scores.append(train_test_scores)
    cv_scores = client.submit(_mean_for_scores, scores)
    return cv_scores


def source_for_param_space(param_space):
    source = bm.ColumnDataSource(
        pd.DataFrame({
            'tstamp': [],
            'cummax_score': [],
            'mean_test_score': [],
            'params': np.array([], dtype=str),
        })
    )
    return source


def datatable_for_source(source):
    columns = [
        bm.TableColumn(field=c, title=c) for c in source.column_names
        if c not in ['index', 'tstamp']
    ]
    columns += [
        bm.TableColumn(
            field='tstamp',
            title='tstamp',
            formatter=bm.DateFormatter(format="%Y-%m-%d %T")
        )
    ]
    table = bm.DataTable(source=source, columns=columns, width=900, height=300)
    return table


def cv_curve_for_source(source):
    ordinal = True

    hover = bm.HoverTool()
    hover.tooltips = [("parameters", "@params")]

    fig = bp.figure(
        plot_width=900, plot_height=300,
        x_axis_type='linear' if ordinal else 'datetime',
        x_axis_label='iteration' if ordinal else 'time',
        y_axis_label='mean cv score', tools="pan,wheel_zoom,box_select,reset",
        logo=None
    )

    fig.grid.visible = False
    x_val = 'index' if ordinal else 'tstamp'
    fig.line(x_val, 'mean_test_score', source=source, line_width=1.5,
             line_join='round', alpha=0.5)
    fig.scatter(x_val, 'mean_test_score', source=source, size=3, alpha=0.5)
    fig.line(x_val, 'cummax_score', source=source, color='orange',
             line_width=1.5, line_join='round')
    fig.scatter(x_val, 'cummax_score', source=source, size=3, color='orange')
    return fig


def cv_curve_and_table_for_source(source):
    curve = cv_curve_for_source(source)
    table = datatable_for_source(source)
    layout = bl.column(
        [curve, table],
    )
    return layout


class log10uniform(object):
    def __init__(self, low, high):
        self.low = low
        self.high = high

    def rvs(self, size=None, random_state=None):
        if random_state:
            pass
        return 10**np.random.uniform(self.low, self.high, size=size)
