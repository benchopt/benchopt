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
 *   - xaxis_type (string)
 *   - hidden_solvers (array)
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Update the state and create/update the plot
 * using the new state.
 *
 * @param {Object} partialState
 */
const setState = (partialState) => {
  window.state = {...state(), ...partialState};
  displayScatterElements(!isBarChart());

  // TODO: `listIdXaxisSelection` to be removed after
  // implementing responsiveness through breakpoints
  // and removing content duplication between big screen and mobile
  let listIdXaxisSelection = ["change_xaxis_type", "change_xaxis_type_mobile"];
  listIdXaxisSelection.forEach(idXaxisSelection => updateXaxis(idXaxisSelection))

  makePlot();
  makeLegend();
}

/**
 * Retrieve the state object from window.state
 *
 * @returns Object
 */
const state = () => window.state;

/**
 * Mapping between selectors and configuration
*/
const config_mapping = {
  'dataset': 'dataset_selector',
  'objective': 'objective_selector',
  'objective_column': 'objective_column',
  'kind': 'plot_kind',
  'scale': 'change_scaling',
  'with_quantiles': 'change_shades',
  'xaxis_type':'change_xaxis_type',
};

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
  let xaxisType = state().xaxis_type;

  getSolvers().forEach(solver => {
    solverSamplingStrategy = data(solver)['sampling_strategy'];

    // plot only solvers that were stopped using xaxis type
    // plot all solver if xaxis type is `time`
    if(xaxisType !== "Time" && solverSamplingStrategy !== xaxisType) {
      return
    }

    ScatterXaxisProperty = xaxisType === "Time" ? 'x' : 'stop_val';

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
      x: data(solver).scatter[ScatterXaxisProperty],
      y: useTransformer(data(solver).scatter.y, 'y', data().transformers),
    });

    // skip plotting quantiles if xaxis is not time
    // as stop_val are predefined and hence deterministic
    if(xaxisType !== "Time") {
      return
    }

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
        x: data(solver).scatter['q1'],
        y: useTransformer(data(solver).scatter.y, 'y', data().transformers),
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
        x: data(solver).scatter['q9'],
        y: useTransformer(data(solver).scatter.y, 'y', data().transformers),
      });
    }
  });

  return curves;
};



/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * CONFIG MANAGEMENT
 *
 * Configs are used to save particular benchmark results' views.
 *
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

const get_lim_plotly = (lim, ax) =>{
  if(getScale()[ax + 'axis'] == 'log'){
    lim = [Math.log10(parseFloat(lim[0])), Math.log10(parseFloat(lim[1]))]
  };
  return lim;
};
const get_lim_config = (lim, ax) =>{
  if(getScale()[ax + 'axis'] == 'log'){
    lim = [Math.pow(10, lim[0]), Math.pow(10, lim[1])]
  };
  return lim;
};


const setConfig = (config_item) =>{
  // Retrieve the name of the config.
  let config_name = config_item.textContent;
  // Select on mobile version
  if (config_item.tagName === "SELECT") {
    config_name = config_item.value;
  }

  // Clear all selected views and select the good one.
  setAllViewsToNonActive();
  config_item.classList.add('active');
  // Select on mobile version
  if (config_item.tagName === "SELECT") {
    config_item.value = config_name;
  }

  if (config_name !== "no_selected_view") {
    // Get the updated state
    let config = window.metadata.plot_configs[config_name];
    let update = {};
    const lims = ['xlim', 'ylim', 'hidden_solvers']
    for(let key in config_mapping){
      if (key in config){
        value = config[key];
        document.getElementById(config_mapping[key]).value = value;
        if (key == "kind"){
          key = "plot_kind";
        }
        update[key] = value;
      }
      else if (!lims.includes(key)) {
        document.getElementById(config_mapping[key]).selectedIndex = 0;
        update[key] = document.getElementById(config_mapping[key]).value;
      }
    }

    setState(update);

    let layout = {};
    for(const ax of ['x', 'y']){
      let lim = ax + 'lim';
      if (config.hasOwnProperty(lim) & (config[lim] != null)){
        layout[ax +'axis.range'] = get_lim_plotly(config[lim], ax);
      };
    };

    // update the plot
    const div = document.getElementById('unique_plot');
    Plotly.relayout(div, layout);
  }
};


