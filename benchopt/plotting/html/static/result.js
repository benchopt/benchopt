const NON_CONVERGENT_COLOR = 'rgba(0.8627, 0.8627, 0.8627)'

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * STATE MANAGEMENT
 * 
 * The state represent the plot state. It's an object
 * that is stored into the window.state variable.
 * 
 * Do not manually update window.state,
 * instead, foreach state modification,
 * you shoud call the setState() function
 * to keep the plot in sync with its state.
 * 
 * The state contains the following keys :
 *   - dataset (string),
 *   - objective (string),
 *   - objective_column (string),
 *   - plot_kind (string),
 *   - scale (string)
 *   - with_quantiles (boolean)
 *   - hidden_solvers (array)
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Update the state and create/update the plot
 * using the new state.
 * 
 * @param {Object} partialState 
 */
const setState = (partialState, updatePlot = true) => {
  window.state = {...state(), ...partialState};
  displayScaleSelector(!isBarChart());
  if (updatePlot) makePlot();
}

/**
 * Retrieve the state object from window.state
 * 
 * @returns Object
 */
const state = () => window.state;

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * PLOT MANAGEMENT
 * 
 * Retrieve formatted data for PlotlyJS using state
 * and create/update the plot.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Create/Update the plot.
 */
const makePlot = () => {
  const div = document.getElementById('unique_plot');
  const data = isBarChart() ? getBarData() : getScatterCurves();
  const layout = isBarChart() ? getBarChartLayout() : getScatterChartLayout();

  Plotly.react(div, data, layout);
};

/**
 * Gives the data formatted for plotlyJS bar chart.
 * 
 * @returns {array}
 */
const getBarData = () => {
  if (!isAvailable()) return [{type:'bar'}];

  const {x, y, colors, texts} = barDataToArrays()

  // Add bars
  const barData = [{
    type: 'bar',
    x: x,
    y: y,
    marker: {
      color: colors,
    },
    text: texts,
    textposition: 'inside',
    insidetextanchor: 'middle',
    textangle: '-90',
  }];

  x.forEach(solver => {
    // Add times for each convergent solver
    // Check if text is not 'Did not converge'
    if (data(solver).bar.text === '') {
      let nbTimes = data(solver).bar.times.length

      barData.push({
        type: 'scatter',
        x: new Array(nbTimes).fill(solver),
        y: data(solver).bar.times,
        marker: {
          color: 'black',
          symbol: 'line-ew-open'
        },
        line: {
          width: 0
        },
      });
    }
  });

  return barData;
};

/**
 * Gives the data formatted for plotlyJS scatter chart.
 * 
 * @returns {array}
 */
const getScatterCurves = () => {
  // create a list of object to plot in plotly
  const curves = [];

  // For each solver, add the median curve with proper style and visibility.
  getSolvers().forEach(solver => {
    curves.push({
      type: 'scatter',
      name: solver,
      mode: 'lines+markers',
      line: {
        color: data(solver).color,
      },
      marker: {
        symbol: data(solver).marker,
        size: 10,
      },
      legendgroup: solver,
      hovertemplate: solver + ' <br> (%{x:.1e},%{y:.1e}) <extra></extra>',
      visible: isVisible(solver) ? true : 'legendonly',
      x: data(solver).scatter.x,
      y: useTransformer(data(solver).scatter.y, 'y', data().transformers),
    });

    if (state().with_quantiles) {
      // Add shaded area for each solver, with proper style and visibility.
      curves.push({
        type: 'scatter',
        mode: 'lines',
        showlegend: false,
        line: {
          width: 0,
          color: data(solver).color,
        },
        legendgroup: solver,
        hovertemplate: '(%{x:.1e},%{y:.1e}) <extra></extra>',
        visible: isVisible(solver) ? true : 'legendonly',
        x: data(solver).scatter.q1,
        y: data(solver).scatter.y,
      }, {
        type: 'scatter',
        mode: 'lines',
        showlegend: false,
        fill: 'tonextx',
        line: {
          width: 0,
          color: data(solver).color,
        },
        legendgroup: solver,
        hovertemplate: '(%{x:.1e},%{y:.1e}) <extra></extra>',
        visible: isVisible(solver) ? true : 'legendonly',
        x: data(solver).scatter.q9,
        y: data(solver).scatter.y,
      });
    }
  });

  return curves;
};

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * DATA TRANSFORMERS
 * 
 * Transformers are used to modify data
 * on the fly.
 * 
 * WARNING : If you add a new transformer function,
 * don't forget to register it in the object : window.tranformers,
 * at the end of this section.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Select the right transformer according to the state.
 * If the requested transformer does not exists,
 * it returns raw data.
 * 
 * @param {Object} data 
 * @param {String} solver 
 * @param {String} axis it could be x, y, q1, q9
 * @returns {array}
 */
const useTransformer = (data, axis, options) => {
  try {
    let transformer = 'transformer_' + axis + '_' + state().plot_kind;
    return window.transformers[transformer](data, options);
  } catch(error) {
    return data;
  }
};

/**
 * Transform data on the y axis for subotimality curve.
 * 
 * @param {Object} data 
 * @param {String} solver 
 * @returns {array}
 */
const transformer_y_suboptimality_curve = (y, options) => {
  // Retrieve c_star value
  const c_star = options.c_star;
  
  // Compute suboptimality for each data
  return y.map(value => value - c_star);
};

