const UNDEFINED_COLOR = 'rgba(0.8627, 0.8627, 0.8627)'

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * SHORT LABEL HELPERS
 *
 * When short_labels are enabled (via the benchmark config),
 * each curve trace carries a `short_label` (display) and a
 * `full_label` (identity / tooltip).  These helpers centralise
 * the lookup so all rendering code can call them consistently.
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

/**
 * Return the display label for a curve (short if available).
 *
 * @param {String} full_name  The curve's identity key (full solver name).
 * @returns {String}
 */
const getDisplayLabel = (full_name) => {
  const curveData = data(full_name);
  if (curveData && curveData.short_label) return curveData.short_label;
  return full_name;
};

/**
 * Return the display label for a dataset / objective name.
 * Falls back to the full name when no short-label map is available.
 *
 * @param {String} full_name
 * @param {'datasets'|'objectives'|'solvers'} kind
 * @returns {String}
 */
const getShortLabel = (full_name, kind = 'solvers') => {
  const map = (window._short_labels || {})[kind] || {};
  return map[full_name] || full_name;
};

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
  const plotKindChanged = (
    "plot_kind" in partialState && partialState.plot_kind !== window._state?.plot_kind
  );

  window._state = {...state(), ...partialState};

  // When changing chart type, apply the default scale defined by the plot data
  if (plotKindChanged) {
    const plotData = getPlotData();
    if (plotData && "scale" in plotData) {
      window._state.scale = plotData.scale;
    }
  }

  renderSidebar();

  /**
   * Hide all containers for the different plots
   */
  ["table", "image", "plot", "plot_with_legend", "legend"].forEach(key => {
    let container = document.getElementById(`${key}_container`);
    hide(container);
  });

  if  (isChart('table')) {
    renderTable();
  } else {
    // Pending table-view settings only apply to tables; drop them otherwise.
    tablePendingView = null;
    if (isChart('image')) {
      renderImages();
    } else {
      renderPlot();
    }
  }

};

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

  // Show and purge the container
  let plot_container = document.getElementById('plot_container');
  let plot_with_legend_container = document.getElementById('plot_with_legend_container');
  Plotly.purge(plot_with_legend_container);
  Plotly.purge(plot_container);
  show(plot_container);

  let div = plot_container;
  if (isChart('scatter')) {
    show(plot_with_legend_container);
    div = plot_with_legend_container;
    renderLegend();
  }

  // Render the plot with PlotlyJS
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
  if (!isAvailable()) return [{type:'bar'}];

  const {x, y, color, texts} = barDataToArrays();

  // Add bars
  const barData = [{
    type: 'bar',
    x: x,
    y: y,
    marker: {
      color: color,
    },
    text: texts,
    textposition: 'inside',
    insidetextanchor: 'middle',
    textangle: '-90',
  }];

  getPlotData().data.forEach(curveData => {
    // Add times for each convergent bar if mulitple values
    let nbTimes = curveData.y.length;
    if (nbTimes > 1) {
      barData.push({
        type: 'scatter',
        x: new Array(nbTimes).fill(
          state().short_labels
            ? (curveData.short_label || curveData.label)
            : curveData.label
        ),
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
      // When X_axis == "Solver" each x entry is a solver name; use short label.
      const displayX = (typeof label === 'string')
        ? (state().short_labels ? (getShortLabel(label, 'solvers') || label) : label)
        : label;
      boxplotData.push({
        y: plotData.y[i],
        name: displayX,
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
    const displayLabel = state().short_labels ? (curveData.short_label || label) : label;
    y = curveData.y;
    if ("y_low" in curveData && "y_high" in curveData && state().with_quantiles) {
      y_low = curveData.y_low;
      y_high = curveData.y_high;
    }
    else if ("x_low" in curveData && "x_high" in curveData && state().with_quantiles) {
      x_low = curveData.x_low;
      x_high = curveData.x_high;
    }
    if (state().suboptimal_curve) {
      y = y.map(value => value - min_y);
    }
    if (state().relative_curve) {
      y = y.map(value => value / (y[0] - min_y));
    }
    curves.push({
      type: 'scatter',
      name: displayLabel,
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
      hovertemplate: displayLabel + ' <br> (%{x:.3e},%{y:.3e}) <extra></extra>',
      visible: isVisible(label) ? true : 'legendonly',
      x: curveData.x,
      y: y,
    });


    if ("y_low" in curveData && "y_high" in curveData && state().with_quantiles) {
      curves.push({
        type: 'scatter',
        mode: 'lines',
        legend: false,
        line: {
          width: 0,
          color: curveData.color,
        },
        legendgroup: label,
        hovertemplate: '(%{x:.3e},%{y:.3e}) <extra></extra>',
        visible: isVisible(label) ? true : 'legendonly',
        x: curveData.x,
        y: y_low,
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
        hovertemplate: '(%{x:.3e},%{y:.3e}) <extra></extra>',
        visible: isVisible(label) ? true : 'legendonly',
        x: curveData.x,
        y: y_high,
      });
    }
    else if ("x_low" in curveData && "x_high" in curveData && state().with_quantiles) {
      curves.push({
        type: 'scatter',
        mode: 'lines',
        legend: false,
        line: {
          width: 0,
          color: curveData.color,
        },
        legendgroup: label,
        hovertemplate: '(%{x:.3e},%{y:.3e}) <extra></extra>',
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
        hovertemplate: '(%{x:.3e},%{y:.3e}) <extra></extra>',
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
    // Table settings are applied by renderTable, not through the state.
    tablePendingView = ('table_order' in config || 'table_hidden_columns' in config)
      ? {order: config.table_order ?? null, hidden: config.table_hidden_columns ?? []}
      : null;
    for(let key in config){
      if (key === 'table_order' || key === 'table_hidden_columns') {
        continue;
      }
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

  // Persist the table order and hidden columns when viewing a table.
  if (isChart('table')) {
    const order = getTableOrder();
    if (order) {
      config.table_order = order;
    }
    config.table_hidden_columns = [...tableHiddenColumns];
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
      else if (value !== null && typeof value === 'object')
        // Arrays/objects (e.g. table_order, hidden columns): JSON is valid YAML.
        value = JSON.stringify(value);
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

const escapeHTML = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/**
 * Inline SVG "info" icon (class `param-icon`) carrying a trace `description`
 * in `data-desc`. Hover is wired through event delegation (see below) so the
 * icon works both in the legend and in Grid.js tables, which re-render their
 * cells on every sort/search. Returning an SVG (not a text glyph) keeps the
 * icon out of `innerText`, so the LaTeX table export is unaffected.
 */
const descIconHTML = (text) =>
  `<svg class="param-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"` +
  ` stroke-width="2" stroke-linecap="round" stroke-linejoin="round"` +
  ` data-desc="${escapeHTML(text)}">` +
  `<circle cx="12" cy="12" r="10"></circle>` +
  `<line x1="12" y1="16" x2="12" y2="12"></line>` +
  `<line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;

/** Show params tooltip for a dataset/objective selector icon. */
const showEntityParamsTooltip = (event, paramType, stateKey) => {
  const sl = window._short_labels || {};
  const lookup = paramType === 'dataset'
    ? (sl.dataset_descriptions || {}) : (sl.objective_descriptions || {});
  const currentValue = state()[stateKey];
  showDescTooltip(event, currentValue ? (lookup[currentValue] || '') : '');
};

/** Show a trace `description` tooltip. The description is already HTML. */
const showDescTooltip = (event, html) => {
  if (!html) return;
  const tip = document.getElementById('params-tooltip');
  tip.innerHTML = html;
  tip.style.display = 'block';
  _moveParamsTooltip(event);
};

/** Hide the shared params tooltip. */
const hideParamsTooltip = () => {
  document.getElementById('params-tooltip').style.display = 'none';
};

// Delegate hover handling for every `.param-icon` (legend + table). Delegation
// is needed because Grid.js re-renders table cells on sort/search, which would
// drop per-node listeners. `.param-icon * { pointer-events: none }` makes the
// SVG the only event target, so no flicker as the cursor moves over it.
document.addEventListener('mouseover', (e) => {
  const icon = e.target.closest?.('.param-icon');
  if (icon) showDescTooltip(e, icon.getAttribute('data-desc'));
});
document.addEventListener('mouseout', (e) => {
  if (e.target.closest?.('.param-icon')) hideParamsTooltip();
});

const _moveParamsTooltip = (event) => {
  const tip = document.getElementById('params-tooltip');
  if (!tip || tip.style.display === 'none') return;
  tip.style.left = (event.clientX + 14) + 'px';
  tip.style.top  = (event.clientY - tip.offsetHeight - 8) + 'px';
};

document.addEventListener('mousemove', _moveParamsTooltip);

/**
 * Render Scale selector
 */
const renderScaleSelector = () => {
  if (isChart(['table', 'image'])) {
    hide(document.querySelectorAll("#scale-form-group"));
  } else {
    show(document.querySelectorAll("#scale-form-group"), 'block');
  }

  if (isChart(['boxplot', 'bar_chart'])) {
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
  if (isChart('scatter') && hasQuantiles()) {
    show(document.querySelectorAll("#change-shades-form-group"), 'flex');
  } else {
    hide(document.querySelectorAll("#change-shades-form-group"));
  }
};

// True if any curve in the current plot carries quantile bounds.
const hasQuantiles = () => getPlotData().data.some(
  c => ("y_low" in c && "y_high" in c) || ("x_low" in c && "x_high" in c)
);

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
    // Keep view selectors visible in the config container.
    if (dropdown.closest('#config_container')) {
      continue;
    }
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
  document.getElementById('change_short_labels').checked = currentState.short_labels;
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
  // If the plot kind is not a default one, check the type of the custom plot in the data.
  if (!["bar_chart", "boxplot", "table", "scatter"].includes(plot_kind)) {
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
    x.push(
      state().short_labels
        ? (plotData.short_label || plotData.label)
        : plotData.label
    );
    y.push(getMedian(plotData.y));
    const plotText = plotData.text || '';
    colors.push(plotData.color || UNDEFINED_COLOR);
    texts.push(plotText);
  });

  return {x, y, color: colors, texts}
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
    case 'log': // used for boxplot or barchart
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

const MPL_AXIS = {
  showline: true,
  linecolor: 'black',
  linewidth: 1,
  mirror: true,
  ticks: 'outside',
  tickcolor: 'black',
  gridcolor: '#d9d9d9',
  griddash: 'dot',
  gridwidth: 0.5,
  zeroline: false,
  automargin: true,
};
const MPL_LAYOUT = {
  plot_bgcolor: 'white',
  paper_bgcolor: 'white',
  font: { family: 'DejaVu Sans, Arial, sans-serif', color: 'black' },
};

const getBarChartLayout = () => {
  let data = getPlotData();
  const layout = {
    autosize: true,
    modebar: {
      orientation: 'v',
    },
    yaxis: {
      ...MPL_AXIS,
      type: getScale().yaxis,
      title: data["ylabel"],
      tickformat: '~g',
    },
    xaxis: {
      ...MPL_AXIS,
      tickangle: -60,
      ticktext: Array(data.data.map(d => d.label)),
      categoryorder: 'trace',
      showgrid: false,  // X axis is text: no vertical gridlines
    },
    showlegend: false,
    title: data["title"],
    ...MPL_LAYOUT,
  };

  if (isSmallScreen()) {
    layout.dragmode = false;
  }

  // If no data available, plot "Not available"
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
      ...MPL_AXIS,
      type: getScale().yaxis,
      title: plot_info["ylabel"],
      tickformat: '~g',
    },
    xaxis: {
      ...MPL_AXIS,
      tickangle: (typeof plot_info.data[0].x[0] === "string") ? -60 : 0,
      showgrid: typeof plot_info.data[0].x[0] !== "string",  // hide vertical gridlines for text X axis
    },
    showlegend: false,
    title: plot_info["title"],
    ...MPL_LAYOUT,
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
      ...MPL_AXIS,
      type: getScale().xaxis,
      title: customData.xlabel,
      tickformat: '~g',
      tickangle: 0,
    },
    yaxis: {
      ...MPL_AXIS,
      type: getScale().yaxis,
      title: customData.ylabel,
      tickformat: '~g',
    },
    title: `${customData.title}`,
    ...MPL_LAYOUT,
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
    if (target.children[i].className.includes('curve')) {
      // Prefer the data-curve attribute (full name) when available.
      const attr = target.children[i].getAttribute('data-curve');
      if (attr) return attr;
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
 * MANAGE IMAGE RENDERING
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

const renderImages = () => {

  // Show and purge the container
  let image_container = document.getElementById('image_container');
  image_container.innerHTML = '';
  show(image_container);

  const plotData = getPlotData();
  if (!plotData || !plotData.data || plotData.data.length === 0) {
    image_container.innerHTML = '<div>No image data available</div>';
    return;
  }

  // Title
  if (plotData.title) {
    const titleEl = document.createElement('h2');
    titleEl.className = 'text-xl text-center text-gray-800 mb-6';
    titleEl.innerText = plotData.title;
    image_container.appendChild(titleEl);
  }

  const ncols = plotData.ncols || Math.min(plotData.data.length, 3);
  const grid = document.createElement('div');
  grid.className = `grid gap-6`;
  grid.style.gridTemplateColumns = `repeat(${ncols}, minmax(0, 1fr))`;

  plotData.data.forEach(imgData => {
    const card = document.createElement('div');

    if (imgData.image === null) {
      // Empty invisible block for grid alignment
      grid.appendChild(card);
      return;
    }

    card.className = 'bg-white rounded-lg shadow border border-gray-200 p-2 flex flex-col gap-2';

    const imgWrapper = document.createElement('div');
    imgWrapper.className = 'bg-gray-50 flex items-center justify-center';
    imgWrapper.style.aspectRatio = '1 / 1';

    if (imgData.image === '__incompatible__') {
      const msg = document.createElement('span');
      msg.className = 'text-sm text-gray-500 italic';
      msg.innerText = 'Incompatible image';
      imgWrapper.appendChild(msg);
    } else {
      const img = document.createElement('img');
      img.src = imgData.image;
      img.alt = imgData.label || '';
      img.className = 'block w-full h-full object-contain';
      img.style.imageRendering = 'pixelated';
      imgWrapper.appendChild(img);
    }
    card.appendChild(imgWrapper);

    if (imgData.label) {
      const labelEl = document.createElement('div');
      labelEl.className = 'text-sm text-center text-gray-700';
      labelEl.innerText = imgData.label;
      card.appendChild(labelEl);
    }

    grid.appendChild(card);
  });

  image_container.appendChild(grid);
};

/*
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * MANAGE TABLE RENDERING
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

// Global state for precision
let tableFloatPrecision = 4;

// Grid.js instance for the table plot, keyed by the table identity so that
// switching to another table rebuilds the grid (and resets its sorting),
// while re-rendering the same table (e.g. on precision change) keeps the
// user's current sorting.
let tableGrid = null;
let tableGridKey = null;

// Columns of the current table hidden through the column toggles.
let tableHiddenColumns = new Set();

// Table settings (order + hidden columns) coming from a saved view, applied
// once by the next renderTable build then cleared. Kept out of window._state
// so they don't leak onto other tables shown via the dropdowns.
let tablePendingView = null;

// Order ({column, ascending}) the current table was built with, used as the
// fallback when Grid.js reports a neutral sort (e.g. right after loading a
// view), so re-saving the view keeps that order.
let tableAppliedOrder = null;

const valueToFixed = (value) => {
  if (typeof value === 'number' && !Number.isInteger(value)) {
    return value.toFixed(tableFloatPrecision);
  }
  return value;
}

/**
 * Compare two cell values, handling both numbers and strings.
 *
 * The result must be -1/0/1, not a difference: Grid.js combines comparator
 * results with a bitwise OR, which truncates fractional values to 0 and
 * would make all close numbers compare as equal.
 */
const compareCells = (a, b) => {
  if (typeof a === 'number' && typeof b === 'number') {
    return a > b ? 1 : a < b ? -1 : 0;
  }
  return String(a).localeCompare(String(b));
}

const sortRows = (plotData, column, ascending) =>
  [...plotData.data].sort((a, b) => {
    const cmp = compareCells(a[column], b[column]);
    return ascending ? cmp : -cmp;
  });

/**
 * Sort the rows for the initial display. A saved view `order`
 * ({column: <name>, ascending: <bool>}) takes precedence; otherwise the
 * `default_order_column` (a column name or index) and `default_order_ascending`
 * metadata keys are used, defaulting to the first column ascending. Grid.js
 * then handles the interactive sorting from this initial order.
 */
const orderTableData = (plotData, order) => {
  let column = 0;
  const orderColumn = plotData.default_order_column;
  if (typeof orderColumn === 'string') {
    const idx = plotData.columns.indexOf(orderColumn);
    column = idx >= 0 ? idx : 0;
  } else if (typeof orderColumn === 'number') {
    column = orderColumn;
  }
  let ascending = plotData.default_order_ascending !== false;

  if (order && order.column != null) {
    const idx = plotData.columns.indexOf(order.column);
    if (idx >= 0) {
      column = idx;
      ascending = order.ascending !== false;
    }
  }

  tableAppliedOrder = {column: plotData.columns[column], ascending};
  return sortRows(plotData, column, ascending);
}

/**
 * Read the current sort (column name + direction) from the Grid.js header, or
 * null when no column is sorted. Grid.js tags the active sort button with
 * `gridjs-sort-asc` / `gridjs-sort-desc`.
 */
const getTableOrder = () => {
  for (const th of document.querySelectorAll('#table_container .gridjs-th')) {
    const btn = th.querySelector('.gridjs-sort');
    if (!btn) continue;
    const name = th.querySelector('.gridjs-th-content')?.textContent.trim();
    if (btn.classList.contains('gridjs-sort-asc')) {
      return {column: name, ascending: true};
    }
    if (btn.classList.contains('gridjs-sort-desc')) {
      return {column: name, ascending: false};
    }
  }
  // Grid.js reports a neutral sort: fall back to the order the table was built
  // with (default or restored from a view).
  return tableAppliedOrder;
}

function renderTable() {

  let table_container = document.getElementById('table_container');
  show(table_container);

  const plotData = getPlotData();
  if (!plotData || !plotData.columns || !plotData.data) {
    table_container.innerHTML = "<div>No data available</div>";
    tableGrid = null;
    tableGridKey = null;
    return;
  }

  const gridKey = [state().plot_kind, ...plotData.columns].join('|');
  if (tableGrid && tableGridKey === gridKey && !tablePendingView) {
    // Same table: refresh in place (e.g. after a precision change), keeping
    // the current sorting. The formatters read the global precision.
    document.getElementById('table-precision-label').innerText =
      `Float Precision: ${tableFloatPrecision}`;
    tableGrid.forceRender();
    return;
  }

  table_container.innerHTML = "";

  // Restore the hidden columns / order from a saved view when one is being
  // loaded, otherwise start fresh with the table's default order.
  tableHiddenColumns = new Set();
  if (tablePendingView && Array.isArray(tablePendingView.hidden)) {
    const valid = tablePendingView.hidden.filter(c => plotData.columns.includes(c));
    // Never hide every column.
    if (valid.length < plotData.columns.length) {
      valid.forEach(c => tableHiddenColumns.add(c));
    }
  }
  const orderedData = orderTableData(plotData, tablePendingView && tablePendingView.order);
  tablePendingView = null;

  // Grid.js table with sortable columns and a search bar
  const card = document.createElement("div");
  card.className = "w-full bg-white overflow-hidden mx-auto";

  // First column holds the row label: the plot's `get_metadata` provides the
  // `short_labels` / `descriptions` maps (keyed by first-column value). The
  // icon is an SVG, so it stays out of the LaTeX export.
  const solverCellHTML = (value) => {
    const full = String(value);
    const label = state().short_labels
      ? ((plotData.short_labels || {})[full] || full) : full;
    const desc = (plotData.descriptions || {})[full];
    return escapeHTML(label) + (desc ? descIconHTML(desc) : '');
  };

  const buildColumns = () => plotData.columns.map((name, colIdx) => ({
    name,
    hidden: tableHiddenColumns.has(name),
    sort: { compare: compareCells },
    formatter: colIdx === 0
      ? (value) => gridjs.html(solverCellHTML(value))
      : (value) => valueToFixed(value),
  }));

  tableGrid = new gridjs.Grid({
    columns: buildColumns(),
    data: orderedData,
    sort: true,
    search: true,
  });
  tableGrid.render(card);
  tableGridKey = gridKey;

  // Pill-shaped toggles to show/hide each column
  const columnsContainer = document.createElement("div");
  columnsContainer.className = "flex items-center flex-wrap px-4 pt-4";

  const columnsLabel = document.createElement("span");
  columnsLabel.innerText = "Columns:";
  columnsLabel.className = "mr-4 text-sm font-medium text-gray-700";
  columnsContainer.appendChild(columnsLabel);

  const setPillStyle = (pill, visible, name) => {
    const base = "inline-flex items-center px-3 py-1 mr-4 mt-1 rounded-full " +
      "text-sm font-medium cursor-pointer transition-all border ";
    if (visible) {
      pill.className = base +
        "border-transparent bg-blue-600 text-white hover:bg-blue-700";
      pill.innerText = `✓ ${name}`;
    } else {
      pill.className = base +
        "border-gray-300 bg-white text-gray-500 hover:bg-gray-100";
      pill.innerText = name;
    }
  };

  plotData.columns.forEach(name => {
    const label = document.createElement("label");
    const visible = !tableHiddenColumns.has(name);

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = visible;
    checkbox.className = "sr-only";

    const pill = document.createElement("span");
    setPillStyle(pill, visible, name);
    pill.title = "Show/hide column";

    checkbox.onchange = () => {
      if (checkbox.checked) {
        tableHiddenColumns.delete(name);
      } else if (tableHiddenColumns.size === plotData.columns.length - 1) {
        // Keep at least one column visible
        checkbox.checked = true;
        return;
      } else {
        tableHiddenColumns.add(name);
      }
      setPillStyle(pill, checkbox.checked, name);
      tableGrid.updateConfig({ columns: buildColumns() }).forceRender();
    };

    label.appendChild(checkbox);
    label.appendChild(pill);
    columnsContainer.appendChild(label);
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
  labelPrec.id = "table-precision-label";
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

  table_container.appendChild(card);

  footer.appendChild(precisionContainer);
  footer.appendChild(exportButton);
  footerWrapper.appendChild(columnsContainer);
  footerWrapper.appendChild(footer);
  table_container.appendChild(footerWrapper);
}


async function exportTable() {
  const button = document.getElementById("table-export");
  const defaultText = button.innerHTML;
  button.innerHTML = "Copying";

  // Export the table as displayed in the Grid.js table, so that the LaTeX
  // output matches the current sorting, search filter, visible columns and
  // float precision.
  const displayedColumns = Array.from(
    document.querySelectorAll('#table_container .gridjs-th-content'),
    el => el.textContent.trim()
  );
  const displayedRows = Array.from(
    document.querySelectorAll('#table_container .gridjs-table tbody tr')
  ).map(tr => Array.from(tr.querySelectorAll('td'), td => td.innerText));

  let value = "\\begin{tabular}{l";
  value += "c".repeat(displayedColumns.length);
  value += "}\n";
  value += "\\hline\n";

  value += displayedColumns[0].replace('_', '\\_');
  displayedColumns.slice(1).forEach(metric => value += ` & ${metric.replace('_', '\\_')}`);

  value += " \\\\\n";
  value += "\\hline\n";

  displayedRows.forEach(rowData => {
    value += rowData[0].replace('_', '\\_');
    rowData.slice(1).forEach(cell => {
      value += ` & ${cell.replace('_', '\\_')}`;
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

  const container = document.getElementById('legend_container');
  const legend = document.getElementById('plot_legend');
  show(container);

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

  // Create the HTML text node for the curve name in the legend.
  // Use short_label for display; keep the full name in a foldable <details>.
  const curveTraceData = data(curve);
  const shortLabel = (curveTraceData && curveTraceData.short_label) || curve;
  const fullLabel  = (curveTraceData && curveTraceData.full_label)  || curve;
  const useShort   = state().short_labels;
  const displayLabel = useShort ? shortLabel : fullLabel;

  const textContainer = document.createElement('div');
  textContainer.style.marginLeft = '0.5rem';
  textContainer.style.flex = '1';
  textContainer.className = 'curve';
  textContainer.setAttribute('data-curve', curve);
  textContainer.appendChild(document.createTextNode(displayLabel));

  // When short labels are toggled on, append a hover icon carrying the
  // trace's `description` (already formatted HTML, shown as-is).
  if (useShort && curveTraceData && curveTraceData.description) {
    textContainer.insertAdjacentHTML(
      'beforeend', descIconHTML(curveTraceData.description)
    );
  }

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