const saveView = () => {
  let n_configs = Object.keys(window.metadata.plot_configs).length;

  let config_name = prompt("Config Name", "Config " + n_configs);
  if(config_name === null || config_name === ""){
    return;
  }

  // Retrieve the drop down menue selected values
  let config = {};
  for(let key in config_mapping) {
    value = config[key];
    config[key] = document.getElementById(config_mapping[key]).value;
  }

  // Retrieve the range of the plots.
  const fig = document.getElementById('unique_plot');
  config['xlim'] = get_lim_config(fig.layout.xaxis.range, 'x');
  config['ylim'] = get_lim_config(fig.layout.yaxis.range, 'y');

  let noViewAvailableElement = document.getElementById('no_view_available');

  if (noViewAvailableElement) {
    noViewAvailableElement.classList.add('hidden');
  }
  setAllViewsToNonActive();

  // Only add a button if the config does not exist yet:
  if (!(config_name in window.metadata.plot_configs)){
    let viewTabs = document.getElementById("view-tabs");
    let node = document.createElement("span");
    node.innerHTML = config_name;
    node.className = "view border-transparent whitespace-nowrap border-b-2 py-4 px-1 text-sm text-gray-400 hover:text-gray-500 hover:border-gray-300 cursor-pointer active";
    node.onclick = function() {setConfig(node)};
    viewTabs.appendChild(node);

    let option = document.createElement("option");
    option.setAttribute("value", config_name);
    option.innerHTML = config_name;
    let tabs = document.getElementById("tabs");
    tabs.appendChild(option);
    tabs.value = config_name;
  }

  // Add the config in the configs mapping.
  window.metadata.plot_configs[config_name] = config;

  return false;
};

const setAllViewsToNonActive = () => {
  let view_items = document.getElementsByClassName('view');
  for (let i = 0; i < view_items.length; i++) {
     view_items.item(i).classList.remove('active');
  }

  document.getElementById('tabs').value = "no_selected_view";
}

const downloadBlob = (blob, name) => {
  var tempLink = document.createElement("a");
  tempLink.setAttribute('href', URL.createObjectURL(blob));
  tempLink.setAttribute('download', name);
  tempLink.click();
  URL.revokeObjectURL(tempLink.href);

  // To prevent the screen from going up when the user clicks on the button
  return false;

};

const exportConfigs = () => {
  // Construct the yaml export of the config.
  var config_yaml = "plot_configs:\n"

  for(var config_name in window.metadata.plot_configs){
    var config = window.metadata.plot_configs[config_name];
    config_yaml += "  " + config_name + ":\n";
    for(var key in config){
      var value = config[key];
      if (key === 'xlim' || key === 'ylim')
        value = "[" + value + "]";
      config_yaml += "    " + key + ": " + value + "\n";
    }
  }

  // Download the resulting yaml file.
  var blob = new Blob([config_yaml], {type: 'text/yaml'});
  return downloadBlob(blob, 'config.yml');
};

const exportHTML = () => {
  var blob = new Blob(
    [document.documentElement.innerHTML],
    {type: 'text/html'}
  );
  return downloadBlob(blob, location.pathname.split("/").pop());
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

const isSolverAvailable = solver => data(solver).scatter.y.filter(value => !isNaN(value)).length > 0;

const isSmallScreen = () => window.screen.availHeight < 900;

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

const displayScatterElements = shouldBeVisible => {
  if (shouldBeVisible) {
    document.getElementById('scale-form-group').style.display = 'inline-block';
    document.getElementById('legend_container').style.display = 'block';
    document.getElementById('plot_legend').style.display = 'flex';
  } else {
    document.getElementById('scale-form-group').style.display = 'none';
    document.getElementById('legend_container').style.display = 'none';
    document.getElementById('plot_legend').style.display = 'none';
  }
};

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
  return _getScale(state().scale)
}

