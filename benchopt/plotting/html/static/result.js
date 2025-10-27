const NON_CONVERGENT_COLOR = 'rgba(0.8627, 0.8627, 0.8627)'

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * STATE MANAGEMENT
 *
 * The state represent the plot state. It's an object
 * that is stored into the window._state variable.
 *
 * Do not manually update window._state,
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
 *   - hidden_curves (array)
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Update the state and create/update the plot
 * using the new state.
 *
 * @param {Object} partialState
 */
const setState = (partialState) => {
  window._state = {...state(), ...partialState};

  renderSidebar();
  renderPlot();
  renderLegend();
}

/**
 * Retrieve the state object from window._state
 *
 * @returns Object
 */
const state = (key = undefined) => {
  if (key) {
    return window._state[key];
  }

  return window._state;
}

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
const renderPlot = () => {
  const div = document.getElementById('unique_plot');
  const data = getChartData();
  const layout = getLayout();

  Plotly.react(div, data, layout);
};

/**
 * Returns data formatted for Plotly.
 *
 * @returns {Array|*[]}
 */
const getChartData = () => {
  if (isChart('scatter')) {
    return getScatterData();
  } else if (isChart('bar_chart')) {
    return getBarData();
  } else if (isChart('boxplot')) {
    return getBoxplotData();
  }
  throw new Error("Unknown plot kind : " + state().plot_kind);
}

/**
 * Returns layout object according to the plot kind.
 *
 * @returns Object
 */
const getLayout = () => {
  if (isChart('scatter')) {
    return getScatterChartLayout();
  } else if (isChart('bar_chart')) {
    return getBarChartLayout();
  } else if (isChart('boxplot')) {
    return getBoxplotChartLayout();
  }
  throw new Error("Unknown plot kind : " + state().plot_kind);
}

/**
 * Gives the data formatted for plotlyJS bar chart.
 *
 * @returns {array}
 */
