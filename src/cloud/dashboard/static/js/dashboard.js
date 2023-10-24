window.activeMachine = null;

const socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('factory_machine_status', function (data) {
    // Update the status of the specific machine
    updateMachineStatus(data.machine_id, data.status);
});

socket.on('initial-status', function (data) {
    // Handle the initial statuses here
    for (let machine_id in data) {
        updateMachineStatus(machine_id, data[machine_id]);
    }
    if (window.activeMachine) {
        toggleMachineData(window.activeMachine);
    }
});

function toggleMachineData(machine_id) {
    let machineElement = document.getElementById(machine_id);

    // Remove 'active' class from all machines
    let machines = document.querySelectorAll('.machine');
    machines.forEach(function (machine) {
        machine.classList.remove('active');
    });

    if (window.activeMachine && window.activeMachine === machine_id) {
        window.activeMachine = null;  // If the machine is toggled off, set the activeMachine to null
    } else {
        window.activeMachine = machine_id;  // If a new machine is toggled on, set the activeMachine
        machineElement.classList.add('active');
    }
    // Toggle placeholder visibility based on the active machine status
    togglePlaceholderVisibility();

    socket.emit('toggle-machine-data', { machine_id: machine_id });
}

function togglePlaceholderVisibility() {
    let placeholder = document.querySelector('.chart-placeholder');

    // If no chart is visible and there's no active machine, show the placeholder
    if (!window.activeMachine) {
        placeholder.style.display = "block";
    } else {
        placeholder.style.display = "none";
    }
}

function updateMachineStatus(machine_id, status) {
    // Find the specific machine element by its ID
    let machineElement = document.getElementById(machine_id);
    if (machineElement) {
        // Get the image and status pill elements
        let imageElement = machineElement.querySelector('img');
        let statusPill = machineElement.querySelector('.status-pill');

        // Set status text
        statusPill.textContent = status;

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

        if (status === "Starting" && machine_id === window.activeMachine) {
            vibrationChartX.data.datasets[0].data = [];
            vibrationChartY.data.datasets[0].data = [];
            vibrationChartZ.data.datasets[0].data = [];
            vibrationChartX.update();
            vibrationChartY.update();
            vibrationChartZ.update();
        }
    }
}

socket.on('start-chart', function () {
    vibrationChartX.data.datasets[0].data = [];
    vibrationChartY.data.datasets[0].data = [];
    vibrationChartZ.data.datasets[0].data = [];
    vibrationChartX.options.plugins.title.text = 'Vibration X for ' + window.activeMachine;
    vibrationChartY.options.plugins.title.text = 'Vibration Y for ' + window.activeMachine;
    vibrationChartZ.options.plugins.title.text = 'Vibration Z for ' + window.activeMachine;

    vibrationChartX.update();
    vibrationChartY.update();
    vibrationChartZ.update();

    document.getElementById("vibrationChartX").style.visibility = "visible";
    document.getElementById("vibrationChartY").style.visibility = "visible";
    document.getElementById("vibrationChartZ").style.visibility = "visible";
});

socket.on('stop-chart', function () {
    vibrationChartX.data.datasets[0].data = [];
    vibrationChartY.data.datasets[0].data = [];
    vibrationChartZ.data.datasets[0].data = [];

    document.getElementById("vibrationChartX").style.visibility = "hidden";
    document.getElementById("vibrationChartY").style.visibility = "hidden";
    document.getElementById("vibrationChartZ").style.visibility = "hidden";
});

socket.on('update-chart', function (data) {
    if (window.activeMachine === null) {
        socket.emit('toggle-machine-data', { machine_id: data.machine_id });
    } else {
        if (data.machine_id !== window.activeMachine) {
            socket.emit('toggle-machine-data', { machine_id: window.activeMachine });
        }
    }

    for (let i = 0; i < data.vibration_data.length; i++) {
        xyz = data.vibration_data[i];
        j = data.sequence_start + i
        vibrationChartX.data.datasets[0].data.push({ x: j, y: xyz[0] });
        vibrationChartY.data.datasets[0].data.push({ x: j, y: xyz[1] });
        vibrationChartZ.data.datasets[0].data.push({ x: j, y: xyz[2] });
    }
    vibrationChartX.update();
    vibrationChartY.update();
    vibrationChartZ.update();
});

let vibrationChartX = new Chart(document.getElementById("vibrationChartX"), {
    type: 'line',
    data: {
        datasets: [{
            borderColor: "#07a889",
            borderWidth: 1,
            pointRadius: 0, // disable for a single dataset
            data: []
        }]
    }, options: {
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
                max: 50000,
            },
            y: {
                min: -2500,
                max: 2500,
            }
        },
        plugins: {
            legend: {
                display: false,
            },
            title: {
                display: true,
                text: 'Vibration Data',
            }
        }
    }
});
let vibrationChartY = new Chart(document.getElementById("vibrationChartY"), {
    type: 'line',
    data: {
        datasets: [{
            borderColor: "#07a889",
            borderWidth: 1,
            pointRadius: 0, // disable for a single dataset
            data: []
        }]
    }, options: {
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
                max: 50000,
            },
            y: {
                min: -2500,
                max: 2500,
            }
        },
        plugins: {
            legend: {
                display: false,
            },
            title: {
                display: true,
                text: 'Vibration Data',
            }
        }
    }
});
let vibrationChartZ = new Chart(document.getElementById("vibrationChartZ"), {
    type: 'line',
    data: {
        datasets: [{
            borderColor: "#07a889",
            borderWidth: 1,
            pointRadius: 0, // disable for a single dataset
            data: []
        }]
    }, options: {
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
                max: 50000,
            },
            y: {
                min: -2500,
                max: 2500,
            }
        },
        plugins: {
            legend: {
                display: false,
            },
            title: {
                display: true,
                text: 'Vibration Data',
            }
        }
    }
});