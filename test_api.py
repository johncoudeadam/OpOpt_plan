#!/usr/bin/env python
"""
Test script for the Rail Operations & Maintenance Optimizer API endpoints.
"""
import requests
import json
import time

def test_run_optimizer():
    """Test the /run_optimizer endpoint."""
    print("Testing /run_optimizer endpoint...")
    
    url = "http://127.0.0.1:5000/run_optimizer"
    
    # Prepare smaller test data for faster response
    payload = {
        "num_vehicles": 5,
        "num_depots": 2,
        "num_parkings": 1,
        "num_routes_per_day": 4,
        "planning_days": 7,
        "time_limit": 30
    }
    
    # Print request
    print(f"Request URL: {url}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    # Send request
    start_time = time.time()
    try:
        response = requests.post(url, json=payload)
        
        # Print response status
        print(f"Response status: {response.status_code}")
        
        # Print response time
        end_time = time.time()
        print(f"Response time: {end_time - start_time:.2f} seconds")
        
        # Print response headers
        print("Response headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        # Print response content summary
        if response.status_code == 200:
            data = response.json()
            print("\nResponse content summary:")
            print(f"  Status: {data.get('status', 'N/A')}")
            print(f"  Objective value: {data.get('objective_value', 'N/A')}")
            
            # Print vehicles summary if available
            if 'vehicles' in data:
                print(f"  Number of vehicles: {len(data['vehicles'])}")
                
            # Print first vehicle details if available
            if 'vehicles' in data and len(data['vehicles']) > 0:
                vehicle_id = list(data['vehicles'].keys())[0]
                vehicle = data['vehicles'][vehicle_id]
                print(f"\nSample vehicle ({vehicle_id}) schedule:")
                
                # Print route assignments
                if 'routes' in vehicle:
                    print(f"  Routes assigned: {len(vehicle['routes'])}")
                
                # Print maintenance activities
                if 'maintenance' in vehicle:
                    print(f"  Maintenance activities: {len(vehicle['maintenance'])}")
        else:
            # Print error response
            print("\nError response:")
            print(response.text)
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_run_optimizer() 