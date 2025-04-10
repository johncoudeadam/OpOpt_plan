"""
Test script for the rail optimization model.

This script generates dummy data and runs the optimization model.
"""
import time
from rail_optimizer.core.data_generator import generate_dummy_data, generate_data_summary
from rail_optimizer.core.optimizer import solve_rail_optimization, print_optimization_results

def main():
    """Generate dummy data and run the optimization model."""
    # Set a fixed seed for reproducibility
    seed = 42
    
    # Generate the dummy data
    print("Generating dummy data...")
    data = generate_dummy_data(
        num_vehicles=10,
        num_depots=2,
        num_parkings=2,
        num_routes_per_day=8,
        planning_days=14,
        seed=seed
    )
    
    # Generate and save a summary of the input data
    generate_data_summary(data)
    
    # Print summary of generated data
    print("\nData Summary:")
    print(f"- Vehicles: {len(data['vehicles'])}")
    print(f"- Locations: {len(data['locations'])} (Depots: {sum(1 for loc in data['locations'].values() if loc['type'] == 'depot')}, "
          f"Parkings: {sum(1 for loc in data['locations'].values() if loc['type'] == 'parking')})")
    print(f"- Maintenance Types: {len(data['maintenance_types'])} (Preventive: {sum(1 for m in data['maintenance_types'] if m['type'] == 'preventive')}, "
          f"Corrective: {sum(1 for m in data['maintenance_types'] if m['type'] == 'corrective')})")
    print(f"- Routes: {len(data['routes'])}")
    
    # Run the optimization model
    print("\nSolving optimization model...")
    start_time = time.time()
    results = solve_rail_optimization(data, time_limit_seconds=60)
    end_time = time.time()
    
    # Print results
    print_optimization_results(results)
    print(f"Total execution time: {end_time - start_time:.2f} seconds")
    
    # Print expected status message
    print("\nNote: At this stage, expect 'UNKNOWN' or possibly 'FEASIBLE' status as there are no constraints yet.")

if __name__ == "__main__":
    main()
