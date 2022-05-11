import re
import os
import itertools
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from pathlib import Path
from matplotlib import rc
import matplotlib.pyplot as plt

# matplotlib style config
fontsize = 12
rc('font', **{'family': 'sans-serif',
              'sans-serif': ['Computer Modern Roman']})
usetex = matplotlib.checkdep_usetex(True)
params = {'axes.labelsize': fontsize,
          'font.size': fontsize,
          'legend.fontsize': fontsize,
          'xtick.labelsize': fontsize - 2,
          'ytick.labelsize': fontsize - 2,
          'text.usetex': usetex,
          'figure.figsize': (8, 6)}
plt.rcParams.update(params)
sns.set_palette('colorblind')
sns.set_style("ticks")

MARKERS = list(plt.Line2D.markers.keys())[:-4]
CMAP = plt.get_cmap('tab20')
#####


SAVEFIG = False
figname = "demo_fig"

BENCH_NAME = './dist_outputs/benchopt_run_2022-05-11_11h21m02.csv'  # meg + leukemia

FLOATING_PRECISION = 1e-8
MIN_XLIM = 1e-3

DICT_XLIM = {
    "libsvm[dataset=rcv1.binary]": 1e-2,
    "libsvm[dataset=news20.binary]": 1e-1,
    "MEG": 1e-2,
    "finance": 1e-1,
}


df = pd.read_csv(BENCH_NAME, header=0, index_col=0)

solvers = df["solver_name"].unique()
solvers = np.array(sorted(solvers, key=str.lower))
datasets = df["data_name"].unique()
objectives = df["objective_name"].unique()

fontsize = 20
labelsize = 20
regex = re.compile('\[(.*?)\]')

plt.close('all')
main_fig, axarr = plt.subplots(
    len(datasets),
    len(objectives),
    sharex=False,
    sharey=True,
    figsize=[12, 0.8 + 2.5 * len(datasets)],
    constrained_layout=True)

# handle if there is only 1 dataset/objective:
if len(datasets) == 1:
    if len(objectives) == 1:
        axarr = np.atleast_2d(axarr)
    else:
        axarr = axarr[None, :]
elif len(objectives) == 1:
    axarr = axarr[:, None]

for idx_data, dataset in enumerate(datasets):
    df1 = df[df['data_name'] == dataset]
    for idx_obj, objective in enumerate(objectives):
        df2 = df1[df1['objective_name'] == objective]
        ax = axarr[idx_data, idx_obj]
        # check that at least one solver converged to compute c_star
        # if df2["objective_duality_gap"].min() > FLOATING_PRECISION * df2["objective_duality_gap"].max():
        #     print(
        #         f"No solver reached a duality gap below {FLOATING_PRECISION}, "
        #         "cannot safely evaluate minimum objective."
        #     )
        #     continue
        c_star = np.min(df2["objective_value"]) - FLOATING_PRECISION
        for i, solver_name in enumerate(solvers):
            df3 = df2[df2['solver_name'] == solver_name]
            curve = df3.groupby('stop_val').median()

            y = curve["objective_value"] - c_star

            ax.loglog(
                curve["time"], y, color=CMAP(i), marker=MARKERS[i], markersize=6,
                label=solver_name, linewidth=2)

        ax.set_xlim([DICT_XLIM.get(dataset, MIN_XLIM), ax.get_xlim()[1]])
        axarr[len(datasets)-1, idx_obj].set_xlabel(
            "Time (s)", fontsize=fontsize - 2)
        axarr[0, idx_obj].set_title(
            '\n'.join(regex.search(objective).group(1).split(",")), fontsize=fontsize - 2)
        ax.tick_params(axis='both', which='major', labelsize=labelsize)

    if regex.search(dataset) is not None:
        dataset_label = (regex.sub("", dataset) + '\n' +
                         '\n'.join(regex.search(dataset).group(1).split(',')))
    else:
        dataset_label = dataset
    axarr[idx_data, 0].set_ylabel(
        dataset_label, fontsize=fontsize - 6)

main_fig.suptitle(regex.sub('', objective), fontsize=fontsize)
plt.show(block=False)

# plot legend on separate fig
leg_fig, ax2 = plt.subplots(1, 1, figsize=(20, 4))
n_col = 3
if n_col is None:
    n_col = len(axarr[0, 0].lines)

# take first ax, more likely to have all solvers converging
ax = axarr[0, 0]
lines_ordered = list(itertools.chain(*[ax.lines[i::n_col] for i in range(n_col)]))
legend = ax2.legend(
    lines_ordered, [line.get_label() for line in lines_ordered], ncol=n_col,
    loc="upper center")
leg_fig.canvas.draw()
leg_fig.tight_layout()
width = legend.get_window_extent().width
height = legend.get_window_extent().height
leg_fig.set_size_inches((width / 80,  max(height / 80, 0.5)))
plt.axis('off')
plt.show(block=False)


if SAVEFIG:
    Path('./figures').mkdir(exist_ok=True)
    main_fig_name = f"figures/{figname}.pdf"
    main_fig.savefig(main_fig_name)
    os.system(f"pdfcrop {main_fig_name} {main_fig_name}")
    main_fig.savefig(f"figures/{figname}.svg")

    leg_fig_name = f"figures/{figname}_legend.pdf"
    leg_fig.savefig(leg_fig_name)
    os.system(f"pdfcrop {leg_fig_name} {leg_fig_name}")
    leg_fig.savefig(f"figures/{figname}_legend.svg")
