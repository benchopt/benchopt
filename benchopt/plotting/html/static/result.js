/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Plot state management
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

const setState = partialState => {
  window.state = {...state(), ...partialState};
  makePlot();
}

/**
 * 
 * @returns Object
 */
const state = () => window.state;

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Plot management
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

const makePlot = () => {
  const div = document.getElementById('unique_plot');
  const data = isBarChart() ? getBarData() : getScatterCurves();
  const layout = isBarChart() ? getBarChartLayout() : getScatterChartLayout();

  Plotly.react(div, data, layout);
};

const getBarData = () => {
  return [{
    type: 'bar',
    x: useTransformer(data(), null, 'x'),
    y: useTransformer(data(), null, 'y'),
  }];
};

const getScatterCurves = () => {
  const curves = [];

  getSolvers().forEach(solver => {
    curves.push({
      type: 'scatter',
      name: solver,
      mode: 'lines+markers',
      line: {
        color: data().solvers[solver].color,
      },
      marker: {
        symbol: data().solvers[solver].marker,
        size: 10,
      },
      legendgroup: solver,
      hovertemplate: solver + ' <br> (%{x:.1e},%{y:.1e}) <extra></extra>',
      visible: isVisible(solver) ? true : 'legendonly',
      x: useTransformer(data(), solver, 'x'),
      y: useTransformer(data(), solver, 'y'),
    });

    if (state().with_quantiles) {
      curves.push({
        type: 'scatter',
        mode: 'lines',
        showlegend: false,
        line: {
          width: 0,
          color: data().solvers[solver].color,
        },
        legendgroup: solver,
        hovertemplate: '(%{x:.1e},%{y:.1e}) <extra></extra>',
        visible: isVisible(solver) ? true : 'legendonly',
        x: useTransformer(data(), solver, 'q1'),
        y: useTransformer(data(), solver, 'y'),
      }, {
        type: 'scatter',
        mode: 'lines',
        showlegend: false,
        fill: 'tonextx',
        line: {
          width: 0,
          color: data().solvers[solver].color,
        },
        legendgroup: solver,
        hovertemplate: '(%{x:.1e},%{y:.1e}) <extra></extra>',
        visible: isVisible(solver) ? true : 'legendonly',
        x: useTransformer(data(), solver, 'q9'),
        y: useTransformer(data(), solver, 'y'),
      });
    }
  });

  return curves;
};

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Data transformers
 * 
 * WARNING : If you add a new transformer function,
 * don't forget to register it in the object : window.tranformers,
 * at the end of this section.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

const useTransformer = (data, solver, axis) => {
  try {
    let transformer = 'transformer_' + axis + '_' + state().plot_kind;
    return window.transformers[transformer](data, solver);
  } catch(e) {
    console.warn('Trying to call unknown transformer for ' + axis + ' axis. The raw data is returned.');
    return data.solvers[solver][axis];
  }
};

const transformer_x_bar_chart = (data, solver) => {
  return getSolvers();
};

const transformer_y_suboptimality_curve = (data, solver) => {
  let y = data.solvers[solver].y;
  // Retrieve c_star value
  const c_star = data.transformers.c_star;
  
  // Compute suboptimality for each data
  return y.map(value => value - c_star);
};

const transformer_y_relative_suboptimality_curve = (data, solver) => {
  let y = data.solvers[solver].y;
  // Retrieve transformer values
  const c_star = data.transformers.c_star;
  const max_f_0 = data.transformers.max_f_0;

  // Compute relative suboptimality for each data
  return y.map(value => (value - c_star) / (max_f_0 - c_star));
};

const transformer_y_bar_chart = (data, solver) => {
  return data.computed_data.bar_chart;
};

window.transformers = {
  transformer_x_bar_chart,
  transformer_y_suboptimality_curve,
  transformer_y_relative_suboptimality_curve,
  transformer_y_bar_chart
};

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Tools
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

const data = () => window.data[state().dataset][state().objective][state().objective_column];

const getSolvers = () => Object.keys(data().solvers);

const isBarChart = () => state().plot_kind === 'bar_chart';

const isVisible = solver => !state().hidden_curves.includes(solver);

const getScale = () => {
  switch (state().scale) {
    case 'loglog':
      return {
        xaxis: 'log',
        yaxis: 'log',
      };
    case "semilog-y":
      return {
        xaxis: 'linear',
        yaxis: 'log',
      };
    case "semilog-x":
      return {
        xaxis: 'log',
        yaxis: 'linear',
      };
    case "linear":
      return {
        xaxis: 'linear',
        yaxis: 'linear',
      };
    default:
      console.error('Unknown scale value : ' + state().scale);
  }
}

const getScatterChartLayout = () => {
  return {
    autosize: true,
    legend: {
      title: {
        text: 'solvers',
      },
      orientation: 'h',
      xanchor: 'center',
      yanchor: 'top',
      y: -.2,
      x: .5
    },
    xaxis: {
      type: getScale().xaxis,
      title: 'Time [sec]',
      tickformat: '.1e',
      tickangle: -45,
    },
    yaxis: {
      type: getScale().yaxis,
      title: getYLabel(),
      tickformat: '.1e',
    },
    title: `${state().objective}\nData: ${state().dataset}`,
  };
};

const getBarChartLayout = () => {
  return {
    width: 900,
    height: 650,
    autosize: false,
    yaxis: {
      type: 'log',
      title: 'Time [sec]',
      tickformat: '.1e',
    },
    xaxis: {
      tickmode: 'array',
      tickangle: -60,
      ticktext: getSolvers(),
      tickvals: getBarColumnPositions(),
      range: [0, 1]
    },
    title: `${state().objective}\nData: ${state().dataset}`,
  };
};

const getYLabel = () => {
  switch(state().plot_kind) {
    case 'objective_curve':
      return 'F(x)';
    case 'suboptimality_curve':
      return 'F(x) - F(x*)';
    case 'relative_suboptimality_curve':
      return 'F(x) - F(x*) / F(x0) - F(x*)'
    case 'bar_chart':
      return 'Time [sec]';
    default:
      return 'unknown';
  };
};

const getBarColumnPositions = () => {
  const width = 1 / (getSolvers().length + 2);
  const xi = [];

  for (let i = 0; i < getSolvers().length; i++) {
    xi.push((i + 1.5) * width);
  }

  return xi;
};

const manageHiddenCurves = event => {
  const curveNumber = event.curveNumber;
  const index = state().hidden_curves.indexOf(event.data[curveNumber].name);

  if (index > -1) {
    state().hidden_curves.splice(index, 1);
    return;
  }

  state().hidden_curves.push(event.data[curveNumber].name);
}