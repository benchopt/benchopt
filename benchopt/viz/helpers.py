import numpy as np
from hashlib import md5

import matplotlib.pyplot as plt


def _color_palette(n_colors=4, cmap='viridis', extrema=False):
    """Create a color palette from a matplotlib color map"""
    if extrema:
        bins = np.linspace(0, 1, n_colors)
    else:
        bins = np.linspace(0, 1, n_colors * 2 - 1 + 2)[1:-1:2]

    cmap = plt.get_cmap(cmap)
    palette = list(map(tuple, cmap(bins)[:, :3]))
    return palette


def get_plot_id(benchmark, df):

    hasher = md5()

    # Hash benchmark, dataset, objective and solver names in the benchmark
    hasher.update(benchmark.encode('utf-8'))  # benchmark
    hasher.update(df['data_name'].unique()[0].encode('utf-8'))
    hasher.update(df['objective_name'].unique()[0].encode('utf-8'))
    for s in df['solver_name'].unique():
        hasher.update(s.encode('utf-8'))
    max_n_rep = df['idx_rep'].max()
    max_stop_val = df['stop_val'].max()
    min_stop_val = df['stop_val'].min()
    hasher.update(f'{max_n_rep} {max_stop_val} {min_stop_val}'.encode('utf-8'))
    plot_id = hasher.hexdigest()
    return plot_id