/**
 * Transform data ont the y axis for relative suboptimality curve.
 * 
 * @param {Object} data 
 * @param {String} solver 
 * @returns {array}
 */
const transformer_y_relative_suboptimality_curve = (y, options) => {
  // Retrieve transformer values
  const c_star = options.c_star;
  const max_f_0 = options.max_f_0;

  // Compute relative suboptimality for each data
  return y.map(value => (value - c_star) / (max_f_0 - c_star));
};

/**
 * Store all the transformer functions to be callable
 * by the useTransformer function.
 */
window.transformers = {
  transformer_y_suboptimality_curve,
  transformer_y_relative_suboptimality_curve,
};

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * TOOLS
 * 
 * Various functions to simplify life.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

const data = (solver = null) => {
  return solver ?
    window.data[state().dataset][state().objective][state().objective_column].solvers[solver]:
    window.data[state().dataset][state().objective][state().objective_column]
}

const getSolvers = () => Object.keys(data().solvers);

const isBarChart = () => state().plot_kind === 'bar_chart';

const isVisible = solver => !state().hidden_solvers.includes(solver);

const isSolverAvailable = solver => data(solver).scatter.y.filter(value => !isNaN(value)).length > 0

/**
 * Check for each solver
 * if data is available
 * 
 * @returns {Boolean}
 */
const isAvailable = () => {
  let isNotAvailable = true;

  getSolvers().forEach(solver => {
    if (isSolverAvailable(solver)) {
      isNotAvailable = false;
    }
  });

  return !isNotAvailable;
}

const displayScaleSelector = shouldBeVisible => shouldBeVisible ?
  document.getElementById('change_scaling').style.display = 'inline-block'
  : document.getElementById('change_scaling').style.display = 'none';

const barDataToArrays = () => {
  const colors = [], texts = [], x = [], y = [];

  getSolvers().forEach(solver => {
    x.push(solver);
    y.push(data(solver).bar.y);
    colors.push(data(solver).bar.text === '' ? data(solver).color : NON_CONVERGENT_COLOR);
    texts.push(data(solver).bar.text);
  });

  return {x, y, colors, texts}
}

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
  const layout = {
    width: 900,
    height: 700,
    autosize: false,
    legend: {
      title: {
        text: 'Solvers',
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
      gridcolor: '#ffffff',
      zeroline : false,
    },
    yaxis: {
      type: getScale().yaxis,
      title: getYLabel(),
      tickformat: '.1e',
      gridcolor: '#ffffff',
      zeroline : false,
    },
    title: `${state().objective}\nData: ${state().dataset}`,
    plot_bgcolor: '#e5ecf6',
  };

  if (!isAvailable()) {
    layout.annotations = [{
      xref: 'paper',
      yref: 'paper',
      x: 0.5,
      y: 0.5,
      text: 'Not available',
      showarrow: false,
      font: {
        color: 'black',
        size: 32,
      }
    }];
  };

  return layout;
};

const getBarChartLayout = () => {
  const layout = {
    width: 900,
    height: 700,
    autosize: false,
    yaxis: {
      type: 'log',
      title: 'Time [sec]',
      tickformat: '.1e',
      gridcolor: '#ffffff',
    },
    xaxis: {
      tickangle: -60,
      ticktext: getSolvers(),
    },
    showlegend: false,
    title: `${state().objective}\nData: ${state().dataset}`,
    plot_bgcolor: '#e5ecf6',
  };

  if (!isAvailable()) {
    layout.annotations = [{
      xref: 'paper',
      yref: 'paper',
      x: 0.5,
      y: 0.5,
      text: 'Not available',
      showarrow: false,
      font: {
        color: 'black',
        size: 32,
      }
    }];
  };

  return layout;
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

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * MANAGE HIDDEN SOLVERS
 * 
 * Functions to hide/display and memorize solvers which were clicked
 * by user on the legend of the plot.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */
const getSolverFromPlotlyEvent = event => event.data[event.curveNumber].name;

const purgeHiddenSolvers = () => setState({hidden_solvers: []}, false);

const hideAllSolversExcept = solver => {setState({hidden_solvers: getSolvers().filter(elmt => elmt !== solver)}, false)};

const hideSolver = solver => isVisible(solver) ? setState({hidden_solvers: [...state().hidden_solvers, solver]}, false) : null;

const showSolver = solver => setState({hidden_solvers: state().hidden_solvers.filter(hidden => hidden !== solver)}, false);

/**
 * Add or remove solver name from the list of hidden solvers.
 * 
 * @param {String} solver
 * @returns {void}
 */
const handleSolverClick = solver => {
  if (!isVisible(solver)) {
    showSolver(solver);

    return;
  }

  hideSolver(solver);
};

const handleSolverDoubleClick = solver => {
  if (!isVisible(solver)) {
    purgeHiddenSolvers();

    return;
  }

  hideAllSolversExcept(solver);
};

/**
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * EVENT REGISTRATIONS
 * 
 * Some events are also registered in result.html.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Listener on the system information "+" button
 */
document.getElementById('btn_subinfo').addEventListener('click', event => {
  const elmt = document.getElementById('subinfo');
  const plus = document.getElementById('btn_plus');
  const minus = document.getElementById('btn_minus');

  if (elmt.style.display === 'none') {
      elmt.style.display = 'block';
      plus.style.display = 'none';
      minus.style.display = 'inline';

      return;
  }

  elmt.style.display = 'none';
  plus.style.display = 'inline';
  minus.style.display = 'none';
});
