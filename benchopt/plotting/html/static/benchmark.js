$(document).ready(function () {
  // Sort the table by descending date order (date being in column 0)
  $(".summary").dataTable({
    order: [[0, "desc"]],
  }); // reorder table by date
  if (location.hostname === "") {
    // local file and not doc website
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
});

// hide columns without content (if system informations not available)
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

/**
 * Filter table from dropdown current value
 */
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

/**
 * Display subinfo in the table
 * Toggle between + and - icon button
 */
function displaymore(id, loop_index) {
  var x = document.getElementById("subinfo" + loop_index);
  $(id).find("svg").toggleClass("fa-plus-circle fa-minus-circle");
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
}

// handle sidebar navigation
var openbtn = document.getElementById("open");
if (openbtn) {
  var closebtn = document.getElementById("close");
  openbtn.style.display = "none"; // only display close button is sidenav opened

  // function to open the sidebar navigation
  function openSideNav() {
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

  // default display depending on device
  if ($(window).width() > 900) {
    openSideNav();
  } else {
    closeSideNav();
  }

  // function to close the sidebar navigation
  function closeSideNav() {
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
}

// dialog box to get path of files we would like to remove
$(function () {
  $("#dialogRm").dialog({
    autoOpen: false, // only open when needed
  });

  // click on delete button in the dialog box
  $("#trashBtn").click(function () {
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
          "Copy to clipboard": function () {
            // copy content in clipboard
            navigator.clipboard.writeText($("#dialogRm").text());
          },
          "Remove row": function () {
            // remove rows with checked checkboxes until refresh
            for (check of allChecked) {
              $(check).closest("tr").remove();
            }
          },
        },
      })
      .dialog("open"); // open dialog box on click
  });
});
