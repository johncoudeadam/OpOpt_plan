"""
Test script for data generation.

This script calls the generate_dummy_data function and prints the output as JSON.
"""
import json
import sys
from core.data_generator import generate_dummy_data, save_dummy_data

def main():
    """Generate dummy data and print it as JSON."""
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
    
    # Print summary of generated data
    print("\nGenerated Data Summary:")
    print(f"- Vehicles: {len(data['vehicles'])}")
    print(f"- Locations: {len(data['locations'])} (Depots: {sum(1 for loc in data['locations'].values() if loc['type'] == 'depot')}, "
          f"Parkings: {sum(1 for loc in data['locations'].values() if loc['type'] == 'parking')})")
    print(f"- Maintenance Types: {len(data['maintenance_types'])} (Preventive: {sum(1 for m in data['maintenance_types'] if m['type'] == 'preventive')}, "
          f"Corrective: {sum(1 for m in data['maintenance_types'] if m['type'] == 'corrective')})")
    print(f"- Routes: {len(data['routes'])}")
    
    # Save data to file if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--save':
        output_file = 'dummy_data.json'
        save_dummy_data(data, output_file)
        print(f"\nData saved to {output_file}")
    
    # Print the full data as JSON
    print("\nFull Data (JSON format):")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
