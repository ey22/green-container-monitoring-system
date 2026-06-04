/*
 * Dashboard logic for the Green Container Monitoring System.
 * Retrieves monitoring data from the Flask backend, updates
 * dashboard metrics, manages container filters, and renders
 * energy and power consumption charts.
 */
async function loadDashboard() {
// Loads dashboard data from the backend and updates all UI components.
  const range = document.getElementById("timeRange").value;
  const container = document.getElementById("containerSelect").value;

  const response = await fetch(`/api/dashboard?range=${range}&container=${container}`);
  const data = await response.json();

  document.getElementById("totalPower").textContent =
    `${data.summary.totalPowerWatts} W`;

  document.getElementById("energyUsed").textContent =
    `${data.summary.energyWh} Wh`;

  document.getElementById("co2").textContent =
    `${data.summary.co2Grams} g`;

  document.getElementById("highestConsumer").textContent =
    data.summary.highestConsumer;

  const ledMinutes = data.summary.ledHours * 60;
  document.getElementById("ledHours").textContent =
      ledMinutes < 60
        ? `${ledMinutes.toFixed(2)} min`
        : `${data.summary.ledHours} h`;

  const tableBody = document.getElementById("containerTableBody");
  tableBody.innerHTML = "";

  data.containers.forEach(item => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${item.name}</td>
      <td>${item.status}</td>
      <td>${item.cpuPercent}</td>
      <td>${item.memoryMb}</td>
      <td>${item.powerWatts}</td>
      <td>${item.energyWh}</td>
      <td>${item.co2Grams}</td>
    `;

    tableBody.appendChild(row);
  });

  updateContainerDropdown(data.containers, container);
  updateCharts(data);
}

function updateContainerDropdown(containers, selectedContainer) {
// Updates the container selection dropdown based on available containers.
  const select = document.getElementById("containerSelect");
  const currentOptions = Array.from(select.options).map(option => option.value);

  containers.forEach(container => {
    if (!currentOptions.includes(container.name)) {
      const option = document.createElement("option");
      option.value = container.name;
      option.textContent = container.name;
      select.appendChild(option);
    }
  });

  select.value = selectedContainer;
}

let powerChart;
let energyChart;

function updateCharts(data) {
// Creates and refreshes dashboard charts using the latest metric data.
  const labels = data.containers.map(item => item.name);
  const powerValues = data.containers.map(item => item.powerWatts);
  const energyValues = data.containers.map(item => item.energyWh);

  if (powerChart) {
    powerChart.destroy();
  }

  powerChart = new Chart(document.getElementById("powerChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Power W",
        data: powerValues
      }]
    }
  });

  if (energyChart) {
    energyChart.destroy();
  }

  energyChart = new Chart(document.getElementById("energyChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Energy Wh",
        data: energyValues
      }]
    }
  });
}

document.getElementById("timeRange").addEventListener("change", loadDashboard);
document.getElementById("containerSelect").addEventListener("change", loadDashboard);

loadDashboard();
setInterval(loadDashboard, 10000);