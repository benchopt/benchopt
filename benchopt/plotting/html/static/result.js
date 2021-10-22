var global_state = {
  dataset_selector: [,],
  objective_selector: [,],
  objective_column: [,],
  plot_kind: [,],
}; // Object storing previous and current value of the dropdown selectors

/**
 * Initialize the global state of the selectors
 */
$(document).ready(function () {
  const selectors = [
    "dataset_selector",
    "objective_selector",
    "objective_column",
    "plot_kind",
  ];
  for (sel of selectors) {
    obj = document.getElementById(sel);
    global_state[sel][1] = global_state[sel][0] = obj.value;
    obj.attributes.counter = 0; // initialize dropdown counter
    showMe(obj); // display initial figure + one pass on all dropdowns
  }
});

/**
 * Get the id of the div containing the plotly graph div
 * @param  {String} which previous for previous graph state, anything for current
 * @return {String}       concatenated dataset,objectives and plot kind as id
 */
function get_id(which) {
  if (which === "previous") index = 0;
  // previous states
  else index = 1; // new states
  return Object.values(global_state) // all values of selectors
    .map(function (value) {
      return value[index]; // select only column of interest
    })
    .join(""); // join as string for complete id
}

/**
 * Only show the selected graph from dropdown menus
 */
function showMe(e) {
  if (global_state[e.id][1] !== "histogram") {
    Object.values(global_state).forEach((arr, _) => {
      arr[0] = arr[1];
    }); // shift all new values to only replace one after
    global_state[e.id].shift(); // previous value is now at index 0
  }
  global_state[e.id][1] = e.value; // set new value of selector
  for (let opt of e.options) {
    all_obj = document.getElementsByClassName(opt.value); // get all divs corresponding
    for (let obj of all_obj) {
      if (opt.value === e.value) obj.style.display = "block";
      else obj.style.display = "none"; // hide non necessary divs
    }
  }
  if (
    e.attributes.counter > 0 &&
    global_state.dataset_selector[0] === global_state.dataset_selector[1]
  ) {
    // if at least another graph was displayed before (initialized)
    visible_traces(); // keep traces coherent accross graphs
  }
  e.attributes.counter += 1; // out of initialization
}

// update the traces accross the different plots
function visible_traces() {
  prev_id = get_id("previous"); // id of previous graph
  now_id = get_id("now"); // id of current graph
  if (global_state.plot_kind[1] !== "histogram") {
    // only check name not type
    graph = document.getElementById(
      document.getElementById(prev_id).getElementsByTagName("div")[1].id
    ); // get revious plotly figure
    traces_visib = graph.data.map((trace) => trace.visible); // get previous visible traces
    graph = document.getElementById(
      document.getElementById(now_id).getElementsByTagName("div")[1].id
    );
    for (i = 0; i < graph.data.length; i++) {
      graph.data[i].visible = traces_visib[i]; // set visible traces for new graph
    }
    Plotly.redraw(graph); // redraw with cohesive visible traces
  }
}

/**
 * Change y axis scale of plotly graph (loglog <-> semilog-y)
 * @param  {Object} e  dropdown for axis log type
 * @param  {Array} all_ids  ids of containers of plots
 */
function changeScale(e, all_ids) {
  for (which = 0; which < all_ids.length; which++) {
    container = document.getElementById(all_ids[which]);
    id_graph = container.getElementsByTagName("div")[1].id;
    graph = document.getElementById(id_graph); // get plotly graph to change
    layout = graph.layout; // get layout to recover only axis
    switch (e.value) {
      case "loglog":
        layout.xaxis.type = "log";
        break;
      case "semilog-y":
        layout.xaxis.type = "linear";
        break;
    }
    Plotly.relayout(id_graph, layout); // change axis type of plot
  }
}

// modify the + into a - when clicking to show more system informations
$(".toggle").click(function () {
  $(this).find("svg").toggleClass("fa-plus-circle fa-minus-circle");
  x = document.getElementById("subinfo");
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
});
