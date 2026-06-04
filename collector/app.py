# Import the Docker SDK for Python to interact with the Docker daemon
import docker

# Import the requests library to send HTTP requests to the Prometheus HTTP API
import requests

# Import Flask to create a lightweight web server
# Response is used to return HTTP responses
from flask import Flask, Response, render_template, jsonify, request

# Gauge is used for metrics that can go up and down (CPU, memory)
# generate_latest formats metrics into Prometheus text format
# CONTENT_TYPE_LATEST sets the correct HTTP response header
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

# Initialize the Flask application
app = Flask(__name__)

# Create a Docker client using environment configuration
# This connects to the local Docker daemon (e.g., Docker Desktop on Mac)
client = docker.from_env()

# Base URL of the Prometheus server
# It's used for querying historical metric data through the Prometheus API
PROMETHEUS_URL = "http://localhost:9090"
# Prometheus scrape interval in seconds
# It's used when converting sampled power values into energy consumption
SCRAPE_INTERVAL_SECONDS = 5
# Estimated carbon emission factor for electricity usage in Turkey
# Unit: grams CO₂ per kilowatt-hour (gCO₂/kWh)
CO2_GRAMS_PER_KWH = 434
# Assumed LED bulb power consumption in watts
# It's used to calculate equivalent LED bulb usage duration
LED_BULB_WATTS = 9

# Define a Prometheus metric for container CPU usage
# metric name: container_cpu_usage_percent
# description: explains what the metric represents
# label: container_name allows tracking multiple containers
container_cpu_usage = Gauge(
    "container_cpu_usage_percent",
    "CPU usage percentage of a Docker container",
    ["container_name"]
)

# Define a Prometheus metric for container memory usage
# Memory is reported in megabytes (MB)
container_memory_usage = Gauge(
    "container_memory_usage_mb",
    "Memory usage of a Docker container in MB",
    ["container_name"]
)

# Define a Prometheus metric for estimated container power usage
# This is an estimation based on CPU utilization
container_estimated_power = Gauge(
    "container_estimated_power_watts",
    "Estimated power contribution of a Docker container in watts",
    ["container_name"]
)

# Define a Prometheus metric for total received network data
# RX stands for received data over the network
container_network_rx_mb = Gauge(
    "container_network_rx_mb",
    "Total network data received by a Docker container in MB",
    ["container_name"]
)

# Define a Prometheus metric for total transmitted network data
# TX stands for transmitted data over the network
container_network_tx_mb = Gauge(
    "container_network_tx_mb",
    "Total network data transmitted by a Docker container in MB",
    ["container_name"]
)

# Define a Prometheus metric for total network I/O activity
# Represents combined RX + TX traffic in MB
container_network_total_mb = Gauge(
    "container_network_total_mb",
    "Total network I/O of a Docker container in MB",
    ["container_name"]
)

# Define a Prometheus metric for total disk read activity
# Represents data read from disk in MB
container_disk_read_mb = Gauge(
    "container_disk_read_mb",
    "Total disk data read by a Docker container in MB",
    ["container_name"]
)

# Define a Prometheus metric for total disk write activity
# Represents data written to disk in MB
container_disk_write_mb = Gauge(
    "container_disk_write_mb",
    "Total disk data written by a Docker container in MB",
    ["container_name"]
)

# Define a Prometheus metric for total disk I/O activity
# Represents combined disk read + write operations in MB
container_disk_total_mb = Gauge(
    "container_disk_total_mb",
    "Total disk I/O of a Docker container in MB",
    ["container_name"]
)


def calculate_cpu_percent(stats):
    """
    Calculate CPU usage percentage for a container.

    Docker provides cumulative CPU usage values.
    We compute the difference (delta) between current and previous readings
    to estimate CPU usage over a short interval.

    Formula:
    CPU % = (cpu_delta / system_delta) * number_of_cpus * 100
    """

    # Calculate the difference in container CPU usage between two readings
    cpu_delta = (
        stats["cpu_stats"]["cpu_usage"]["total_usage"]
        - stats["precpu_stats"]["cpu_usage"]["total_usage"]
    )

    # Calculate the difference in total system CPU usage between two readings
    system_delta = (
        stats["cpu_stats"]["system_cpu_usage"]
        - stats["precpu_stats"]["system_cpu_usage"]
    )

    # Get the number of CPUs available to Docker
    online_cpus = stats["cpu_stats"].get("online_cpus", 1)

    # Avoid division by zero
    if system_delta > 0 and cpu_delta > 0:
        return (cpu_delta / system_delta) * online_cpus * 100.0

    return 0.0


