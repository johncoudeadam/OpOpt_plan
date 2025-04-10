"""
Routes for the Rail Operations & Maintenance Optimizer web application.

This module defines the API endpoints for the web interface.
"""
from flask import jsonify, request
from webapp.app import app

@app.route('/api/optimize', methods=['POST'])
def optimize():
    """
    API endpoint to run the optimization model.
    
    Expected JSON payload:
    {
        "num_vehicles": 10,
        "num_depots": 2,
        "num_parkings": 2,
        "num_routes_per_day": 8,
        "planning_days": 14,
        "seed": 42
    }
    
    Returns:
        JSON response with optimization results
    """
    # Get parameters from request
    data = request.get_json()
    
    # Default parameters
    params = {
        'num_vehicles': 10,
        'num_depots': 2,
        'num_parkings': 2,
        'num_routes_per_day': 8,
        'planning_days': 14,
        'seed': 42
    }
    
    # Update with provided parameters
    if data:
        params.update(data)
    
    # Import the optimization module
    from rail_optimizer.core.data_generator import generate_dummy_data, generate_data_summary
    from rail_optimizer.core.optimizer import solve_rail_optimization, print_optimization_results
    
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
    results = solve_rail_optimization(dummy_data, time_limit_seconds=60)
    
    # Return the results
    return jsonify(results)

@app.route('/api/data', methods=['GET'])
def get_data():
    """
    API endpoint to get the current data.
    
    Returns:
        JSON response with the current data
    """
    import json
    import os
    
    # Check if data summary exists
    summary_path = os.path.join('output', 'data_summary.json')
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    else:
        return jsonify({
            'error': 'Data not found',
            'message': 'No data summary available. Run the optimization first.'
        }), 404 