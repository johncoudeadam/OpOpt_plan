/**
 * Visualization module for Rail Operations & Maintenance Optimizer
 * 
 * Handles API calls to the optimizer and renders the schedule visualization.
 */

/**
 * Run the optimization and display results
 * @param {boolean} useCached - Whether to use cached results (default: true)
 * @param {boolean} regenerate - Whether to regenerate data (default: false)
 */
function runOptimization(useCached = true, regenerate = false) {
    const resultContainer = document.getElementById('optimization-results');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    // Show loading spinner
    if (loadingSpinner) {
        loadingSpinner.style.display = 'block';
    }
    
    // Clear previous results
    if (resultContainer) {
        resultContainer.innerHTML = '<div class="alert alert-info">Running optimization...</div>';
    }
    
    // Default parameters for the optimization
    const params = {
        num_vehicles: 5,        // Smaller dataset for faster response
        num_depots: 2,
        num_parkings: 1,
        num_routes_per_day: 4,
        planning_days: 7,
        time_limit: 30,         // 30 seconds time limit
        use_cached: useCached,  // Whether to use cached results
        regenerate: regenerate  // Whether to regenerate data
    };
    
    // Make API call to run the optimizer
    fetch('/run_optimizer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(params)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Hide loading spinner
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
        
        // Check if we have valid data
        if (!data || data.status === 'error') {
            if (resultContainer) {
                resultContainer.innerHTML = `
                    <div class="alert alert-warning">
                        <h4>Optimization Failed</h4>
                        <p>${data && data.message ? data.message : 'Unknown error occurred'}</p>
                    </div>
                `;
            }
            return;
        }
        
        // Display the results
        displayResults(data, resultContainer);
    })
    .catch(error => {
        // Hide loading spinner
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
        
        // Display error message
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h4>Error Running Optimization</h4>
                    <p>${error.message}</p>
                </div>
            `;
        }
        console.error('Error:', error);
    });
}

/**
 * Display the optimization results in the provided container
 */
function displayResults(data, container) {
    if (!container) return;
    
    // Check if we have valid data
    if (!data || data.status === 'error') {
        container.innerHTML = `
            <div class="alert alert-warning">
                <h4>Optimization Failed</h4>
                <p>${data && data.message ? data.message : 'Unknown error occurred'}</p>
            </div>
        `;
        return;
    }
    
    // Create results container
    let html = `
        <div class="optimization-summary card mb-4">
            <div class="card-header bg-primary text-white">
                <h3 class="mb-0">Optimization Results</h3>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Status:</strong> ${data.status}</p>
                        <p><strong>Objective Value:</strong> ${data.objective_value !== undefined ? data.objective_value : 'N/A'}</p>
                        <p><strong>Wall Time:</strong> ${data.wall_time !== undefined ? data.wall_time.toFixed(2) + ' seconds' : 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Vehicles:</strong> ${data.vehicles ? Object.keys(data.vehicles).length : 0}</p>
                        <p><strong>Routes Assigned:</strong> ${data.total_routes || 'N/A'}</p>
                        <p><strong>Maintenance Activities:</strong> ${data.total_maintenance !== undefined ? data.total_maintenance : 'N/A'}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add visualization section
    html += `
        <div class="card mb-4">
            <div class="card-header">
                <h3 class="mb-0">Schedule Visualization</h3>
            </div>
            <div class="card-body">
                <div class="schedule-visualization">
                    ${createScheduleVisualization(data)}
                </div>
            </div>
        </div>
    `;
    
    // Add vehicle details section
    html += `
        <div class="card">
            <div class="card-header">
                <h3 class="mb-0">Vehicle Details</h3>
            </div>
            <div class="card-body">
                <div class="accordion" id="vehicleAccordion">
                    ${createVehicleAccordion(data)}
                </div>
            </div>
        </div>
    `;
    
    // Update the container with the results
    container.innerHTML = html;
    
    // Initialize any Bootstrap components
    initializeBootstrapComponents();
}

/**
 * Create a schedule visualization for the optimization results
 */
function createScheduleVisualization(data) {
    if (!data || !data.vehicles) {
        return '<div class="alert alert-warning">No vehicle data available for visualization</div>';
    }
    
    // Create timeline headers (shifts)
    const totalShifts = getTotalShifts(data);
    const shiftLabels = generateShiftLabels(totalShifts);
    
    let html = `
        <div class="schedule-container">
            <div class="timeline-header">
                <div class="vehicle-header">Vehicle</div>
                ${shiftLabels.map(label => `<div class="shift-header">${label}</div>`).join('')}
            </div>
    `;
    
    // Create timeline for each vehicle
    const vehicleIds = Object.keys(data.vehicles);
    vehicleIds.forEach(vehicleId => {
        const vehicle = data.vehicles[vehicleId];
        
        html += `
            <div class="timeline-row">
                <div class="vehicle-label">${vehicleId}</div>
                ${createVehicleTimeline(vehicle, totalShifts)}
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

/**
 * Get the total number of shifts from the data
 */
function getTotalShifts(data) {
    if (!data || !data.vehicles) return 0;
    
    let maxShift = 0;
    Object.values(data.vehicles).forEach(vehicle => {
        // Check routes
        if (vehicle.routes) {
            Object.values(vehicle.routes).forEach(route => {
                if (route.shift > maxShift) maxShift = route.shift;
            });
        }
        
        // Check maintenance
        if (vehicle.maintenance) {
            Object.values(vehicle.maintenance).forEach(maintenance => {
                if (maintenance.end_shift > maxShift) maxShift = maintenance.end_shift;
            });
        }
    });
    
    return maxShift + 1; // +1 because shifts are zero-indexed
}

/**
 * Generate shift labels (Day 1 - Day N, Night 1 - Night N)
 */
function generateShiftLabels(totalShifts) {
    const labels = [];
    for (let i = 0; i < totalShifts; i++) {
        const day = Math.floor(i / 2) + 1;
        const isDay = i % 2 === 0;
        labels.push(`${isDay ? 'Day' : 'Night'} ${day}`);
    }
    return labels;
}

/**
 * Create a timeline for a single vehicle
 */
function createVehicleTimeline(vehicle, totalShifts) {
    let timeline = '';
    
    // Create cells for each shift
    for (let shift = 0; shift < totalShifts; shift++) {
        // Default empty cell
        let cellContent = '&nbsp;';
        let cellClass = 'empty-shift';
        
        // Check if there's a route assignment for this shift
        if (vehicle.routes) {
            const routeForShift = Object.values(vehicle.routes).find(r => r.shift === shift);
            if (routeForShift) {
                cellContent = `Route: ${routeForShift.route_id}`;
                cellClass = 'route-shift';
            }
        }
        
        // Check if there's maintenance for this shift
        if (vehicle.maintenance) {
            const maintenanceForShift = Object.values(vehicle.maintenance).find(
                m => shift >= m.start_shift && shift <= m.end_shift
            );
            
            if (maintenanceForShift) {
                cellContent = `Maint: ${maintenanceForShift.maintenance_type}`;
                cellClass = maintenanceForShift.maintenance_type.includes('preventive') 
                    ? 'preventive-maintenance-shift' 
                    : 'corrective-maintenance-shift';
            }
        }
        
        timeline += `<div class="shift-cell ${cellClass}" title="${cellContent}">${cellContent}</div>`;
    }
    
    return timeline;
}

/**
 * Create accordion for detailed vehicle data
 */
function createVehicleAccordion(data) {
    if (!data || !data.vehicles) {
        return '<div class="alert alert-warning">No vehicle data available</div>';
    }
    
    let html = '';
    const vehicleIds = Object.keys(data.vehicles);
    
    vehicleIds.forEach((vehicleId, index) => {
        const vehicle = data.vehicles[vehicleId];
        
        html += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading${index}">
                    <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#collapse${index}" aria-expanded="${index === 0}" aria-controls="collapse${index}">
                        ${vehicleId} - Routes: ${vehicle.routes ? Object.keys(vehicle.routes).length : 0}, 
                        Maintenance: ${vehicle.maintenance ? Object.keys(vehicle.maintenance).length : 0}
                    </button>
                </h2>
                <div id="collapse${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" 
                     aria-labelledby="heading${index}" data-bs-parent="#vehicleAccordion">
                    <div class="accordion-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h4>Routes</h4>
                                ${createRoutesTable(vehicle)}
                            </div>
                            <div class="col-md-6">
                                <h4>Maintenance</h4>
                                ${createMaintenanceTable(vehicle)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    return html;
}

/**
 * Create routes table for a vehicle
 */
function createRoutesTable(vehicle) {
    if (!vehicle.routes || Object.keys(vehicle.routes).length === 0) {
        return '<p>No routes assigned</p>';
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        <th>Shift</th>
                        <th>Route ID</th>
                        <th>From</th>
                        <th>To</th>
                        <th>KM</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    Object.values(vehicle.routes).forEach(route => {
        const day = Math.floor(route.shift / 2) + 1;
        const isDay = route.shift % 2 === 0;
        const shiftLabel = `${isDay ? 'Day' : 'Night'} ${day}`;
        
        html += `
            <tr>
                <td>${shiftLabel}</td>
                <td>${route.route_id}</td>
                <td>${route.start_location || 'N/A'}</td>
                <td>${route.end_location || 'N/A'}</td>
                <td>${route.km !== undefined ? route.km : 'N/A'}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    return html;
}

/**
 * Create maintenance table for a vehicle
 */
function createMaintenanceTable(vehicle) {
    if (!vehicle.maintenance || Object.keys(vehicle.maintenance).length === 0) {
        return '<p>No maintenance scheduled</p>';
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Start Shift</th>
                        <th>End Shift</th>
                        <th>Depot</th>
                        <th>KM</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    Object.values(vehicle.maintenance).forEach(maintenance => {
        const startDay = Math.floor(maintenance.start_shift / 2) + 1;
        const startIsDay = maintenance.start_shift % 2 === 0;
        const startShiftLabel = `${startIsDay ? 'Day' : 'Night'} ${startDay}`;
        
        const endDay = Math.floor(maintenance.end_shift / 2) + 1;
        const endIsDay = maintenance.end_shift % 2 === 0;
        const endShiftLabel = `${endIsDay ? 'Day' : 'Night'} ${endDay}`;
        
        html += `
            <tr>
                <td>${maintenance.maintenance_type || 'N/A'}</td>
                <td>${startShiftLabel}</td>
                <td>${endShiftLabel}</td>
                <td>${maintenance.depot || 'N/A'}</td>
                <td>${maintenance.km !== undefined ? maintenance.km : 'N/A'}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    return html;
}

/**
 * Initialize Bootstrap components
 */
function initializeBootstrapComponents() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Export functions for use in other modules
window.runOptimization = runOptimization; 