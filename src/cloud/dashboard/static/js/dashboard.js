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
});

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
    }
}