def bytes_to_mb(value):
    # Convert bytes to megabytes
    # 1 MB = 1024 * 1024 bytes
    return value / (1024 * 1024)


def estimate_power_watts(cpu_percent, memory_mb, memory_limit_mb, online_cpus):
    """
    Estimate container power contribution in watts.

    The model uses:
    - CPU utilization
    - Memory utilization

    Assumptions:
    - Maximum host CPU power consumption: 35W
    - Maximum memory power contribution: 5W

    The result is an estimated relative power contribution,
    not a direct hardware power measurement.
    """

    # Assumed maximum CPU power consumption of the host machine
    host_max_cpu_power_watts = 35
    # Assumed maximum memory-related power contribution
    host_max_memory_power_watts = 5

    # Maximum possible CPU percentage across all cores
    # Example:
    # 4 cores -> max possible CPU usage = 400%
    max_cpu_percent = online_cpus * 100

    # Estimate CPU-related power usage proportionally based on the container CPU utilization
    cpu_power = host_max_cpu_power_watts * (cpu_percent / max_cpu_percent)

    # Estimate memory-related power contribution proportionally based on memory usage ratio
    if memory_limit_mb > 0:
        memory_power = host_max_memory_power_watts * (memory_mb / memory_limit_mb)
    else:
        # Fallback protection if memory limit is unavailable
        memory_power = 0

    # Return total estimated power usage
    return cpu_power + memory_power


def query_prometheus(query):
    """
    Send an instant PromQL query to Prometheus and return the result list.
    """
    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": query},
        timeout=5
    )

    response.raise_for_status()

    return response.json()["data"]["result"]


def get_energy_by_container(selected_range):
    """
    Calculate estimated energy usage per container for the selected time range.

    Unit:
    - container_estimated_power_watts is W
    - sum_over_time adds samples
    - multiplying by scrape interval gives watt-seconds
    - dividing by 3600 gives Wh
    """
    query = (
        f"sum by (container_name) "
        f"(sum_over_time(container_estimated_power_watts[{selected_range}])) "
        f"* {SCRAPE_INTERVAL_SECONDS} / 3600"
    )

    results = query_prometheus(query)

    energy_by_container = {}

    for item in results:
        container_name = item["metric"].get("container_name")
        energy_wh = float(item["value"][1])

        if container_name:
            energy_by_container[container_name] = energy_wh

    return energy_by_container


def collect_current_container_data():
    """
    Collect current Docker container metrics once and return
    them in a reusable structure.

    This data can be used both for:
    - Prometheus metric updates
    - Custom dashboard API responses
    """
    container_data = []

    containers = client.containers.list()

    for container in containers:
        stats = container.stats(stream=False)

        cpu_percent = calculate_cpu_percent(stats)

        online_cpus = stats["cpu_stats"].get("online_cpus", 1)

        memory_usage = stats["memory_stats"]["usage"]
        memory_usage_mb = bytes_to_mb(memory_usage)

        memory_limit = stats["memory_stats"].get("limit", 0)
        memory_limit_mb = bytes_to_mb(memory_limit)

        power_watts = estimate_power_watts(
            cpu_percent,
            memory_usage_mb,
            memory_limit_mb,
            online_cpus
        )

        network_rx_mb, network_tx_mb, network_total_mb = calculate_network_io_mb(stats)
        disk_read_mb, disk_write_mb, disk_total_mb = calculate_disk_io_mb(stats)

        container_data.append({
            "name": container.name,
            "status": container.status,
            "cpuPercent": cpu_percent,
            "memoryMb": memory_usage_mb,
            "powerWatts": power_watts,
            "networkRxMb": network_rx_mb,
            "networkTxMb": network_tx_mb,
            "networkTotalMb": network_total_mb,
            "diskReadMb": disk_read_mb,
            "diskWriteMb": disk_write_mb,
            "diskTotalMb": disk_total_mb
        })

    return container_data


def collect_container_metrics():
    """
    Update Prometheus metrics using current Docker container data.
    """
    containers = collect_current_container_data()

    for container in containers:
        container_name = container["name"]

        container_cpu_usage.labels(
            container_name=container_name
        ).set(container["cpuPercent"])

        container_memory_usage.labels(
            container_name=container_name
        ).set(container["memoryMb"])

        container_estimated_power.labels(
            container_name=container_name
        ).set(container["powerWatts"])

        container_network_rx_mb.labels(
            container_name=container_name
        ).set(container["networkRxMb"])

        container_network_tx_mb.labels(
            container_name=container_name
        ).set(container["networkTxMb"])

        container_network_total_mb.labels(
            container_name=container_name
        ).set(container["networkTotalMb"])

        container_disk_read_mb.labels(
            container_name=container_name
        ).set(container["diskReadMb"])

        container_disk_write_mb.labels(
            container_name=container_name
        ).set(container["diskWriteMb"])

        container_disk_total_mb.labels(
            container_name=container_name
        ).set(container["diskTotalMb"])


