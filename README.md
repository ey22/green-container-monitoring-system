# Green Container Monitoring System

## Project Overview

Green Container Monitoring System is a lightweight monitoring solution designed to track the resource consumption and environmental impact of Docker containers.

The system collects container-level metrics such as CPU usage, memory consumption, network activity and disk I/O statistics. Based on these metrics, it calculates estimated power usage, energy consumption and CO₂ emissions and visualizes the results through a custom web dashboard and Grafana dashboards.

## Features

- Automatic discovery of running Docker containers
- Real-time CPU and memory monitoring
- Estimated power consumption calculation
- Estimated energy usage calculation
- Estimated CO₂ emission calculation
- Interactive web dashboard
- Grafana integration for visualization
- Prometheus-based metric storage

## Technologies Used

- Python
- Flask
- Docker
- Docker Compose
- Docker SDK for Python
- Prometheus
- Grafana
- Chart.js

## Project Structure

```text
collector/
    Metric collection and Prometheus exporter

dashboard/
    Flask-based web dashboard

prometheus/
    Prometheus configuration

docker-compose.yml
    Service orchestration configuration
```

## Installation

### Prerequisites

- Docker
- Docker Compose
- Python 3.x

### Clone the Repository

```bash
git clone https://github.com/ey22/green-container-monitoring-system.git
cd green-container-monitoring-system
```

### Start Prometheus and Grafana

Prometheus and Grafana are started using Docker Compose:

```bash
docker compose up -d
```

### Start the Flask Dashboard

After Prometheus and Grafana are running, start the Flask application manually from the app.py file.
```bash
python dashboard/app.py
```

## Accessing the Dashboard

Custom Dashboard:

```text
http://localhost:8000
```

Grafana Dashboard:

```text
http://localhost:3000
```

Prometheus:

```text
http://localhost:9090
```

## Sustainability Metrics

The system estimates:

- Power Consumption (W)
- Energy Consumption (Wh)
- CO₂ Emissions (g)
- Usage time equivalent of a 9W LED bulb (min)

### Custom Dashboard
<img width="1419" height="671" alt="Screenshot 2026-06-04 at 15 08 34" src="https://github.com/user-attachments/assets/1e41e19f-7e4f-436a-99a5-87fd9defaa20" />
<img width="1419" height="671" alt="Screenshot 2026-06-04 at 15 09 23" src="https://github.com/user-attachments/assets/94602c85-a0cd-46b6-a096-329c845b96cf" />

### Grafana Dashboard
<img width="1384" height="706" alt="Screenshot 2026-06-04 at 15 12 23" src="https://github.com/user-attachments/assets/c17569ac-a85d-441a-bdf5-b979ed4836fc" />
<img width="1384" height="731" alt="Screenshot 2026-06-04 at 15 13 09" src="https://github.com/user-attachments/assets/ac185429-47d1-4632-9cfa-4b02a91c3b7f" />