const _getScale = (scale) => {
  switch (scale) {
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
  let xaxisType = state().xaxis_type;

  const layout = {
    autosize: !isSmallScreen(),
    modebar: {
      orientation: 'v',
    },
    height: 700,
    showlegend: false,
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
      title: xaxisType === "Time" ? "Time [sec]": xaxisType,
      tickformat:  ["Time", "Tolerance"].includes(xaxisType) ? '.1e': '',
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
    title: `${state().objective}<br />Data: ${state().dataset}`,
    plot_bgcolor: '#e5ecf6',
  };

  if (isSmallScreen()) {
    layout.width = 900;
    layout.height = window.screen.availHeight - 200;
    layout.dragmode = false;
  }

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
    autosize: !isSmallScreen(),
    modebar: {
      orientation: 'v',
    },
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
    title: `${state().objective}<br />Data: ${state().dataset}`,
    plot_bgcolor: '#e5ecf6',
  };

  if (isSmallScreen()) {
    layout.width = 900;
    layout.height = window.screen.availHeight - 200;
    layout.dragmode = false;
  }

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
const getSolverFromEvent = event => {
  const target = event.currentTarget;

  for (let i = 0; i < target.children.length; i++) {
    if (target.children[i].className == 'solver') {
      return target.children[i].firstChild.nodeValue;
    }
  }

  return null;
};

const purgeHiddenSolvers = () => setState({hidden_solvers: []});

const hideAllSolversExcept = solver => {setState({hidden_solvers: getSolvers().filter(elmt => elmt !== solver)})};

const hideSolver = solver => isVisible(solver) ? setState({hidden_solvers: [...state().hidden_solvers, solver]}) : null;

const showSolver = solver => setState({hidden_solvers: state().hidden_solvers.filter(hidden => hidden !== solver)});

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
  // If all solvers except one are hidden, so double click should show all solvers
  if (state().hidden_solvers.length === getSolvers().length - 1) {
    purgeHiddenSolvers();

    return;
  }

  hideAllSolversExcept(solver);
};

/**
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * MANAGE PLOT LEGEND
 *
 * We don't use the plotly legend to keep control
 * on the size of the plot.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Creates the legend at the bottom of the plot.
 */
const makeLegend = () => {
  const legend = document.getElementById('plot_legend');

  legend.innerHTML = '';
  const solversDescription = window.metadata["solvers_description"];

  Object.keys(data().solvers).forEach(solver => {
    const color = data().solvers[solver].color;
    const symbolNumber = data().solvers[solver].marker;

    let legendItem = createLegendItem(solver, color, symbolNumber);

    // preserve compatibility with prev version
    if(solversDescription === null || solversDescription === undefined) {
      legend.appendChild(legendItem);
      return;
    }

    let payload = {
      description: solversDescription[solver],
    }

    legend.appendChild(
      createSolverDescription(legendItem, payload)
    );
  });
}

/**
 * Creates a legend item which contains the solver name,
 * the solver marker as an SVG and an horizontal bar with
 * the solver color.
 *
 * @param {String} solver
 * @param {String} color
 * @param {int} symbolNumber
 * @retuns {HTMLElement}
 */
