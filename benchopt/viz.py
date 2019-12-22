import matplotlib.pyplot as plt


def plot_benchmark(df):
    datasets = df.data.unique()
    methods = df.method.unique()
    for data in datasets:
        plt.figure(data)
        df_data = df[df.data == data]
        c_star = df_data.loss.min()
        for m in methods:
            df_ = df_data[df_data.method == m]
            plt.loglog(df_.time, df_.loss - c_star + 1e-7, label=m)
        plt.legend()
    plt.show()