@app.route("/api/dashboard")
def dashboard():
    """
    Generates dashboard data for the selected time range and container.
    The endpoint collects current container statistics, retrieves historical
    energy consumption data, calculates estimated CO₂ emissions, aggregates
    summary metrics, and returns the processed information as JSON for the
    web dashboard.
    """
    selected_range = request.args.get("range", "10m")
    selected_container = request.args.get("container", "all")

    raw_containers = collect_current_container_data()
    energy_by_container = get_energy_by_container(selected_range)

    dashboard_containers = []

    for container in raw_containers:
        energy_wh = energy_by_container.get(container["name"], 0)
        co2_grams = (energy_wh / 1000) * CO2_GRAMS_PER_KWH

        dashboard_containers.append({
            "name": container["name"],
            "status": container["status"],
            "cpuPercent": round(container["cpuPercent"], 2),
            "memoryMb": round(container["memoryMb"], 2),
            "powerWatts": round(container["powerWatts"], 2),
            "energyWh": round(energy_wh, 4),
            "co2Grams": round(co2_grams, 4)
        })

    if selected_container != "all":
        dashboard_containers = [
            container for container in dashboard_containers
            if container["name"] == selected_container
        ]

    total_power = round(
        sum(container["powerWatts"] for container in dashboard_containers),
        2
    )

    total_energy = round(
        sum(container["energyWh"] for container in dashboard_containers),
        4
    )

    total_co2 = round(
        sum(container["co2Grams"] for container in dashboard_containers),
        4
    )

    led_hours = total_energy / LED_BULB_WATTS

    highest_consumer = "-"
    if dashboard_containers:
        highest_consumer = max(
            dashboard_containers,
            key=lambda item: item["powerWatts"]
        )["name"]

    return jsonify({
        "selectedRange": selected_range,
        "selectedContainer": selected_container,
        "summary": {
            "totalPowerWatts": total_power,
            "energyWh": total_energy,
            "co2Grams": total_co2,
            "highestConsumer": highest_consumer,
            "ledHours": round(led_hours, 4)
        },
        "containers": dashboard_containers
    })


def calculate_network_io_mb(stats):
    """
    Calculate total network input/output in MB.

    RX means received data.
    TX means transmitted data.
    """

    total_rx_bytes = 0
    total_tx_bytes = 0

    # Retrieve network statistics for all container interfaces
    networks = stats.get("networks") or {}

    # Sum received and transmitted bytes across all interfaces
    for interface_stats in networks.values():
        total_rx_bytes += interface_stats.get("rx_bytes", 0)
        total_tx_bytes += interface_stats.get("tx_bytes", 0)

    # Convert total network traffic values from bytes to MB
    rx_mb = bytes_to_mb(total_rx_bytes)
    tx_mb = bytes_to_mb(total_tx_bytes)
    total_mb = rx_mb + tx_mb

    return rx_mb, tx_mb, total_mb


def calculate_disk_io_mb(stats):
    """
    Calculate total disk read/write in MB.
    Docker reports block I/O stats under blkio_stats.
    Read means data read from disk.
    Write means data written to disk.
    """

    total_read_bytes = 0
    total_write_bytes = 0

    # Retrieve Docker block I/O statistics
    io_stats = stats.get("blkio_stats", {}).get(
        "io_service_bytes_recursive") or []

    # Iterate through all block I/O operations
    for entry in io_stats:
        operation = entry.get("op")
        value = entry.get("value", 0)

        # Separate read and write operations
        if operation == "Read":
            total_read_bytes += value
        elif operation == "Write":
            total_write_bytes += value

    # Convert disk I/O values from bytes to MB
    read_mb = bytes_to_mb(total_read_bytes)
    write_mb = bytes_to_mb(total_write_bytes)
    total_mb = read_mb + write_mb

    return read_mb, write_mb, total_mb


@app.route("/metrics")
def metrics():
    # Update metrics before exposing them to Prometheus
    collect_container_metrics()

    # Return metrics in Prometheus text format
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/")
def home():
    """
    Basic check endpoint.
    Can be used to verify that the collector service is running.
    """
    return render_template("index.html")


if __name__ == "__main__":
    """
    Entry point of the application.

    Runs the Flask development server:
    - host="0.0.0.0" allows access from outside the container/host
    - port=8000 defines the HTTP port
    """
    app.run(host="0.0.0.0", port=8000)