function getVibrationChartConfig() {
    return {
        type: 'line',
        data: {
            datasets: [{
                borderColor: "#07a889",
                borderWidth: 1,
                pointRadius: 0,
                data: []
            }]
        },
        options: {
            animation: false,
            maintainAspectRatio: false,
            parsing: false,
            normalized: true,
            interaction: {
                intersect: false
            },
            scales: {
                x: {
                    type: 'linear',
                    min: 0,
                    max: 50000
                },
                y: {
                    min: -2500,
                    max: 2500
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Vibration Data'
                }
            }
        }
    }
};

class MachineDashboard {
    constructor() {
        this.activeMachine = null;
        this.dashboardState = 'initialized';
        this.socket = io.connect('http://' + window.location.hostname + ':' + location.port);
        this.vibrationChartX = this.initVibrationChart("vibrationChartX");
        this.vibrationChartY = this.initVibrationChart("vibrationChartY");
        this.vibrationChartZ = this.initVibrationChart("vibrationChartZ");

        this.vibrationCharts = [this.vibrationChartX, this.vibrationChartY, this.vibrationChartZ];

        this.initSocketEvents();
    }

    initVibrationChart(elementId) {
        return new Chart(document.getElementById(elementId), getVibrationChartConfig());
    }

    initSocketEvents() {
        this.socket.on('connect', () => {
            console.log('Connected to socket server.');
            this.dashboardState = 'connected';
            this.updateVisibility();
        });
        this.socket.on('disconnect', () => {
            console.warn('Disconnected from socket server.');
            this.dashboardState = 'disconnected';
            this.highlightActiveMachine(null);
            this.updateVisibility("Disconnected. Trying to reconnect...");
        });
        this.socket.on('error', error => {
            console.error('Socket error:', error);
            this.dashboardState = 'error';
            this.updateVisibility("An error occurred. Please refresh or contact support.");
        });

        this.socket.on('factory_machine_status', data => this.updateMachineStatus(data.machine_id, data.status));
        this.socket.on('initial-status', data => this.initializeAllMachineStatuses(data));
        this.socket.on('start-chart', () => this.startCharts());
        this.socket.on('stop-chart', () => this.stopCharts());
        this.socket.on('update-chart', data => this.updateCharts(data));
    }

    initializeAllMachineStatuses(data) {
        for (let machine_id in data) {
            this.updateMachineStatus(machine_id, data[machine_id]);
        }
        if (this.activeMachine) {
            this.handleMachineSelection(this.activeMachine);
        }
    }

    updateMachineStatus(machine_id, status) {
        console.log(`[MachineDashboard] machine '${machine_id}' state change to '${status}'`);
        let machineElement = document.getElementById(machine_id);
        if (machineElement) {
            let statusPill = machineElement.querySelector('.status-pill');
            statusPill.textContent = status;

            this.setMachineAppearance(machineElement, status);

            if (status === "Starting" && machine_id === this.activeMachine) {
                this.clearCharts();
            }
        }
    }

    startCharts() {
        this.clearCharts();

        this.updateVisibility();
    }

    stopCharts() {
        this.clearCharts();
        this.updateVisibility();
    }

    updateCharts(data) {
        const targetMachineId = this.activeMachine === null ? data.machine_id : this.activeMachine;
        if (data.machine_id !== targetMachineId) {
            this.socket.emit('toggle-machine-data', { machine_id: targetMachineId });
        }

        if (data.sequence_start === 0) {
            this.clearCharts();
        }

        for (let i = 0; i < data.vibration_data.length; i++) {
            let xyz = data.vibration_data[i];
            let j = data.sequence_start + i;

            this.vibrationCharts.forEach((chart, index) => {
                chart.data.datasets[0].data.push({ x: j, y: xyz[index] });
            });
        }

        this.vibrationCharts.forEach(chart => {
            chart.update();
        });
    }

    updateVisibility(message) {
        if (this.dashboardState === 'connected' && this.activeMachine) {
            this.showCharts();
            this.hidePlaceholder();
        } else {
            this.hideCharts();
            this.showPlaceholder(message || "Please select a machine to view its vibration data.");
        }
    }

