"""
Flask application for the Rail Operations & Maintenance Optimizer.

This module sets up the Flask application and defines routes for the web interface.
"""
import os
import json
from flask import Flask, render_template, jsonify, request

# Create the Flask application
app = Flask(__name__)

# Import routes after app creation to avoid circular imports
from webapp import routes

@app.route('/')
def index():
    """Render the main page of the application."""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """API endpoint to check the status of the application."""
    return jsonify({
        'status': 'ok',
        'message': 'Rail Operations & Maintenance Optimizer API is running'
    })

@app.route('/run_optimizer', methods=['POST'])
def run_optimizer():
    """
    API endpoint to run the optimization model.
    
    Request Parameters (optional):
    - num_vehicles: Number of vehicles (default: 10)
    - num_depots: Number of depots (default: 2)
    - num_parkings: Number of parkings (default: 2)
    - num_routes_per_day: Number of routes per day (default: 8)
    - planning_days: Number of planning days (default: 14)
    - seed: Random seed (default: 42)
    - time_limit: Time limit in seconds (default: 60)
    - use_cached: Whether to use cached results from schedule_results.json (default: true)
    - regenerate: Whether to generate new data (default: false)
    
    Returns:
        JSON response with optimization results or error message
    """
    try:
        # Get parameters from request
        data = request.get_json() or {}
        
        # Default parameters
        params = {
            'num_vehicles': 5,
            'num_depots': 2,
            'num_parkings': 2,
            'num_routes_per_day': 8,
            'planning_days': 7,
            'seed': 42,
            'time_limit': 60,
            'use_cached': True,
            'regenerate': False
        }
        
        # Update with provided parameters
        params.update(data)
        
        # Path to the cached results file
        results_file = os.path.join('output', 'schedule_results.json')
        
        # Check if we should generate new data or use cached results
        if params['regenerate']:
            # Import the optimization module
            from rail_optimizer.core.data_generator import generate_dummy_data, generate_data_summary
            from rail_optimizer.core.optimizer import solve_rail_optimization
            
            # Generate dummy data
            dummy_data = generate_dummy_data(
                num_vehicles=params['num_vehicles'],
                num_depots=params['num_depots'],
                num_parkings=params['num_parkings'],
                num_routes_per_day=params['num_routes_per_day'],
                planning_days=params['planning_days'],
                seed=params['seed']
            )
            
            # Generate data summary
            generate_data_summary(dummy_data)
            
            # Run the optimization model
            results = solve_rail_optimization(dummy_data, time_limit_seconds=params['time_limit'])
            
            # Save the results to the schedule_results.json file
            os.makedirs('output', exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
        elif params['use_cached'] and os.path.exists(results_file):
            # Load the pre-computed results
            with open(results_file, 'r') as f:
                results = json.load(f)
        else:
            # Run the optimization from scratch
            from rail_optimizer.core.data_generator import generate_dummy_data, generate_data_summary
            from rail_optimizer.core.optimizer import solve_rail_optimization
            
            # Generate dummy data
            dummy_data = generate_dummy_data(
                num_vehicles=params['num_vehicles'],
                num_depots=params['num_depots'],
                num_parkings=params['num_parkings'],
                num_routes_per_day=params['num_routes_per_day'],
                planning_days=params['planning_days'],
                seed=params['seed']
            )
            
            # Generate data summary
            generate_data_summary(dummy_data)
            
            # Run the optimization model
            results = solve_rail_optimization(dummy_data, time_limit_seconds=params['time_limit'])
        
        # Format the results for the frontend
        frontend_results = format_results_for_frontend(results)
        
        # Return the results
        return jsonify(frontend_results)
    
    except Exception as e:
        # Log the error
        app.logger.error(f"Error in run_optimizer: {str(e)}")
        
        # Return error response
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'An error occurred while running the optimization'
        }), 500

def format_results_for_frontend(results):
    """
    Format the optimization results for the frontend visualization.
    
    Args:
        results: Raw optimization results from schedule_results.json
        
    Returns:
        Formatted results for the frontend
    """
    # Get optimization info
    if 'optimization_info' in results:
        status = results['optimization_info'].get('status', 'OPTIMAL')
        wall_time = results['optimization_info'].get('wall_time', 0)
        objective_value = results['optimization_info'].get('objective_value', 0)
    else:
        status = 'OPTIMAL'
        wall_time = 0.6
        objective_value = 0
    
    # Count total routes and maintenance activities
    total_routes = 0
    total_maintenance = 0
    
    vehicles_data = {}
    
    if 'vehicles' in results:
        for vehicle_id, vehicle_data in results['vehicles'].items():
            # Initialize vehicle in the output format
            vehicles_data[vehicle_id] = {
                'routes': {},
                'maintenance': {},
                'initial_km': vehicle_data.get('initial_state', {}).get('km', 0)
            }
            
            # Process route assignments
            route_assignments = vehicle_data.get('route_assignments', {})
            for shift_key, route_data in route_assignments.items():
                if route_data:  # Skip null routes
                    # Parse shift (e.g., "1_day" or "1_night")
                    parts = shift_key.split('_')
                    day = int(parts[0])
                    is_day = parts[1] == 'day'
                    shift_index = (day - 1) * 2 + (0 if is_day else 1)
                    
                    # Add route to the vehicle data
                    vehicles_data[vehicle_id]['routes'][shift_key] = {
                        'route_id': route_data.get('route_id', ''),
                        'start_location': route_data.get('start_location', ''),
                        'end_location': route_data.get('end_location', ''),
                        'km': route_data.get('distance_km', 0),
                        'shift': shift_index
                    }
                    
                    total_routes += 1
            
            # Process maintenance activities
            maintenance_activities = vehicle_data.get('maintenance_activities', [])
            for i, maintenance in enumerate(maintenance_activities):
                # Create a unique ID for each maintenance activity
                maint_id = f"{maintenance.get('maintenance_id', '')}_activity_{i}"
                
                # Parse shift data
                start_day = maintenance.get('start_day', 1)
                start_shift = maintenance.get('start_shift', 'day')
                end_day = maintenance.get('end_day', 1)
                end_shift = maintenance.get('end_shift', 'day')
                
                # Convert to shift indices
                start_shift_index = (start_day - 1) * 2 + (0 if start_shift == 'day' else 1)
                end_shift_index = (end_day - 1) * 2 + (0 if end_shift == 'day' else 1)
                
                # Add maintenance to the vehicle data
                vehicles_data[vehicle_id]['maintenance'][maint_id] = {
                    'maintenance_type': maintenance.get('maintenance_type', ''),
                    'start_shift': start_shift_index,
                    'end_shift': end_shift_index,
                    'depot': maintenance.get('depot', ''),
                    'km': maintenance.get('km_at_start', 0)
                }
                
                total_maintenance += 1
    
    # Create the final output structure
    frontend_results = {
        'status': status,
        'objective_value': objective_value,
        'wall_time': wall_time,
        'vehicles': vehicles_data,
        'total_routes': total_routes,
        'total_maintenance': total_maintenance
    }
    
    return frontend_results

if __name__ == '__main__':
    app.run(debug=True) 