var globalState = {
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
    globalState[sel][1] = globalState[sel][0] = obj.value;
    obj.attributes.counter = 0; // initialize dropdown counter
    showMe(obj); // display initial figure + one pass on all dropdowns
  }
});

/**
 * Get the id of the div containing the plotly graph div
 * @param  {String} which previous for previous graph state, anything for current
 * @return {String}       concatenated dataset,objectives and plot kind as id
 */
function getId(which) {
  if (which === "previous") index = 0;
  // previous states
  else index = 1; // new states
  return Object.values(globalState) // all values of selectors
    .map(function (value) {
      return value[index]; // select only column of interest
    })
    .join(""); // join as string for complete id
}

/**
 * Only show the selected graph from dropdown menus
 */
function showMe(e) {
  if (globalState[e.id][1] !== "histogram") {
    Object.values(globalState).forEach((arr, _) => {
      arr[0] = arr[1];
    }); // shift all new values to only replace one after
    globalState[e.id].shift(); // previous value is now at index 0
  }
  globalState[e.id][1] = e.value; // set new value of selector
  for (let opt of e.options) {
    allObj = document.getElementsByClassName(opt.value); // get all divs corresponding
    for (let obj of allObj) {
      if (opt.value === e.value) obj.style.display = "block";
      else obj.style.display = "none"; // hide non necessary divs
    }
  }
  if (
    e.attributes.counter > 0 &&
    globalState.dataset_selector[0] === globalState.dataset_selector[1]
  ) {
    // if at least another graph was displayed before (initialized)
    visibleTraces(); // keep traces coherent accross graphs
  }
  e.attributes.counter += 1; // out of initialization
}

// update the traces accross the different plots
function visibleTraces() {
  prevId = getId("previous"); // id of previous graph
  nowId = getId("now"); // id of current graph
  if (globalState.plot_kind[1] !== "histogram") {
    // only check name not type
    graph = document.getElementById(
      document.getElementById(prevId).getElementsByTagName("div")[1].id
    ); // get revious plotly figure
    tracesVisib = graph.data.map((trace) => trace.visible); // get previous visible traces
    graph = document.getElementById(
      document.getElementById(nowId).getElementsByTagName("div")[1].id
    );
    for (i = 0; i < graph.data.length; i++) {
      graph.data[i].visible = tracesVisib[i]; // set visible traces for new graph
    }
    Plotly.redraw(graph); // redraw with cohesive visible traces
  }
}

/**
 * Change y axis scale of plotly graph (loglog <-> semilog-y)
 * @param  {Object} e  dropdown for axis log type
 * @param  {Array} allIds  ids of containers of plots
 */
function changeScale(e, allIds) {
  for (which = 0; which < allIds.length; which++) {
    container = document.getElementById(allIds[which]);
    idGraph = container.getElementsByTagName("div")[1].id;
    graph = document.getElementById(idGraph); // get plotly graph to change
    layout = graph.layout; // get layout to recover only axis
    switch (e.value) {
      case "loglog":
        layout.xaxis.type = "log";
        break;
      case "semilog-y":
        layout.xaxis.type = "linear";
        break;
    }
    Plotly.relayout(idGraph, layout); // change axis type of plot
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
