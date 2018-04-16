Experiments in monitoring hyperparameter optimisation with Python.

To run example notebooks, install the environment:

    cd <source directory>
    conda env create

Start the Jupyter notebook:

    cd <source directory>/notebooks && jupyter notebook

To run the bokeh application, after starting a search
(as in `notebooks/2 - RF classifier example.ipynb`):

    bokeh serve bokeh_app --show --args <path of the scoring.log file>