const getBarData = () => {
  // TODO fix with other PR
  // if (!isAvailable()) return [{type:'bar'}];

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

  getCustomPlotData().data.forEach(curveData => {
    // Add times for each convergent bar
    // Check if text is not 'Did not converge'
    if (curveData.text === '') {
      let nbTimes = curveData.times.length

      barData.push({
        type: 'scatter',
        x: new Array(nbTimes).fill(curveData.label),
        y: curveData.times,
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


const getBoxplotData = () => {
  const boxplotData = [];

  getCustomPlotData().data.forEach(dataset => {
    // dataset.x is like ["A", "B", "C"]
    // dataset.y is like [[vals for A], [vals for B], [vals for C]]
    dataset.x.forEach((label, i) => {
      boxplotData.push({
        y: dataset.y[i],
        name: label,
        type: 'box',
        line: {color: dataset.color},
        fillcolor: dataset.color,
        boxpoints: false
      });
    });
  });

  return boxplotData;
};


const getCustomPlotData = () => {
  let params = getParams();
  let param_values = params.map(param => state()[param]);
  let data_key = [state().plot_kind, ...param_values].join('_');
  return window._custom_plots[state().plot_kind][data_key];
}

// TODO add other types of custom plots
/**
 * Gives the data formatted for plotlyJS scatter chart.
 *
 * @returns {array}
 */
const getScatterData = () => {
  // create a list of object to plot in plotly
  const curves = [];

  // get the minimum y value over all curves
  let min_y = Infinity;
  getCustomPlotData().data.forEach(curveData => {
    min_y = Math.min(min_y, ...curveData.y);
  });
  min_y -=  1e-10; // to avoid zeros in log scale

  getCustomPlotData().data.forEach(curveData => {
    label = curveData.label;
    y = curveData.y;
    if ("q1" in curveData && "q9" in curveData && state().with_quantiles) {
      q1 = curveData.q1;
      q9 = curveData.q9;
    }
    if (state().suboptimal_curve) {
      y = y.map(value => value - min_y);
      if ("q1" in curveData && "q9" in curveData && state().with_quantiles) {
        q1 = q1.map(value => value - min_y);
        q9 = q9.map(value => value - min_y);
      }
    }
    if (state().relative_curve) {
      y = y.map(value => value / (y[0] - min_y));
      if ("q1" in curveData && "q9" in curveData && state().with_quantiles) {
        q1 = q1.map(value => value / (y[0] - min_y));
        q9 = q9.map(value => value / (y[0] - min_y));
      }
    }
    curves.push({
      type: 'scatter',
      name: label,
      mode: 'lines+markers',
      line: {
        color: curveData.color,
      },
      marker: {
        symbol: curveData.marker,
        size: 10,
        color: curveData.color,
      },
      legendgroup: label,
      hovertemplate: label + ' <br> (%{x:.1e},%{y:.1e}) <extra></extra>',
      visible: isVisible(label) ? true : 'legendonly',
      x: curveData.x,
      y: y,
    });

    if ("q1" in curveData && "q9" in curveData && state().with_quantiles) {
      curves.push({
        type: 'scatter',
        mode: 'lines',
        showlegend: false,
        line: {
          width: 0,
          color: curveData.color,
        },
        legendgroup: label,
        hovertemplate: '(%{x:.1e},%{y:.1e}) <extra></extra>',
        visible: isVisible(label) ? true : 'legendonly',
        x: q1,
        y: y,
      }, {
        type: 'scatter',
        mode: 'lines',
        showlegend: false,
        fill: 'tonextx',
        line: {
          width: 0,
          color: curveData.color,
        },
        legendgroup: label,
        hovertemplate: '(%{x:.1e},%{y:.1e}) <extra></extra>',
        visible: isVisible(label) ? true : 'legendonly',
        x: q9,
        y: y,
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

const get_lim_config = (lim, ax) => {
  if(getScale()[ax + 'axis'] == 'log'){
    lim = [Math.pow(10, lim[0]), Math.pow(10, lim[1])]
  };
  return lim;
};

const setConfig = (config_item) => {
  if (!config_item) {
    return;
  }

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
    const lims = ['xlim', 'ylim', 'hidden_curves']
    for(let key in config_mapping){
      if (key in config){
        const value = config[key];
        document.getElementById(config_mapping[key]).value = value;
        if (key === "kind"){
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
      if (config.hasOwnProperty(lim) & (config[lim] != null)) {
        layout[ax +'axis.range'] = get_lim_plotly(config[lim], ax);
      }
    }

    // update the plot
    renderPlot();
  }
};

const saveView = () => {
  let n_configs = Object.keys(window.metadata.plot_configs).length;

  let config_name = prompt("Config Name", "Config " + n_configs);
  if(config_name === null || config_name === ""){
    return;
  }

  // Retrieve the dropdown menu selected values
  let config = {};
  for(let key in config_mapping) {
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
 * LEFT SIDEBAR MANAGEMENT
 *
 * Functions that control the left sidebar.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Render sidebar
 */
const renderSidebar = () => {
  renderScaleSelector();
  renderWithQuantilesToggle();
  renderSuboptimalRelativeToggle();
  mapSelectorsToState();
  renderCustomParams();
}

/**
 * Render Scale selector
 */
const renderScaleSelector = () => {
  if (isChart('bar_chart')) {
    hide(document.querySelectorAll("#scale-form-group"));
  } else {
    show(document.querySelectorAll("#scale-form-group"), 'block');
  }

  if (isChart('boxplot')) {
    hide(document.querySelectorAll(".other_plot_option"));
    show(document.querySelectorAll(".boxplot_option"));
  } else {
    hide(document.querySelectorAll(".boxplot_option"));
    show(document.querySelectorAll(".other_plot_option"));
  }
};

/**
 * Render WithQuantile toggle
 */
const renderWithQuantilesToggle = () => {
  if (isChart('scatter')) {
    show(document.querySelectorAll("#change-shades-form-group"), 'flex');
  } else {
    hide(document.querySelectorAll("#change-shades-form-group"));
  }
};

const renderSuboptimalRelativeToggle = () => {
  if (isChart('scatter')) {
    show(document.querySelectorAll("#change-relative-suboptimal-form-group"), 'flex');
  } else {
    hide(document.querySelectorAll("#change-relative-suboptimal-form-group"));
  }
};


const renderCustomParams = () => {
  hide(document.querySelectorAll(`[id$='-custom-params-container']`));
  show(document.querySelectorAll(`#${state().plot_kind}-custom-params-container`), 'block');

}


const mapSelectorsToState = () => {
  const currentState = state();
  document.getElementById('plot_kind').value = currentState.plot_kind;
  document.getElementById('change_scaling').value = currentState.scale;
  document.getElementById('change_shades').checked = currentState.with_quantiles;
};

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * TOOLS
 *
 * Various functions to simplify life.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

// Get the data for a given plot state, indexed by curve names.
const data = (curve = null) => {
  let curves;
  const kind = state().plot_kind;
  if (kind === 'bar_chart' || kind === 'boxplot') {
      const info = state();
      curves = window._data[info.dataset][info.objective][info.objective_column].solvers;
    }
    else{
      curves = getCustomPlotData().data.reduce(
        (map, obj) => {map[obj.label] = obj; return map}, {}
      );
    }
    return curve ? curves[curve]: curves;
}

const getParams = () => {
  let kind = state().plot_kind;
  let params = [];
  Object.keys(state()).forEach(key => {
    if (key.includes(kind)) {
      params.push(key);
    }
  });
  return params;
}

const getCurves = () => Object.keys(data());

const isCustomPlot = () => {
  let non_custom_kinds = ['bar_chart', 'boxplot'];
  return !non_custom_kinds.includes(state().plot_kind);
}

const isChart = chart => {
  if (typeof chart === 'string' || chart instanceof String) {
    chart = [chart]
  }

  let plot_kind = state().plot_kind;
  if (!["bar_chart", "boxplot"].includes(plot_kind)) {
    let custom_data = getCustomPlotData();
    plot_kind = custom_data.type;
  }
  return chart.includes(plot_kind);
}

const isVisible = curve => !state().hidden_curves.includes(curve);

const isSolverAvailable = solver => data(solver) !== null;

const isSmallScreen = () => window.screen.availHeight < 900;

/**
 * Check for each solver
 * if data is available
 *
 * @returns {Boolean}
 */
const isAvailable = () => {
  let isNotAvailable = true;

  getCurves().forEach(solver => {
    if (isSolverAvailable(solver)) {
      isNotAvailable = false;
    }
  });

  return !isNotAvailable;
}

const barDataToArrays = () => {
  const colors = [], texts = [], x = [], y = [];

  getCustomPlotData().data.forEach(plotData => {
    x.push(plotData.label);
    y.push(plotData.y);
    colors.push(plotData.text === '' ? plotData.color : NON_CONVERGENT_COLOR);
    texts.push(plotData.text);
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
    case 'log': // used for boxplot
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

const getBarChartLayout = () => {
  let data = getCustomPlotData();
  const layout = {
    autosize: !isSmallScreen(),
    modebar: {
      orientation: 'v',
    },
    yaxis: {
      type: 'log',
      title: data["ylabel"],
      tickformat: '.1e',
      gridcolor: '#ffffff',
    },
    xaxis: {
      tickangle: -60,
      ticktext: getSolvers(),
    },
    showlegend: false,
    title: data["title"],
    plot_bgcolor: '#e5ecf6',
  };

  if (isSmallScreen()) {
    layout.width = 900;
    layout.height = window.screen.availHeight - 200;
    layout.dragmode = false;
  }

  // TODO: fix with other PR
  // if (!isAvailable()) {
  //   layout.annotations = [{
  //     xref: 'paper',
  //     yref: 'paper',
  //     x: 0.5,
  //     y: 0.5,
  //     text: 'Not available',
  //     showarrow: false,
  //     font: {
  //       color: 'black',
  //       size: 32,
  //     }
  //   }];
  // }

  return layout;
};

const getBoxplotChartLayout = () => {
  plot_info = getCustomPlotData()
  const layout = {
    autosize: !isSmallScreen(),
    modebar: {
      orientation: 'v',
    },
    yaxis: {
      type: getScale().yaxis,
      title: plot_info["ylabel"],
      tickformat: '.1e',
      gridcolor: '#ffffff',
    },
    xaxis: {
      tickangle: (typeof plot_info.data[0].x[0] === "string") ? -60 : 0,
    },
    showlegend: false,
    title: plot_info["title"],
    plot_bgcolor: '#e5ecf6',
  };

  if (isSmallScreen()) {
    layout.width = 900;
    layout.height = window.screen.availHeight - 200;
    layout.dragmode = false;
  }

  return layout;
};


const getScatterChartLayout = () => {
  let customData = getCustomPlotData();

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
      title: customData.xlabel,
      tickformat: '.1e', // TODO adapt if xaxis is not numeric
      tickangle: -45,
      gridcolor: '#ffffff',
      zeroline : false,
    },
    yaxis: {
      type: getScale().yaxis,
      title: customData.ylabel,
      tickformat: '.1e',
      gridcolor: '#ffffff',
      zeroline : false,
    },
    title: `${customData.title}`,
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


/**
 * Returns true if sampling strategy 'Iteration' value is in data
 *
 * @returns {boolean}
 */
const isIterationSamplingStrategy = () => {
  let options = new Set(['Time']);
  // get solvers run for selected (dataset, objective, objective colum)
  // and select their unique sampling strategies
  getCurves().forEach(solver => options.add(data(solver).sampling_strategy));

  return options.has('Iteration')
};

/**
 * Hide an HTML element by applying a none value to its display style property.
 *
 * @param HTMLElements
 */
const hide = HTMLElements => {
  if (HTMLElements instanceof Element) {
    HTMLElements = [HTMLElements]
  }

  HTMLElements.forEach(h => h.style.display = 'none');
};

/**
 * Show an HTML element by applying an initial value to its display style property.
 *
 * @param HTMLElements
 * @param style
 */
const show = (HTMLElements, style = 'initial') => {
  if (HTMLElements instanceof Element) {
    HTMLElements = [HTMLElements]
  }

  HTMLElements.forEach(h => h.style.display = style);
};

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * MANAGE HIDDEN CURVES
 *
 * Functions to hide/display and memorize curves which
 * were clicked by user on the legend of the plot.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */
const getCurveFromEvent = event => {
  const target = event.currentTarget;

  for (let i = 0; i < target.children.length; i++) {
    if (target.children[i].className === 'curve') {
      return target.children[i].firstChild.nodeValue;
    }
  }

  return null;
};

const purgeHiddenCurves = () => setState({hidden_curves: []});

const hideAllCurvesExcept = curve => {setState({hidden_curves: getCurves().filter(elmt => elmt !== curve)})};

const hideCurve = curve => isVisible(curve) ? setState({hidden_curves: [...state().hidden_curves, curve]}) : null;

const showCurve = curve => setState({hidden_curves: state().hidden_curves.filter(hidden => hidden !== curve)});

/**
 * Add or remove curve name from the list of hidden curves.
 *
 * @param {String} curve
 * @returns {void}
 */
const handleCurveClick = curve => {
  if (!isVisible(curve)) {
    showCurve(curve);

    return;
  }

  hideCurve(curve);
};

const handleCurveDoubleClick = curve => {
  // If all curves except one are hidden, so double click should show all curves
  if (state().hidden_curves.length === getCurves().length - 1) {
    purgeHiddenCurves();

    return;
  }

  hideAllCurvesExcept(curve);
};

/*
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
const renderLegend = () => {
  const legendContainer = document.getElementById('legend_container')
  if (!isChart('scatter')) {
    hide(legendContainer);
    return;
  } else {
    show(legendContainer);
  }

  const legend = document.getElementById('plot_legend');

  legend.innerHTML = '';
  const curvesDescription = window.metadata["solvers_description"];

  getCurves().forEach(curve => {
    const color = data(curve).color;
    const symbolNumber = data(curve).marker;

    let legendItem = createLegendItem(curve, color, symbolNumber);

    // preserve compatibility with prev version
    if(curvesDescription === null || curvesDescription === undefined) {
      legend.appendChild(legendItem);
      return;
    }

    let payload = createSolverDescription(
      legendItem, {
        description: curvesDescription[curve],
      }
    );
    if (payload === undefined) {
      legend.appendChild(legendItem);
    }
  });
}

/**
 * Creates a legend item which contains the curve name,
 * the curve marker as an SVG and an horizontal bar with
 * the curve color.
 *
 * @param {String} curve
 * @param {String} color
 * @param {int} symbolNumber
 * @returns {HTMLElement}
 */
const createLegendItem = (curve, color, symbolNumber) => {
  // Create item container
  const item = document.createElement('div');
  item.style.display = 'flex';
  item.style.flexDirection = 'row';
  item.style.alignItems = 'center';
  item.style.position = 'relative';
  item.style.cursor = 'pointer';
  item.className = 'bg-white py-1 px-4 shadow-sm mt-2 rounded'

  if (!isVisible(curve)) {
    item.style.opacity = 0.5;
  }

  // Click on a curve in the legend
  item.addEventListener('click', event => {
    curve = getCurveFromEvent(event);

    if (!getCurves().includes(curve)) {
      console.error('An invalid curve has been handled during the click event.');

      return;
    }

    // In javascript we must simulate double click.
    // So first click is handled and kept in memory (window.clickedCurve)
    // during 500ms, if nothing else happen timeout will execute
    // single click function. However, if an other click happen during this
    // 500ms, it clears the timeout and execute the double click function.
    if (!window.clickedCurve) {
      window.clickedCurve = curve;

      // Timeout will execute single click function after 500ms
      window.clickedTimeout = setTimeout(() => {
        window.clickedCurve = null;

        handleCurveClick(curve);
      }, 500);
    } else if (window.clickedCurve === curve) {
      clearTimeout(window.clickedTimeout);
      window.clickedCurve = null;
      handleCurveDoubleClick(curve);
    }
  });

  // Create the HTML text node for the curve name in the legend
  const textContainer = document.createElement('div');
  textContainer.style.marginLeft = '0.5rem';
  textContainer.className = 'curve';
  textContainer.appendChild(document.createTextNode(curve));

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
    return;

  let descriptionContainer = document.createElement("div");
  descriptionContainer.setAttribute("class", "curve-description-container")

  descriptionContainer.innerHTML = `
  <div class="curve-description-content text-sm">
    <span class="curve-description-body">${description}</span>
  </div>
  `;

  descriptionContainer.prepend(legendItem);

  return descriptionContainer;
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
