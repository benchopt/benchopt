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
  if (isChart('table')) {
    renderTable();
  } else {
    renderPlot();
  }
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
  'plot_kind': 'plot_kind',
  'scale': 'change_scale',
  'with_quantiles': 'change_shades',
  'suboptimal_curve': 'change_suboptimal',
  'relative_curve': 'change_relative',
  'hidden_curves': '',
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
  let div;
  let plot_with_legend_container = document.getElementById('plot_with_legend_container');
  let plot_container = document.getElementById('plot_container');

  hide(document.getElementById('table_container'));
  if (isChart('scatter')) {
    show(plot_container);
    show(plot_with_legend_container);
    div = plot_with_legend_container;
  } else {
    show(plot_container);
    hide(plot_with_legend_container);
    div = plot_container;
  }
  const data = getChartData();
  const layout = getLayout();

  Plotly.purge(plot_with_legend_container);
  Plotly.purge(plot_container);
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

  getPlotData().data.forEach(curveData => {
    // Add times for each convergent bar
    // Check if text is not 'Did not converge'
    curveText = curveData.text || ''
    if (curveText === '') {
      let nbTimes = curveData.y.length

      barData.push({
        type: 'scatter',
        x: new Array(nbTimes).fill(curveData.label),
        y: curveData.y,
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

  getPlotData().data.forEach(plotData => {
    plotData.x.forEach((label, i) => {
      boxplotData.push({
        y: plotData.y[i],
        name: label,
        type: 'box',
        line: {color: plotData.color},
        fillcolor: plotData.color,
        boxpoints: false
      });
    });
  });

  return boxplotData;
};


const getPlotData = () => {
  let dropdowns = getPlotDropdowns();
  let dropdown_values = dropdowns.map(dropdown => state()[dropdown]);
  let data_key = [state().plot_kind, ...dropdown_values].join('_');
  return window._plots[state().plot_kind][data_key];
}


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
  getPlotData().data.forEach(curveData => {
    min_y = Math.min(min_y, ...curveData.y);
  });
  min_y -=  1e-10; // to avoid zeros in log scale

  getPlotData().data.forEach(curveData => {
    label = curveData.label;
    y = curveData.y;
    if ("x_low" in curveData && "x_high" in curveData && state().with_quantiles) {
      x_low = curveData.x_low;
      x_high = curveData.x_high;
    }
    if (state().suboptimal_curve) {
      y = y.map(value => value - min_y);
      if ("x_low" in curveData && "x_high" in curveData && state().with_quantiles) {
        x_low = x_low.map(value => value - min_y);
        x_high = x_high.map(value => value - min_y);
      }
    }
    if (state().relative_curve) {
      y = y.map(value => value / (y[0] - min_y));
      if ("x_low" in curveData && "x_high" in curveData && state().with_quantiles) {
        x_low = x_low.map(value => value / (y[0] - min_y));
        x_high = x_high.map(value => value / (y[0] - min_y));
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

    if ("x_low" in curveData && "x_high" in curveData && state().with_quantiles) {
      curves.push({
        type: 'scatter',
        mode: 'lines',
        legend: false,
        line: {
          width: 0,
          color: curveData.color,
        },
        legendgroup: label,
        hovertemplate: '(%{x:.1e},%{y:.1e}) <extra></extra>',
        visible: isVisible(label) ? true : 'legendonly',
        x: x_low,
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
        x: x_high,
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

const DEFAULT_CONFIG_OPTIONS = [
  "plot_kind",
  "hidden_curves",
  "scale",
  "with_quantiles",
  "suboptimal_curve",
  "relative_curve",
];

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
    // const lims = ['xlim', 'ylim', 'hidden_curves']
    const lims = ['hidden_curves']
    let kind = state().plot_kind;
    if ("plot_kind" in config) {
      kind = config["plot_kind"];
    }
    for(let key in config){
      const value = config[key];
      if (key in config_mapping) {
        if (config_mapping[key] !== '') {
          div_key = config_mapping[key];
          document.getElementById(div_key).value = value;
        }
      }
      else {
        // Custom parameters which should be related to the current kind
        // and the div prefix is 'change_{kind}_'. Ignore otherwise with
        // a warning in the console.
        if (!key.startsWith(kind)) {
          key = kind + "_" + key;
        }
        div_key = "change_" + key;
        try {
          document.getElementById(div_key).value = value;
        } catch (error) {
          // Element not found, ignore
          console.warn("Unknown config parameter: '" + key + "'");
        }
      }
      update[key] = value;
    }

    setState(update);

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
  dropdowns = getPlotDropdowns();
  for(let key of dropdowns) {
    config[key] = state()[key];
  }
  for (let option of DEFAULT_CONFIG_OPTIONS) {
    config[option] = state()[option];
  }

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
  renderPlotDropdowns();
}

/**
 * Render Scale selector
 */
const renderScaleSelector = () => {
  if (isChart(['bar_chart', 'table'])) {
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

const renderPlotDropdowns = () => {
  hide(document.querySelectorAll(`[id$='-custom-params-container']`));
  show(document.querySelectorAll(`#${state().plot_kind}-custom-params-container`), 'block');
  // Hide dropdowns with only one option
  for (let dropdown of document.getElementsByTagName('select')) {
    if (dropdown.options.length <= 1) {
      hide(dropdown.parentElement.parentElement);
    }
  }

}

const mapSelectorsToState = () => {
  const currentState = state();
  document.getElementById('plot_kind').value = currentState.plot_kind;
  document.getElementById('change_scale').value = currentState.scale;
  document.getElementById('change_shades').checked = currentState.with_quantiles;
  document.getElementById('change_suboptimal').checked = currentState.suboptimal_curve;
  document.getElementById('change_relative').checked = currentState.relative_curve;
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
  let curves = getPlotData().data.reduce(
    (map, obj) => {map[obj.label] = obj; return map}, {}
  );
  return curve ? curves[curve]: curves;
}

const getPlotDropdowns = () => {
  let kind = state().plot_kind;
  let params = [];
  Object.keys(state()).forEach(key => {
    if (key.startsWith(kind)) {
      params.push(key);
    }
  });
  return params;
}

const getCurves = () => Object.keys(data());

const isChart = chart => {
  if (typeof chart === 'string' || chart instanceof String) {
    chart = [chart]
  }

  let plot_kind = state().plot_kind;
  if (!["bar_chart", "boxplot"].includes(plot_kind)) {
    let custom_data = getPlotData();
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

const getMedian = (arr) => {
  const sorted = [...arr].sort((a, b) => a - b);
  let median = null;
  if (sorted.length > 0) {
    const mid = Math.floor(sorted.length / 2);
    median = (sorted.length % 2 === 1) ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return median;
}

const barDataToArrays = () => {
  const colors = [], texts = [], x = [], y = [];

  getPlotData().data.forEach(plotData => {
    x.push(plotData.label);
    y.push(getMedian(plotData.y));
    const plotText = plotData.text || '';
    colors.push(plotText === '' ? plotData.color : NON_CONVERGENT_COLOR);
    texts.push(plotText);
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
  let data = getPlotData();
  const layout = {
    autosize: true,
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
      ticktext: Array(data.data.map(d => d.label)),
    },
    showlegend: false,
    title: data["title"],
    plot_bgcolor: '#e5ecf6',
  };

  if (isSmallScreen()) {
    layout.dragmode = false;
  }

  // TODO what does this do ??
  if (!isAvailable()) {
    layout.annotations = [{
      xref: 'paper',
      yref: 'paper',
      x: 0.5,
      y: 0.5,
      text: 'Not available',
      showlegend: false,
      showarrow: false,
      font: {
        color: 'black',
        size: 32,
      }
    }];
  }
  return layout;
};

const getBoxplotChartLayout = () => {
  const plot_info = getPlotData()
  const layout = {
    autosize: true,
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
    layout.dragmode = false;
  }

  return layout;
};


const getScatterChartLayout = () => {
  let customData = getPlotData();

  const layout = {
    autosize: true,  // Let Plotly handle sizing; CSS controls aspect ratio and min-height
    modebar: {
      orientation: 'v',
    },
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
const show = (HTMLElements, style = '') => {
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
 * MANAGE TABLE RENDERING
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

// Global state for precision
let tableFloatPrecision = 4;

const valueToFixed = (value) => {
  if (typeof value === 'number' && !Number.isInteger(value)) {
    return value.toFixed(tableFloatPrecision);
  }
  return value;
}

function renderTable() {

  let table_container = document.getElementById('table_container');
  hide(document.getElementById('plot_container'));
  show(table_container);

  table_container.innerHTML = "";

  const plotData = getPlotData();
  if (!plotData || !plotData.columns || !plotData.data) {
    table_container.innerHTML = `<div >No data available</div>`;
    return;
  }

  const { columns, data: rows } = plotData;

  // Card Wrapper
  const card = document.createElement("div");
  card.className = "w-full bg-white overflow-hidden border border-gray-200 mx-auto";

  // Table Element
  const table = document.createElement("table");
  table.className = "w-full border-collapse text-left";

  // Header
  const thead = document.createElement("thead");
  thead.className = "bg-gray-50";
  const trHead = document.createElement("tr");

  columns.forEach(headerText => {
    const th = document.createElement("th");
    th.innerText = headerText;
    th.className = "px-4 py-4 text-xs font-bold uppercase tracking-wider border-b border-gray-200";
    trHead.appendChild(th);
  });
  thead.appendChild(trHead);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");

  rows.forEach((rowData, index) => {
    const tr = document.createElement("tr");
    tr.className = "bg-white transition-colors duration-150 ease-in-out hover:bg-gray-50";

    tr.onmouseenter = () => tr.style.backgroundColor = "#f9fafb";
    tr.onmouseleave = () => tr.style.backgroundColor = "#fff";

    rowData.forEach(cellValue => {
      const td = document.createElement("td");
      td.innerHTML = valueToFixed(cellValue);

      let cellClasses = "px-4 py-4 text-sm text-gray-700";
      if (index !== rows.length - 1) {
        cellClasses += " border-b border-gray-100";
      }
      td.className = cellClasses;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  // Footer with Precision Controls & Export
  const footerWrapper = document.createElement("div");
  footerWrapper.className = "w-full";

  const footer = document.createElement("div");
  footer.className = "flex justify-between items-center p-4";

  // Precision Controls (Left)
  const precisionContainer = document.createElement("div");
  precisionContainer.className = "flex items-center gap-2 text-sm text-gray-700";

  const createPrecBtn = (text) => {
    const btn = document.createElement("button");
    btn.innerText = text;
    btn.className = "px-3 py-1 border border-gray-300 bg-white rounded cursor-pointer hover:bg-gray-100";
    return btn;
  };

  const btnDec = createPrecBtn("-");
  const btnInc = createPrecBtn("+");
  const labelPrec = document.createElement("span");
  labelPrec.innerText = `Float Precision: ${tableFloatPrecision}`;
  labelPrec.className = "mx-2 px-4";

  btnDec.onclick = () => {
    if (tableFloatPrecision > 0) {
      tableFloatPrecision--;
      renderTable();
    }
  };

  btnInc.onclick = () => {
    tableFloatPrecision++;
    renderTable();
  };

  precisionContainer.appendChild(btnDec);
  precisionContainer.appendChild(labelPrec);
  precisionContainer.appendChild(btnInc);

  // Export Button (Right)
  const exportButton = document.createElement("button");
  exportButton.id = "table-export";
  exportButton.innerText = "Export LaTeX";
  exportButton.className = "inline-flex items-center px-4 py-2 space-x-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500";

  exportButton.addEventListener('click', () => {
    exportTable();
  });

  table.appendChild(tbody);
  card.appendChild(table);
  table_container.appendChild(card);

  footer.appendChild(precisionContainer);
  footer.appendChild(exportButton);
  footerWrapper.appendChild(footer);
  table_container.appendChild(footerWrapper);
}


async function exportTable() {
  const button = document.getElementById("table-export");
  const defaultText = button.innerHTML;
  button.innerHTML = "Copying";

  const plotData = getPlotData();

  let value = "\\begin{tabular}{l";
  value += "c".repeat(plotData.columns.length);
  value += "}\n";
  value += "\\hline\n";

  value += plotData.columns[0].replace('_', '\\_');
  plotData.columns.slice(1).forEach(metric => value += ` & ${metric.replace('_', '\\_')}`);

  value += " \\\\\n";
  value += "\\hline\n";

  plotData.data.forEach(rowData => {
    value += valueToFixed(rowData[0]).toString().replace('_', '\\_');
    rowData.slice(1).forEach(cell => {
      value += ` & ${valueToFixed(cell).toString().replace('_', '\\_')}`;
    });
    value += " \\\\\n";
  });

  value += "\\hline\n";
  value += "\\end{tabular}";

  try {
    await navigator.clipboard.writeText(value);
    button.innerHTML = "Copied in clipboard!";
    setTimeout(() => button.innerHTML = defaultText, 2500);
  } catch (err) {
    button.innerHTML = "Error!";
    setTimeout(() => button.innerHTML = defaultText, 2500);
  }
}

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
    const curve_data = data(curve);
    const color = curve_data.color;
    const symbolNumber = curve_data.marker;

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
    if (payload !== undefined) {
      legend.appendChild(payload);
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
    return legendItem;

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
