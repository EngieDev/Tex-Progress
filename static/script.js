$(document).ready(function() {
  applySettings();
  log();
  drawChart();

  window.colours = {}
  setInterval(drawChart, 30000);
  setInterval(log, 10000);
});

// Random colour function for chartjs
function randomRGB() {
  return "rgb(" + Math.floor(Math.random()*255) + "," + Math.floor(Math.random()*255) + "," + Math.floor(Math.random()*255) + ")"
}

// Gets setting from api and applies them to the interface
function applySettings() {
  jQuery.getJSON("/api/settings/", function(data){
    $("#inputTexFile").val(data.texFile);
    $("#inputPeriod").val(data.period);
    $("#inputPort").val(data.port);
  });
}

// Sends settings back to the backend when form gets submitted
$("#settings").submit(function(e) {
    $.ajax({
       type: "POST",
       url: "/api/settings/",
       dataType: "json",
       data: JSON.stringify({
         "texFile": $("#inputTexFile").val(),
         "period":  $("#inputPeriod").val(),
         "port":  $("#inputPort").val()
       }),
       success: function(data){
         applySettings();
       },
       error: function(data){
            alert('An error occurred.');
            console.log(data);
        },
    });
    // Disables form submission via normal methods
    e.preventDefault();
});

// Updates the log
function log() {
  jQuery.getJSON("/api/log/", function(data){
    var string = "";
    data.forEach(function(m) {
      string = string + '<div class="message">' + m + '</div>'
    })

    $('#log').html(string);
  });
}

function drawChart() {
  options = {
				responsive: true,
				title: {
					display: true,
					text: 'Data:'
				},
				tooltips: {
					mode: 'index',
				},
				hover: {
					mode: 'index'
				},
				scales: {
					xAxes: [{
            type: 'time',
						scaleLabel: {
							display: true,
							labelString: 'Time'
						}
					}],
					yAxes: [{
						stacked: true,
						scaleLabel: {
							display: true,
							labelString: 'Word Count'
						}
					}]
				}
			};
  var datasets = [];
  var labels = [];

  jQuery.getJSON("/api/data/", function(data){
    data.timestamps.forEach(function(timestamp){
      labels.push(moment(parseInt(timestamp)*1000));
    });

    for(var key in data.data){
      if(key in window.colours){
        colour = window.colours[key]
      } else {
        colour = randomRGB();
        window.colours[key] = colour
      }

      d = {
        label: data.data[key]["name"],
        data: data.data[key]["values"],
        borderColor: colour,
        backgroundColor: colour,
      };
      datasets.push(d);
    }

    ctx = document.getElementById("chart").getContext("2d");

    if(typeof window.countChart == "undefined"){
      config = {
        type: "line",
        data: {
          datasets: datasets,
          labels: labels,
        },
        options: options
      };

      window.countChart = new Chart(ctx, config);
    } else {
      window.countChart.data.labels = labels
      window.countChart.data.datasets = datasets
      window.countChart.update()
    }
  });
}
