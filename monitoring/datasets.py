import gzip
import os
import shutil
from pathlib import Path
import numpy as np

FASHION_MNIST_PATH = Path('~/fashion-mnist').expanduser()


def load_fashion_mnist(kind='train', data_home=FASHION_MNIST_PATH):
    """Load fashion MNIST data"""
    if kind == 'test':
        kind = 't10k'

    if not data_home.exists():
        os.system(
            f'git clone https://github.com/zalandoresearch/fashion-mnist '
            f'{data_home}'
        )

    path = data_home / 'data/fashion'

    labels_path = path / f'{kind}-labels-idx1-ubyte.gz'
    images_path = path / f'{kind}-images-idx3-ubyte.gz'

    with gzip.open(labels_path, 'rb') as lbpath:
        labels = np.frombuffer(lbpath.read(), dtype=np.uint8,
                               offset=8)

    with gzip.open(images_path, 'rb') as imgpath:
        images = np.frombuffer(imgpath.read(), dtype=np.uint8,
                               offset=16).reshape(len(labels), 784)

    return images, labels


def clear_data_path(data_home=FASHION_MNIST_PATH):
    if data_home.exists():
        shutil.rmtree(data_home)