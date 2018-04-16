"""Version of RandomizedSearchCV from sklearn that incorporates monitoring and
distributed parallelism via Bokeh and Dask.Distributed"""


import logging
from time import time
import os
from datetime import datetime
from bokeh.io import push_notebook
import bokeh.plotting as bp
import numpy as np
import pandas as pd
from dask.distributed import Client, as_completed
from pythonjsonlogger import jsonlogger
from sklearn.model_selection import check_cv, ParameterSampler
from tensorboardX import SummaryWriter

from monitoring.utils import cv_curve_and_table_for_source, source_for_param_space, \
    evaluate


def make_logdir():
    current_time = datetime.now().strftime('%b%d_%H-%M-%S')
    log_dir = os.path.join('runs', current_time)

    os.makedirs(log_dir, exist_ok=True)

    return log_dir


def make_filelogger(log_dir):
    """File-based logging"""
    logger = logging.getLogger(__name__)

    handler = logging.FileHandler(
        filename=os.path.join(log_dir, 'results.log'), mode='a'
    )
    handler.setFormatter(
        jsonlogger.JsonFormatter()
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


def make_summarywriter(log_dir):
    writer = SummaryWriter(log_dir=log_dir)

    return writer


def random_search_cv(est, X, y, param_dist, n_iter=100, cv=3, client=None,
                     log2file=False, log2tbx=False):
    if client is None:
        client = Client()

    if log2file or log2tbx:
        log_dir = make_logdir()
        if log2file:
            logger = make_filelogger(log_dir)
        if log2tbx:
            writer = make_summarywriter(log_dir)

    cv = check_cv(cv)
    source = source_for_param_space(param_dist)
    layout = cv_curve_and_table_for_source(source)
    h = bp.show(layout, notebook_handle=True)

    nworkers = len(client.scheduler_info()['workers'])
    param_iter = iter(ParameterSampler(param_dist, n_iter=n_iter))
    initial_params = [next(param_iter) for _ in range(nworkers)]
    initial_futures = [evaluate(est, X, y, params, cv, client) for params in initial_params]
    params_map = dict(zip(initial_futures, initial_params))
    af = as_completed(initial_futures)

    for step, future in enumerate(af):
        mean_train_score, mean_test_score = future.result()
        source.stream({
            'index': [len(source.data['index'])],
            'mean_test_score': [mean_test_score],
            'cummax_score': [max(np.append(source.data['cummax_score'], mean_test_score))],
            'tstamp': [pd.datetime.fromtimestamp(time())],
            'params': [str(params_map[future])],
        })
        push_notebook(h)

        if log2file:
            logger.info('scoring', extra={
                'mean_test_score': mean_test_score,
                'mean_train_score': mean_train_score,
                'tstamp': time(),
                'params': params_map[future],
            })

        if log2tbx:
            writer.add_scalars('search-results/cv-curve', {
                'mean_test_score': np.array(mean_test_score),
                'cummax_score': np.array(max(np.append(source.data['cummax_score'], mean_test_score))),
            }, step)

        try:
            params = next(param_iter)
            f = evaluate(est, X, y, params, cv, client)
            params_map[f] = params
            af.add(f)
        except StopIteration:
            pass
