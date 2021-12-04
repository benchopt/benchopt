/*********************************************
 *  JS functions for the benchmark page.
 *********************************************/

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Format the table once the page has been loaded.
* - Order the table based on run date.
* - Add trash button if it is a local file
* - Hide sysinfo if the column is empty
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
$(function () {
  // Sort the table by descending date order (date being in column 0)
  $(".summary").dataTable({
    order: [[0, "desc"]],
  }); // reorder table by date

  //Add trash button if this is a local document
  if (location.hostname === "") {
    $("[name='checkfiles']").css({
      // only show lines that not hidden by user
      display: "block",
      "margin-left": "auto",
      float: "left",
    }); // display checkboxes
    $("#trashBtn").css({
      display: "block",
      float: "left",
      "margin-bottom": "5vh",
    });
  }

  // Hide the system information column if it is empty
  $("table").each(function (a, tbl) {
    var currentTableRows = $(tbl).find("tbody tr").length;
    $(tbl)
      .find("th") // also take care of table head
      .each(function (i) {
        var remove = 0;
        var currentTable = $(this).parents("table");
        var tds = currentTable.find("tr td:nth-child(" + (i + 1) + ")");
        tds.each(function (j) {
          if ($(this)[0].innerText.length == 0) remove++;
        });
        if (remove == currentTableRows) {
          $(this).hide();
          tds.hide();
        }
      });
  });
});

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Callback for the side bar select box.
* Filter the benchmark runs in the table
* based on the current selected values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
function change(ll_item) {
  var td, i, fil;
  var filter = new Array();
  for (item = 0; item < ll_item.length; item++) {
    filter.push(
      document
        .getElementById("select" + ll_item[item].replace(/\s/g, ""))
        .value.toUpperCase()
    ); // Add dropdown value on top of the array (order is necessary)
  }
  var table = document.getElementById("summary");
  var tr = table.getElementsByTagName("tr");
  for (i = 0; i < tr.length; i++) {
    tr[i].style.display = "";
    td = tr[i].getElementsByTagName("td")[2];
    if (td) {
      // do not display elements from table not in filter
      for (fil = 0; fil < filter.length; fil++) {
        if (
          td.innerHTML.toUpperCase().indexOf(filter[fil]) > -1 &&
          tr[i].style.display !== "none"
        ) {
          tr[i].style.display = "";
        } else {
          tr[i].style.display = "none";
        }
      }
    }
  }
}

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Callback for the +/- button of system-info.
* Display sub info in the table.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
$(function () {
  $(".button.buttoncent").click(displayMore);
});

function displayMore() {
  var loop_index = $(this).attr("data-idx");
  var x = document.getElementById("subinfo" + loop_index);
  $(this).find("svg").toggleClass("fa-plus-circle fa-minus-circle");
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
}

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Open or close sidebar when document ready
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
$(function () {
  var openbtn = document.getElementById("open");
  var closebtn = document.getElementById("close");
  if (openbtn) {
    openbtn.style.display = "none"; // only display close button is sidenav opened
    // default display depending on device
    if ($(window).width() > 900) {
      openSideNav({ data: { op: openbtn, cl: closebtn } });
    } else {
      closeSideNav({ data: { op: openbtn, cl: closebtn } });
    }
  }
  // click method is the recommended way
  $("#open").click({ op: openbtn, cl: closebtn }, openSideNav);
  $("#close").click({ op: openbtn, cl: closebtn }, closeSideNav);
  $(".closebtn").click({ op: openbtn, cl: closebtn }, closeSideNav);
});

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Open sidebar: the argument must be an event
* ie an object containing a data dictionnary
* the data has a key op for the open button
* and a key cl for the close button.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
function openSideNav(event) {
  openbtn = event.data.op;
  closebtn = event.data.cl;
  navbar = document.getElementById("sidenav");
  navbar.style.visibility = "visible";
  main = document.getElementById("main");
  if ($(window).width() < 900) {
    // mobile adaptativity
    navbar.style.height = "100%";
    main.style.marginLeft = "0";
  } else {
    navbar.style.height = "1000px";
    main.style.marginLeft = "200px";
  }
  navbar.style.opacity = "1";
  openbtn.style.display = "none"; // hide open button
  closebtn.style.display = ""; // show close button
}

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Same as openSideNav above but for closing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
function closeSideNav(event) {
  openbtn = event.data.op;
  closebtn = event.data.cl;
  navbar = document.getElementById("sidenav");
  main = document.getElementById("main");
  navbar.style.visibility = "hidden";
  navbar.style.opacity = "0";
  navbar.style.height = "0";
  if ($(window).width() > 900) {
    // adapt to devices
    main.style.marginLeft = "0px";
  }
  openbtn.style.display = ""; // show open button
  closebtn.style.display = "none"; // hide close button
}

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Launch a dialog box to hide rows in table or
* get the files checked by user in local rendering.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/
$(function () {
  $("#dialogRm").dialog({
    autoOpen: false, // only open when needed
  });

  // click on delete button in the dialog box
  $("#trashBtn").click(trashIconDialog);
});

// copy content from trash dialog box in clipboard
function clipboardCopy() {
  navigator.clipboard.writeText($("#dialogRm").text());
}

// remove rows with checked checkboxes until refresh
function hideRows(allChecked) {
  for (check of allChecked) {
    $(check).closest("tr").remove();
  }
}

// open dialog to get paths of checked files and/or hide table rows
function trashIconDialog() {
  // get files with checheck checkbox
  allChecked = document.querySelectorAll("input[name=checkfiles]:checked");
  delCmd = "rm \\\n <br />"; // n and br for html and copy to clipboard
  for (check of allChecked) {
    delCmd += $(check).attr("data-csv") + " \\\n <br />";
    delCmd += $(check).attr("data-html") + " \\\n <br />";
  }
  delCmd += "cache_run_list.json"; // add the cache file
  $("#dialogRm").html(delCmd); // modify the content in the html file
  $("#dialogRm") // dialog box
    .dialog({
      title: "Remove selected entries",
      modal: true,
      draggable: true, // the user can move it
      resizable: false, // but not resize it
      width: "auto",
      buttons: {
        "Copy to clipboard": clipboardCopy,
        "Hide row": hideRows.bind(null, allChecked), // binder to use params
      },
    })
    .dialog("open"); // open dialog box on click
}
