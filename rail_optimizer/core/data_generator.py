"""
Data generator module for the Rail Operations & Maintenance Optimizer.

This module provides functions to generate dummy test data for the optimization model.
"""
import random
import json
from typing import Dict, List, Any, Tuple, Optional

def generate_dummy_data(
    num_vehicles: int = 10,
    num_depots: int = 2,
    num_parkings: int = 2,
    num_routes_per_day: int = 8,
    planning_days: int = 14,
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate dummy data for the Rail Operations & Maintenance Optimizer.
    
    Args:
        num_vehicles: Number of vehicles in the fleet
        num_depots: Number of depot locations
        num_parkings: Number of parking locations
        num_routes_per_day: Number of routes per day shift
        planning_days: Number of days in the planning horizon
        seed: Random seed for reproducibility
        
    Returns:
        Dictionary containing the generated data with the following keys:
        - vehicles: List of vehicle data
        - locations: Dict of depot and parking locations with capacities
        - maintenance_types: List of maintenance activity definitions
        - routes: List of route definitions
    """
    if seed is not None:
        random.seed(seed)
    
    # Generate locations (depots and parkings)
    locations = _generate_locations(num_depots, num_parkings)
    
    # Generate maintenance types (preventive and corrective)
    maintenance_types = _generate_maintenance_types(locations)
    
    # Generate vehicles with initial state
    vehicles = _generate_vehicles(num_vehicles, locations, maintenance_types)
    
    # Generate routes for each day
    routes = _generate_routes(num_routes_per_day, planning_days, locations)
    
    # Validate the generated data
    _validate_data(vehicles, locations, maintenance_types, routes)
    
    return {
        "vehicles": vehicles,
        "locations": locations,
        "maintenance_types": maintenance_types,
        "routes": routes
    }

def _generate_locations(num_depots: int, num_parkings: int) -> Dict[str, Dict[str, Any]]:
    """Generate depot and parking locations with capacities."""
    locations = {}
    
    # Generate depots
    for i in range(num_depots):
        depot_id = f"depot_{i+1}"
        locations[depot_id] = {
            "type": "depot",
            "capacity": random.randint(10, 15),
            "manhours_per_shift": random.randint(40, 100),
            "specialized_maintenance": []
        }
    
    # Assign some specialized maintenance capabilities to depots
    maintenance_specializations = [
        "electrical", "mechanical", "hydraulic", "pneumatic", "structural"
    ]
    
    for depot in locations.values():
        if depot["type"] == "depot":
            # Each depot can handle 1-3 specialized maintenance types
            num_specializations = random.randint(1, 3)
            depot["specialized_maintenance"] = random.sample(
                maintenance_specializations, num_specializations
            )
    
    # Generate parkings
    for i in range(num_parkings):
        parking_id = f"parking_{i+1}"
        locations[parking_id] = {
            "type": "parking",
            "capacity": random.randint(10, 20),
        }
    
    return locations

def _generate_maintenance_types(locations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate preventive and corrective maintenance types."""
    maintenance_types = []
    
    # Get all specializations from depots
    all_specializations = set()
    for loc in locations.values():
        if loc["type"] == "depot":
            all_specializations.update(loc["specialized_maintenance"])
    
    all_specializations = list(all_specializations)
    
    # Generate preventive maintenance types
    preventive_types = [
        {
            "id": f"preventive_{i+1}",
            "type": "preventive",
            "optimal_km": random.randint(5000, 20000),
            "max_km": lambda opt_km: opt_km + random.randint(1000, 3000),
            "manhours": random.randint(4, 24),
            "specialization": random.choice(all_specializations) if all_specializations and random.random() < 0.7 else None
        }
        for i in range(5)  # 5 preventive maintenance types
    ]
    
    # Fix the max_km values
    for maint in preventive_types:
        maint["max_km"] = maint["max_km"](maint["optimal_km"])
    
    # Generate corrective maintenance types
    corrective_types = [
        {
            "id": f"corrective_{i+1}",
            "type": "corrective",
            "max_km_window": random.randint(300, 1000),
            "manhours": random.randint(2, 16),
            "specialization": random.choice(all_specializations) if all_specializations and random.random() < 0.5 else None,
            "safety_critical": random.random() < 0.3  # 30% chance of being safety-critical
        }
        for i in range(5)  # 5 corrective maintenance types
    ]
    
    maintenance_types = preventive_types + corrective_types
    return maintenance_types

def _generate_vehicles(
    num_vehicles: int, 
    locations: Dict[str, Dict[str, Any]], 
    maintenance_types: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate vehicles with initial state."""
    vehicles = []
    
    # Get all location IDs
    location_ids = list(locations.keys())
    
    # Get corrective maintenance types
    corrective_types = [m for m in maintenance_types if m["type"] == "corrective"]
    
    for i in range(num_vehicles):
        # Random initial location
        initial_location = random.choice(location_ids)
        
        # Random initial km (between 0 and 25000)
        initial_km = random.randint(0, 25000)
        
        # Generate pending corrective tasks (0-2 per vehicle)
        pending_tasks = []
        num_pending_tasks = random.randint(0, 2)
        
        for _ in range(num_pending_tasks):
            corrective_type = random.choice(corrective_types)
            
            # Calculate remaining km window
            remaining_km = random.randint(50, corrective_type["max_km_window"])
            
            pending_tasks.append({
                "maintenance_type_id": corrective_type["id"],
                "remaining_km": remaining_km
            })
        
        vehicle = {
            "id": f"vehicle_{i+1}",
            "initial_location": initial_location,
            "initial_km": initial_km,
            "pending_corrective_tasks": pending_tasks
        }
        
        vehicles.append(vehicle)
    
    return vehicles

def _generate_routes(
    num_routes_per_day: int, 
    planning_days: int, 
    locations: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate routes for each day in the planning horizon."""
    routes = []
    
    # Get all location IDs
    location_ids = list(locations.keys())
    
    for day in range(planning_days):
        for route_num in range(num_routes_per_day):
            # Random start and end locations
            start_location = random.choice(location_ids)
            end_location = random.choice(location_ids)
            
            # Random route distance (50-300 km)
            distance_km = random.randint(50, 300)
            
            route = {
                "id": f"route_day{day+1}_{route_num+1}",
                "day": day + 1,
                "shift": "day",  # All routes are for day shift
                "start_location": start_location,
                "end_location": end_location,
                "distance_km": distance_km
            }
            
            routes.append(route)
    
    return routes

def _validate_data(
    vehicles: List[Dict[str, Any]],
    locations: Dict[str, Dict[str, Any]],
    maintenance_types: List[Dict[str, Any]],
    routes: List[Dict[str, Any]]
) -> None:
    """Validate the generated data for consistency."""
    # Check that all vehicle initial locations exist
    location_ids = set(locations.keys())
    for vehicle in vehicles:
        if vehicle["initial_location"] not in location_ids:
            raise ValueError(f"Vehicle {vehicle['id']} has invalid initial location: {vehicle['initial_location']}")
    
    # Check that all route start/end locations exist
    for route in routes:
        if route["start_location"] not in location_ids:
            raise ValueError(f"Route {route['id']} has invalid start location: {route['start_location']}")
        if route["end_location"] not in location_ids:
            raise ValueError(f"Route {route['id']} has invalid end location: {route['end_location']}")
    
    # Check that all pending maintenance tasks reference valid maintenance types
    maintenance_type_ids = {m["id"] for m in maintenance_types}
    for vehicle in vehicles:
        for task in vehicle["pending_corrective_tasks"]:
            if task["maintenance_type_id"] not in maintenance_type_ids:
                raise ValueError(f"Vehicle {vehicle['id']} has invalid maintenance type: {task['maintenance_type_id']}")
    
    # Check that specialized maintenance types have at least one capable depot
    for maint_type in maintenance_types:
        if maint_type.get("specialization"):
            capable_depots = [
                depot_id for depot_id, depot in locations.items()
                if depot["type"] == "depot" and maint_type["specialization"] in depot.get("specialized_maintenance", [])
            ]
            if not capable_depots:
                raise ValueError(f"Maintenance type {maint_type['id']} with specialization {maint_type['specialization']} has no capable depots")

def save_dummy_data(data: Dict[str, Any], filepath: str) -> None:
    """Save the generated dummy data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_dummy_data(filepath: str) -> Dict[str, Any]:
    """Load dummy data from a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)