const createLegendItem = (solver, color, symbolNumber) => {
  // Create item container
  const item = document.createElement('div');
  item.style.display = 'flex';
  item.style.flexDirection = 'row';
  item.style.alignItems = 'center';
  item.style.position = 'relative';
  item.style.cursor = 'pointer';
  item.className = 'bg-white py-1 px-4 shadow-sm mt-2 rounded'

  if (!isVisible(solver)) {
    item.style.opacity = 0.5;
  }

  // Click on a solver in the legend
  item.addEventListener('click', event => {
    solver = getSolverFromEvent(event);

    if (!getSolvers().includes(solver)) {
      console.error('An invalid solver has been handled during the click event.');

      return;
    }

    // In javascript we must simulate double click.
    // So first click is handled and kept in memory (window.clickedSolver)
    // during 500ms, if nothing else happen timeout will execute
    // single click function. However, if an other click happen during this
    // 500ms, it clears the timeout and execute the double click function.
    if (!window.clickedSolver) {
      window.clickedSolver = solver;

      // Timeout will execute single click function after 500ms
      window.clickedTimeout = setTimeout(() => {
        window.clickedSolver = null;

        handleSolverClick(solver);
      }, 500);
    } else if (window.clickedSolver === solver) {
      clearTimeout(window.clickedTimeout);
      window.clickedSolver = null;
      handleSolverDoubleClick(solver);
    }
  });

  // Create the HTML text node for the solver name in the legend
  const textContainer = document.createElement('div');
  textContainer.style.marginLeft = '0.5rem';
  textContainer.className = 'solver';
  textContainer.appendChild(document.createTextNode(solver));

  // Create the horizontal bar in the legend to represent the curve
  const hBar = document.createElement('div');
  hBar.style.height = '2px';
  hBar.style.width = '30px';
  hBar.style.backgroundColor = color;
  hBar.style.position = 'absolute';
  hBar.style.left = '1em';
  hBar.style.zIndex = 10;

  // Append elements to the legend item
  item.appendChild(createSymbol(symbolNumber, color));
  item.appendChild(hBar);
  item.appendChild(textContainer);

  return item;
}


function createSolverDescription(legendItem, { description }) {
  if (description === null || description === undefined || description === "")
    description = "No description provided";

  let descriptionContainer = document.createElement("div");
  descriptionContainer.setAttribute("class", "solver-description-container")

  descriptionContainer.innerHTML = `
  <div class="solver-description-content text-sm">
    <span class="solver-description-body">${description}</span>
  </div>
  `;

  descriptionContainer.prepend(legendItem);

  return descriptionContainer;
}


function updateXaxis(idXaxisTypeSelection) {
  let selection = document.getElementById(idXaxisTypeSelection);
  selection.innerHTML = "";

  let xaxisType = state()["xaxis_type"];
  let options = new Set(['Time']);

  // get solvers run for selected (dataset, objective, objective colum)
  // and select their unique sampling strategies
  let solvers = data()['solvers'];
  Object.values(solvers).forEach(solver => options.add(solver['sampling_strategy']));

  // create xaxis type options
  options.forEach(option => {
    element = document.createElement('option');
    element.setAttribute('value', option);
    element.innerText = option;

    selection.append(element);
  });

  // set selected value
  if (!options.has(xaxisType)){
    alert("Unknown xaxis type '"+ xaxisType + "'.");
  }
  selection.value = options.has(xaxisType) ? xaxisType : "Time";
}

/**
 * Create the same svg symbol as plotly.
 * Returns an <svg> HTML Element
 *
 * @param {int} symbolNumber
 * @param {String} color
 * @returns {HTMLElement}
 */
const createSymbol = (symbolNumber, color) => {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');

  svg.setAttribute('width', 30);
  svg.setAttribute('height', 30);
  svg.style.zIndex = 20;

  // createPathElement() come from the local file symbols.js
  svg.appendChild(createPathElement(symbolNumber, color));

  return svg;
}

/**
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * EVENT REGISTRATIONS
 *
 * Some events are also registered in result.html.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

document.getElementById('btn-plot-config').addEventListener('click', () => {
  const elmt = document.getElementById('mobile-plot-form');

  if (elmt.style.display === 'block') {
      elmt.style.display = 'none';

      return;
  }

  elmt.style.display = 'block';
});

document.getElementById('btn-main-menu').addEventListener('click', () => {
  const elmt = document.getElementById('mobile-menu');

  if (elmt.style.display === 'block') {
      elmt.style.display = 'none';

      return;
  }

  elmt.style.display = 'block';
});