    showCharts() {
        const titles = ['Vibration X for ', 'Vibration Y for ', 'Vibration Z for '];

        this.vibrationCharts.forEach((chart, index) => {
            chart.canvas.style.visibility = "visible";
            chart.options.plugins.title.text = titles[index] + this.activeMachine;
            chart.update();
        });
    }

    hideCharts() {
        this.vibrationCharts.forEach(chart => {
            chart.canvas.style.visibility = "hidden";
        });
    }

    showPlaceholder(message) {
        let placeholder = document.getElementById('chart-placeholder');
        placeholder.textContent = message;
        placeholder.style.display = "block";
    }

    hidePlaceholder() {
        let placeholder = document.getElementById('chart-placeholder');
        placeholder.style.display = "none";
    }

    handleMachineSelection(machine_id) {
        if (this.dashboardState !== 'connected') {
            return
        }

        this.highlightActiveMachine(machine_id);
        try {
            this.socket.emit('toggle-machine-data', { machine_id: machine_id });
        } catch (error) {
            console.error('Error while toggling machine data:', error);
        }
        this.updateVisibility();
    }

    highlightActiveMachine(machine_id) {
        let machineElement = machine_id ? document.getElementById(machine_id) : null;

        let machines = document.querySelectorAll('.machine');
        machines.forEach(function (machine) {
            machine.classList.remove('active');
        });

        let prevState = this.activeMachine;  // Save the previous state

        if (!machine_id) {
            this.activeMachine = null;
        }
        else if (this.activeMachine && this.activeMachine === machine_id) {
            this.activeMachine = null;  // If the machine is toggled off, set the activeMachine to null
        } else {
            this.activeMachine = machine_id;  // If a new machine is toggled on, set the activeMachine
            machineElement.classList.add('active');
        }

        console.log(`[MachineDashboard] activeMachine changed from '${prevState}' to '${this.activeMachine}'`);
    }

    setMachineAppearance(machineElement, status) {
        let imageElement = machineElement.querySelector('img');
        let statusPill = machineElement.querySelector('.status-pill');

        machineElement.classList.remove('inspection');
        machineElement.classList.remove('maintenance');

        // Set the image and pill color based on status
        switch (status) {
            case "Initializing":
                imageElement.setAttribute('src', '/static/img/unkown.png');
                statusPill.style.backgroundColor = "gray";
                break;
            case "Starting":
                statusPill.style.backgroundColor = "#00876a";
                break;
            case "Running":
                imageElement.setAttribute('src', '/static/img/running.apng');
                statusPill.style.backgroundColor = "#07a889";
                break;
            case "Completed":
                statusPill.style.backgroundColor = "#00876a";
                break;
            case "Inspection":
                imageElement.setAttribute('src', '/static/img/maintenance.png');
                statusPill.style.backgroundColor = "#FBC02D";
                machineElement.classList.add('inspection');
                break;
            case "Maintenance":
                imageElement.setAttribute('src', '/static/img/maintenance.png');
                statusPill.style.backgroundColor = "#DD3736";
                machineElement.classList.add('maintenance');
                break;
            case "Reloading":
                imageElement.setAttribute('src', '/static/img/reload.apng');
                statusPill.style.backgroundColor = "#00876a";
                break;
            default:
                imageElement.setAttribute('src', '/static/img/unknown.png');
                statusPill.style.backgroundColor = "gray";
                break;
        }
    }

    clearCharts() {
        this.vibrationCharts.forEach(chart => {
            chart.data.datasets[0].data = [];
            chart.update();
        });
    }
}

// const dashboard = new MachineDashboard();

const logger = className => {
    return new Proxy(new className(), {
        get: function (target, name, receiver) {
            if (!target.hasOwnProperty(name)) {
                if (typeof target[name] === "function") {
                    console.log(
                        "Calling Method : ",
                        name,
                        "|| on : ",
                        target.constructor.name
                    );
                }
                return new Proxy(target[name], this);
            }
            return Reflect.get(target, name, receiver);
        }
    });
};



const dashboard = logger(MachineDashboard)