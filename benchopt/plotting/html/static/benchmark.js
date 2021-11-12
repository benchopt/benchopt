$(document).ready(function () {
  $(".summary").dataTable({
    order: [[0, "desc"]],
  }); // reorder table by date
  if (location.hostname === "") {
    // local file
    $("[name='checkfiles']").css({
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

$("table").each(function (a, tbl) {
  var currentTableRows = $(tbl).find("tbody tr").length;
  $(tbl)
    .find("th")
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

function change(ll_item) {
  var td, i, fil;
  var filter = new Array();
  for (item = 0; item < ll_item.length; item++) {
    filter.push(
      document
        .getElementById("select" + ll_item[item].replace(/\s/g, ""))
        .value.toUpperCase()
    );
  }
  var table = document.getElementById("summary");
  var tr = table.getElementsByTagName("tr");
  for (i = 0; i < tr.length; i++) {
    tr[i].style.display = "";
    td = tr[i].getElementsByTagName("td")[2];
    if (td) {
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

function displaymore(id, loop_index) {
  var x = document.getElementById("subinfo" + loop_index);
  $(id).find("svg").toggleClass("fa-plus-circle fa-minus-circle");
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
}

var openbtn = document.getElementById("open");
if (openbtn) {
  var closebtn = document.getElementById("close");
  openbtn.style.display = "none";

  function openSideNav() {
    navbar = document.getElementById("sidenav");
    navbar.style.visibility = "visible";
    main = document.getElementById("main");
    if ($(window).width() < 900) {
      navbar.style.height = "100%";
      main.style.marginLeft = "0";
    } else {
      navbar.style.height = "1000px";
      main.style.marginLeft = "200px";
    }
    navbar.style.opacity = "1";
    openbtn.style.display = "none";
    closebtn.style.display = "";
  }

  if ($(window).width() > 900) {
    openSideNav();
  } else {
    closeSideNav();
  }

  function closeSideNav() {
    navbar = document.getElementById("sidenav");
    main = document.getElementById("main");
    navbar.style.visibility = "hidden";
    navbar.style.opacity = "0";
    navbar.style.height = "0";
    if ($(window).width() > 900) {
      main.style.marginLeft = "0px";
    }
    openbtn.style.display = "";
    closebtn.style.display = "none";
  }
}

$(function () {
  $("#dialogRm").dialog({
    autoOpen: false,
  });

  $("#trashBtn").click(function () {
    allChecked = document.querySelectorAll("input[name=checkfiles]:checked");
    delCmd = "rm \\\n <br />"; // n and br for html and copy to clipboard
    for (check of allChecked) {
      delCmd += $(check).attr("data-csv") + " \\\n <br />";
      delCmd += $(check).attr("data-html") + " \\\n <br />";
    }
    delCmd += "cache_run_list.json";
    $("#dialogRm").html(delCmd);
    $("#dialogRm")
      .dialog({
        title: "Remove selected entries",
        modal: true,
        draggable: true,
        resizable: false,
        width: "auto",
        buttons: {
          "Copy to clipboard": function () {
            navigator.clipboard.writeText($("#dialogRm").text());
          },
          "Remove row": function () {
            for (check of allChecked) {
              $(check).closest("tr").remove();
            }
          },
        },
      })
      .dialog("open");
  });
});
