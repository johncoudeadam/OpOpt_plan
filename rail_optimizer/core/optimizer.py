"""
Optimizer module for the Rail Operations & Maintenance Optimizer.

This module implements the constraint programming model using Google OR-Tools.
"""
from typing import Dict, List, Any, Tuple, Optional
from ortools.sat.python import cp_model

def solve_rail_optimization(data: Dict[str, Any], time_limit_seconds: int = 60) -> Dict[str, Any]:
    """
    Solve the rail operations and maintenance optimization problem.
    
    Args:
        data: Dictionary containing the input data (vehicles, locations, maintenance_types, routes)
        time_limit_seconds: Time limit for the solver in seconds
        
    Returns:
        Dictionary containing the optimization results
    """
    # Extract data
    vehicles = data["vehicles"]
    locations = data["locations"]
    maintenance_types = data["maintenance_types"]
    routes = data["routes"]
    
    # Create the CP-SAT model
    model = cp_model.CpModel()
    
    # Track deviation variables for the objective function
    deviation_vars = []
    
    # Define the planning horizon
    planning_days = max(route["day"] for route in routes)
    shifts = ["day", "night"]
    
    # Create a list of all shifts in the planning horizon
    all_shifts = []
    for day in range(1, planning_days + 1):
        for shift in shifts:
            all_shifts.append((day, shift))
    
    # Get routes by day and shift
    routes_by_day_shift = {}
    for day, shift in all_shifts:
        routes_by_day_shift[(day, shift)] = [
            route for route in routes 
            if route["day"] == day and route["shift"] == shift
        ]
    
    # Create variables
    
    # 1. Route assignment variables: assign_vr[v, r] = 1 if vehicle v is assigned to route r
    assign_vr = {}
    for vehicle in vehicles:
        vehicle_id = vehicle["id"]
        for route in routes:
            route_id = route["id"]
            var_name = f"assign_{vehicle_id}_{route_id}"
            assign_vr[(vehicle_id, route_id)] = model.NewBoolVar(var_name)
    
    # 2. Location variables: loc_start_vs[v, s] = location of vehicle v at the start of shift s
    # Create a mapping of location IDs to integers for the integer variables
    location_ids = list(locations.keys())
    location_id_to_index = {loc_id: idx for idx, loc_id in enumerate(location_ids)}
    
    # Create a reverse mapping from indices to location IDs
    index_to_location_id = {idx: loc_id for loc_id, idx in location_id_to_index.items()}
    
    # Create all shifts including the initial state (0)
    all_shifts_with_initial = [(0, "initial")] + all_shifts
    
    # Create a mapping from shift to index for easy lookup
    shift_to_index = {shift: idx for idx, shift in enumerate(all_shifts_with_initial)}
    
    # Create location variables
    loc_start_vs = {}
    for vehicle in vehicles:
        vehicle_id = vehicle["id"]
        for idx, (day, shift) in enumerate(all_shifts_with_initial):
            var_name = f"loc_start_{vehicle_id}_{day}_{shift}"
            # Location variable domain: 0 to len(locations)-1
            loc_start_vs[(vehicle_id, idx)] = model.NewIntVar(0, len(locations) - 1, var_name)
    
    # 3. KM tracking variables: km_at_shift_start[v, s] = accumulated km of vehicle v at the start of shift s
    # Define the maximum possible km (sum of all route distances + initial km)
    max_initial_km = max(vehicle["initial_km"] for vehicle in vehicles)
    max_route_km = sum(route["distance_km"] for route in routes)
    max_possible_km = max_initial_km + max_route_km
    
    # Create KM variables
    km_at_shift_start = {}
    for vehicle in vehicles:
        vehicle_id = vehicle["id"]
        for idx, (day, shift) in enumerate(all_shifts_with_initial):
            var_name = f"km_at_shift_start_{vehicle_id}_{day}_{shift}"
            # KM variable domain: 0 to max_possible_km
            km_at_shift_start[(vehicle_id, idx)] = model.NewIntVar(0, max_possible_km, var_name)
    
    # 4. Maintenance variables
    # Create a list of all potential maintenance instances
    all_maint_instances = []
    
    # Track maintenance variables in dictionaries for easy access
    maint_performed = {}  # Boolean: 1 if maintenance is performed, 0 otherwise
    maint_start_s = {}    # Integer: shift index when maintenance starts
    maint_assigned_depot = {}  # Integer: depot index where maintenance is performed
    km_at_maint_start = {}  # Integer: vehicle km at the start of maintenance
    maint_intervals = {}  # OptionalIntervalVar: represents the maintenance interval
    maint_active_s = {}  # Boolean: 1 if maintenance is active during shift s
    
    # Get depot locations (for maintenance assignment)
    depot_locations = [loc_id for loc_id, loc_data in locations.items() if loc_data["type"] == "depot"]
    depot_indices = [location_id_to_index[loc_id] for loc_id in depot_locations]
    
    # Maximum maintenance duration in shifts (for interval variables)
    max_maint_duration = 5  # Assuming no maintenance takes more than 5 shifts
    
    # For each vehicle and maintenance type, create potential maintenance instances
    for vehicle in vehicles:
        vehicle_id = vehicle["id"]
        
        # For each maintenance type
        for maint_type in maintenance_types:
            maint_id = maint_type["id"]
            maint_type_id = maint_type["type"]  # 'preventive' or 'corrective'
            required_manhours = maint_type["manhours"]  # Field is called 'manhours' in the data generator
            
            # For each potential start shift (excluding the initial state)
            for start_idx, (start_day, start_shift) in enumerate(all_shifts_with_initial[1:], 1):
                # Create a unique ID for this maintenance instance
                instance_id = f"{vehicle_id}_{maint_id}_{start_day}_{start_shift}"
                
                # Add to the list of all maintenance instances
                all_maint_instances.append({
                    "id": instance_id,
                    "vehicle_id": vehicle_id,
                    "maint_id": maint_id,
                    "maint_type": maint_type_id,
                    "start_idx": start_idx,
                    "required_manhours": required_manhours,
                    "specialization": maint_type.get("specialization", None)
                })
                
                # 1. maint_performed: Boolean variable indicating if this maintenance is performed
                var_name = f"maint_performed_{instance_id}"
                maint_performed[instance_id] = model.NewBoolVar(var_name)
                
                # 2. maint_start_s: Integer variable for the shift index when maintenance starts
                # This is fixed to the start_idx for this instance
                maint_start_s[instance_id] = start_idx
                
                # 3. maint_assigned_depot: Integer variable for the depot where maintenance is performed
                var_name = f"maint_assigned_depot_{instance_id}"
                
                # If the maintenance type has a specialization, restrict the domain to capable depots
                specialization = maint_type.get("specialization", None)
                if specialization:
                    # Find depots that can handle this specialization
                    capable_depot_ids = []
                    for loc_id, loc_data in locations.items():
                        if loc_data["type"] == "depot" and specialization in loc_data.get("specialized_maintenance", []):
                            capable_depot_ids.append(loc_id)
                    
                    # Convert capable depot IDs to indices
                    capable_depot_indices = [location_id_to_index[depot_id] for depot_id in capable_depot_ids]
                    
                    # If no capable depots found, use all depots (fallback)
                    if not capable_depot_indices:
                        capable_depot_indices = depot_indices
                    
                    # Create domain from capable depot indices
                    maint_assigned_depot[instance_id] = model.NewIntVarFromDomain(
                        cp_model.Domain.FromValues(capable_depot_indices), var_name)
                else:
                    # Any depot can perform this maintenance
                    maint_assigned_depot[instance_id] = model.NewIntVarFromDomain(
                        cp_model.Domain.FromValues(depot_indices), var_name)
                
                # 4. km_at_maint_start: Integer variable for the vehicle's km at the start of maintenance
                var_name = f"km_at_maint_start_{instance_id}"
                km_at_maint_start[instance_id] = model.NewIntVar(0, max_possible_km, var_name)
                
                # C6: KM Recording - Link km_at_maint_start to the vehicle's km at the start of the shift
                # Use AddElement to dynamically select the correct km_at_shift_start based on maint_start_s
                # This is a more flexible approach than directly using start_idx
                # Only enforce if maintenance is performed
                model.Add(km_at_maint_start[instance_id] == km_at_shift_start[(vehicle_id, start_idx)])\
                    .OnlyEnforceIf(maint_performed[instance_id])
                
                # C7: Max KM Limit - Ensure maintenance is performed before reaching max_km
                if maint_type_id == "preventive":
                    # For preventive maintenance, use the max_km from the maintenance type
                    max_km = maint_type["max_km"]
                    optimal_km = maint_type["optimal_km"]
                    
                    # Add constraint: km_at_maint_start <= max_km
                    # Only enforce if maintenance is performed
                    model.Add(km_at_maint_start[instance_id] <= max_km)\
                        .OnlyEnforceIf(maint_performed[instance_id])
                    
                    # Create deviation variable for the objective function
                    # This linearizes the absolute difference |km_at_maint_start - optimal_km|
                    var_name = f"deviation_{instance_id}"
                    deviation_var = model.NewIntVar(0, max_possible_km, var_name)
                    
                    # Create helper variables for the linearization
                    pos_diff_var = model.NewIntVar(0, max_possible_km, f"pos_diff_{instance_id}")
                    neg_diff_var = model.NewIntVar(0, max_possible_km, f"neg_diff_{instance_id}")
                    
                    # Add constraints to linearize the absolute difference
                    # km_at_maint_start - optimal_km = pos_diff - neg_diff
                    model.Add(km_at_maint_start[instance_id] - optimal_km == pos_diff_var - neg_diff_var)\
                        .OnlyEnforceIf(maint_performed[instance_id])
                    
                    # deviation = pos_diff + neg_diff
                    model.Add(deviation_var == pos_diff_var + neg_diff_var)\
                        .OnlyEnforceIf(maint_performed[instance_id])
                    
                    # If maintenance is not performed, deviation is 0
                    model.Add(deviation_var == 0).OnlyEnforceIf(maint_performed[instance_id].Not())
                    
                    # Add to the list of deviation variables for the objective function
                    deviation_vars.append(deviation_var)
                elif maint_type_id == "corrective":
                    # For corrective maintenance, use the max_km_window from the maintenance type
                    # Check if this vehicle has this corrective maintenance type pending
                    for pending_task in vehicle.get("pending_corrective_tasks", []):
                        if pending_task["maintenance_type_id"] == maint_id:
                            # Calculate the max KM based on initial KM and remaining KM window
                            initial_km = vehicle["initial_km"]
                            remaining_km = pending_task["remaining_km"]
                            max_km = initial_km + remaining_km
                            
                            # Add constraint: km_at_maint_start <= max_km
                            # Only enforce if maintenance is performed
                            model.Add(km_at_maint_start[instance_id] <= max_km)\
                                .OnlyEnforceIf(maint_performed[instance_id])
                            
                            # C8: Force Corrective Maintenance - Ensure this corrective task is performed
                            # Instead of forcing all corrective tasks to be performed (which may cause infeasibility),
                            # we'll track them and ensure at least one instance of each corrective task is performed
                            # This will be handled in a separate constraint after all maintenance instances are created
                            break
                
                # 5. maint_intervals: OptionalIntervalVar representing the maintenance interval
                # Estimate duration based on required manhours (simplified for now)
                # In a real implementation, this would depend on depot manhours per shift
                est_duration = min(max(1, required_manhours // 8), max_maint_duration)  # Rough estimate: 8 hours per shift
                
                var_name = f"maint_interval_{instance_id}"
                maint_intervals[instance_id] = model.NewOptionalIntervalVar(
                    start=start_idx,  # Start shift index
                    size=est_duration,  # Estimated duration in shifts
                    end=start_idx + est_duration,  # End shift index
                    is_present=maint_performed[instance_id],  # Present if maintenance is performed
                    name=var_name
                )
                
                # 6. maint_active_s: Boolean variables indicating if maintenance is active during each shift
                # For each shift in the potential maintenance interval
                for s_idx in range(start_idx, min(start_idx + est_duration, len(all_shifts_with_initial))):
                    var_name = f"maint_active_{instance_id}_{s_idx}"
                    maint_active_s[(instance_id, s_idx)] = model.NewBoolVar(var_name)
                    
                    # Link maint_active_s to the maintenance being performed
                    # maint_active_s is true if and only if:
                    # 1. The maintenance is performed (maint_performed is true)
                    # 2. The shift index is within the maintenance interval
                    
                    # If maintenance is performed and shift is within interval, maint_active_s is true
                    model.AddBoolAnd([maint_performed[instance_id]]).OnlyEnforceIf(maint_active_s[(instance_id, s_idx)])
                    
                    # If maintenance is not performed, maint_active_s is false
                    model.AddImplication(maint_performed[instance_id].Not(), maint_active_s[(instance_id, s_idx)].Not())
                    
                    # C8: Maintenance Location Constraint - Part 2: Location continuity during maintenance
                    # If maintenance is active during this shift, the vehicle must remain at the same location for the next shift
                    if s_idx + 1 < len(all_shifts_with_initial):
                        # Vehicle location at the current shift
                        loc_current = loc_start_vs[(vehicle_id, s_idx)]
                        # Vehicle location at the next shift
                        loc_next = loc_start_vs[(vehicle_id, s_idx + 1)]
                        
                        # If maintenance is active, vehicle must stay at the same location
                        model.Add(loc_next == loc_current).OnlyEnforceIf(maint_active_s[(instance_id, s_idx)])
                
                # C8: Maintenance Location Constraint - Part 1: Maintenance must be performed at the assigned depot
                # If maintenance is performed, the vehicle must be at the assigned depot at the start of maintenance
                model.Add(loc_start_vs[(vehicle_id, start_idx)] == maint_assigned_depot[instance_id])\
                    .OnlyEnforceIf(maint_performed[instance_id])
    
    # Add constraints
    
    # C1: Route Coverage - Each route must be assigned to exactly one vehicle
    for route in routes:
        route_id = route["id"]
        # Get all assignment variables for this route
        route_vars = [assign_vr[(vehicle["id"], route_id)] for vehicle in vehicles]
        # Add constraint: sum of assignments for this route must be exactly 1
        model.Add(sum(route_vars) == 1)
    
    # C2: Vehicle Uniqueness - Each vehicle can be assigned to at most one route per shift
    for day, shift in all_shifts:
        # Get routes for this shift
        shift_routes = routes_by_day_shift.get((day, shift), [])
        if not shift_routes:
            continue
            
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            # Get all assignment variables for this vehicle in this shift
            vehicle_shift_vars = [assign_vr[(vehicle_id, route["id"])] for route in shift_routes]
            # Add constraint: sum of assignments for this vehicle in this shift must be at most 1
            if vehicle_shift_vars:
                model.Add(sum(vehicle_shift_vars) <= 1)
    
    # C12: Full Vehicle Activity Exclusivity - A vehicle cannot be assigned to a route during a shift where it's under maintenance
    for shift_idx, (day, shift) in enumerate(all_shifts):
        # Skip night shifts (no routes during night shifts)
        if shift == "night":
            continue
            
        # Get routes for this shift
        shift_routes = routes_by_day_shift.get((day, shift), [])
        if not shift_routes:
            continue
        
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            
            # Get all route assignment variables for this vehicle in this shift
            vehicle_route_vars = [assign_vr[(vehicle_id, route["id"])] for route in shift_routes]
            
            # Get all maintenance activity variables for this vehicle in this shift
            # The shift index in all_shifts is offset by 1 from all_shifts_with_initial (which includes initial state)
            active_shift_idx = shift_idx + 1  # +1 to account for the initial state
            
            for instance in all_maint_instances:
                if instance["vehicle_id"] == vehicle_id:
                    instance_id = instance["id"]
                    
                    # Check if this maintenance instance is active in this shift
                    if (instance_id, active_shift_idx) in maint_active_s:
                        maint_active_var = maint_active_s[(instance_id, active_shift_idx)]
                        
                        # For each route, add constraint: if maintenance is active, route cannot be assigned
                        for route_var in vehicle_route_vars:
                            # route_var and maint_active_var cannot both be 1
                            model.AddBoolOr([route_var.Not(), maint_active_var.Not()])
    
    # C3: Initial Location Constraint - Set the initial location for each vehicle
    for vehicle in vehicles:
        vehicle_id = vehicle["id"]
        initial_location = vehicle["initial_location"]
        initial_location_index = location_id_to_index[initial_location]
        
        # Set the initial location (shift index 0)
        model.Add(loc_start_vs[(vehicle_id, 0)] == initial_location_index)
    
    # C4: Location Transition Logic - Track vehicle locations across shifts
    # Create a mapping from (day, shift) to shift index for easier reference
    shift_to_index = {shift: idx for idx, shift in enumerate(all_shifts_with_initial)}
    
    for idx, (day, shift) in enumerate(all_shifts):
        # Skip the initial state (already handled)
        if idx == 0 and shift == "initial":
            continue
            
        # Get the current shift index
        curr_shift_idx = shift_to_index[(day, shift)]
        
        # Get routes for this shift
        shift_routes = routes_by_day_shift.get((day, shift), [])
        
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            
            # Get the previous shift index
            prev_shift_idx = curr_shift_idx - 1
            
            # For each route in this shift
            for route in shift_routes:
                route_id = route["id"]
                start_location = route["start_location"]
                end_location = route["end_location"]
                start_location_index = location_id_to_index[start_location]
                end_location_index = location_id_to_index[end_location]
                
                # Create a literal for this route assignment
                route_assigned_lit = assign_vr[(vehicle_id, route_id)]
                
                # If vehicle is assigned to this route:
                # 1. Current location must match route start location
                model.Add(loc_start_vs[(vehicle_id, curr_shift_idx)] == start_location_index).OnlyEnforceIf(route_assigned_lit)
                
                # 2. Next location (at the start of next shift) must match route end location
                if curr_shift_idx + 1 < len(all_shifts_with_initial):
                    model.Add(loc_start_vs[(vehicle_id, curr_shift_idx + 1)] == end_location_index).OnlyEnforceIf(route_assigned_lit)
            
            # Check for maintenance activities in this shift
            # Get all maintenance activity variables for this vehicle in this shift
            maint_active_in_shift = False
            for instance in all_maint_instances:
                if instance["vehicle_id"] == vehicle_id:
                    instance_id = instance["id"]
                    # Check if this maintenance instance is active in this shift
                    if (instance_id, curr_shift_idx) in maint_active_s:
                        maint_active_lit = maint_active_s[(instance_id, curr_shift_idx)]
                        maint_active_in_shift = True
                        
                        # If maintenance is active, the vehicle's location doesn't change
                        if curr_shift_idx + 1 < len(all_shifts_with_initial):
                            model.Add(loc_start_vs[(vehicle_id, curr_shift_idx + 1)] == loc_start_vs[(vehicle_id, curr_shift_idx)])\
                                .OnlyEnforceIf(maint_active_lit)
            
            # If vehicle is idle during this shift (not assigned to any route)
            # Create a literal for the idle state
            if shift_routes:
                # Get all route assignment variables for this vehicle in this shift
                vehicle_shift_vars = [assign_vr[(vehicle_id, route["id"])] for route in shift_routes]
                
                # Create a Boolean variable for the idle state (1 if idle, 0 if assigned to a route)
                idle_var_name = f"idle_{vehicle_id}_{day}_{shift}"
                idle_lit = model.NewBoolVar(idle_var_name)
                
                # idle_lit is true if and only if the vehicle is not assigned to any route
                model.Add(sum(vehicle_shift_vars) == 0).OnlyEnforceIf(idle_lit)
                model.Add(sum(vehicle_shift_vars) > 0).OnlyEnforceIf(idle_lit.Not())
                
                # If vehicle is idle and not under maintenance, its location doesn't change
                if curr_shift_idx + 1 < len(all_shifts_with_initial) and not maint_active_in_shift:
                    model.Add(loc_start_vs[(vehicle_id, curr_shift_idx + 1)] == loc_start_vs[(vehicle_id, curr_shift_idx)])\
                        .OnlyEnforceIf(idle_lit)
            
            # NEW: Enforce location continuity for night shifts
            # If this is a night shift, the vehicle's location at the end of the night shift
            # must be the same as its location at the start of the next day shift
            if shift == "night" and curr_shift_idx + 1 < len(all_shifts_with_initial):
                next_day, next_shift = all_shifts_with_initial[curr_shift_idx + 1]
                
                # Only apply if the next shift is a day shift
                if next_shift == "day":
                    # Create a Boolean variable for the night shift state
                    night_var_name = f"night_{vehicle_id}_{day}_{shift}"
                    night_lit = model.NewBoolVar(night_var_name)
                    
                    # night_lit is always true for night shifts
                    model.Add(night_lit == 1)
                    
                    # If it's a night shift, the vehicle's location at the start of the next day shift
                    # must be the same as its location at the start of this night shift
                    model.Add(loc_start_vs[(vehicle_id, curr_shift_idx + 1)] == loc_start_vs[(vehicle_id, curr_shift_idx)])\
                        .OnlyEnforceIf(night_lit)
            
            # NEW: Enforce location continuity for transitions between day and night shifts
            # If this is a day shift, the vehicle's location at the start of the next night shift
            # must be the same as its location at the end of this day shift
            if shift == "day" and curr_shift_idx + 1 < len(all_shifts_with_initial):
                next_day, next_shift = all_shifts_with_initial[curr_shift_idx + 1]
                
                # Only apply if the next shift is a night shift
                if next_shift == "night":
                    # Check if the vehicle is assigned to any route in this day shift
                    assigned_to_route = False
                    for route in shift_routes:
                        route_id = route["id"]
                        if (vehicle_id, route_id) in assign_vr:
                            route_assigned_lit = assign_vr[(vehicle_id, route_id)]
                            
                            # If the vehicle is assigned to this route, its location at the start of the next night shift
                            # must be the same as the route's end location
                            if curr_shift_idx + 1 < len(all_shifts_with_initial):
                                end_location = route["end_location"]
                                end_location_index = location_id_to_index[end_location]
                                model.Add(loc_start_vs[(vehicle_id, curr_shift_idx + 1)] == end_location_index)\
                                    .OnlyEnforceIf(route_assigned_lit)
                            
                            assigned_to_route = True
                    
                    # If the vehicle is not assigned to any route and not under maintenance,
                    # its location at the start of the next night shift must be the same as its location at the start of this day shift
                    if not assigned_to_route and not maint_active_in_shift:
                        model.Add(loc_start_vs[(vehicle_id, curr_shift_idx + 1)] == loc_start_vs[(vehicle_id, curr_shift_idx)])
    
    # C5: Location Capacity Constraint - Ensure number of vehicles at each location doesn't exceed capacity
    for idx, (day, shift) in enumerate(all_shifts_with_initial):
        # For each location
        for loc_id, loc_data in locations.items():
            loc_index = location_id_to_index[loc_id]
            capacity = loc_data["capacity"]
            
            # Get all vehicle location variables for this shift
            vehicles_at_loc = []
            for vehicle in vehicles:
                vehicle_id = vehicle["id"]
                # Create a Boolean variable that is 1 if the vehicle is at this location, 0 otherwise
                is_at_loc_var_name = f"is_at_loc_{vehicle_id}_{loc_id}_{day}_{shift}"
                is_at_loc = model.NewBoolVar(is_at_loc_var_name)
                
                # Link the Boolean variable to the location variable
                model.Add(loc_start_vs[(vehicle_id, idx)] == loc_index).OnlyEnforceIf(is_at_loc)
                model.Add(loc_start_vs[(vehicle_id, idx)] != loc_index).OnlyEnforceIf(is_at_loc.Not())
                
                vehicles_at_loc.append(is_at_loc)
            
            # Add constraint: sum of vehicles at this location must be at most the capacity
            model.Add(sum(vehicles_at_loc) <= capacity)
    
    # C6: KM Accumulation - Track vehicle kilometers based on route assignments
    # Set initial KM for each vehicle
    for vehicle in vehicles:
        vehicle_id = vehicle["id"]
        initial_km = vehicle["initial_km"]
        
        # Set the initial KM (shift index 0)
        model.Add(km_at_shift_start[(vehicle_id, 0)] == initial_km)
        
        # C8: Force corrective maintenance to be performed
        # For each pending corrective task, ensure at least one corresponding maintenance instance is performed
        for pending_task in vehicle.get("pending_corrective_tasks", []):
            corrective_type_id = pending_task["maintenance_type_id"]
            
            # Find all maintenance instances for this vehicle and corrective type
            corrective_instances = []
            for instance in all_maint_instances:
                if instance["vehicle_id"] == vehicle_id and instance["maint_id"] == corrective_type_id:
                    corrective_instances.append(instance["id"])
            
            # If there are instances available, add constraint to ensure at least one is performed
            if corrective_instances:
                # Create a list of maint_performed variables for these instances
                corrective_vars = [maint_performed[instance_id] for instance_id in corrective_instances]
                
                # Add constraint: at least one corrective maintenance instance must be performed
                model.Add(sum(corrective_vars) >= 1)
        
        # C11: Routing to Depot Constraint
        # For each maintenance instance, if it's performed, ensure the vehicle is at a depot capable of performing the maintenance
        # This applies to both preventive and corrective maintenance
        for instance in all_maint_instances:
            if instance["vehicle_id"] == vehicle_id:
                instance_id = instance["id"]
                start_idx = instance["start_idx"]
                
                # If this maintenance is performed, ensure the vehicle is at the assigned depot at the start
                # This is already covered by C8 Part 1, but we need to ensure the route before maintenance ends at the depot
                
                # If maintenance starts after day 1 (not the first shift), we need to ensure the previous route ends at the depot
                if start_idx > 1:  # Skip initial state (0) and first shift (1)
                    # Get the previous shift index
                    prev_idx = start_idx - 1
                    prev_day, prev_shift = all_shifts_with_initial[prev_idx]
                    
                    # Only apply for day shifts (since routes only happen during day shifts)
                    if prev_shift == "day":
                        # Get all routes for the previous shift
                        prev_shift_routes = routes_by_day_shift.get((prev_day, prev_shift), [])
                        
                        # For each route in the previous shift
                        for route in prev_shift_routes:
                            route_id = route["id"]
                            end_location = route["end_location"]
                            end_location_index = location_id_to_index[end_location]
                            
                            # If the vehicle is assigned to this route and maintenance is performed,
                            # the route's end location must match the maintenance assigned depot
                            route_assigned_lit = assign_vr[(vehicle_id, route_id)]
                            
                            # Create a combined literal for both conditions
                            combined_lit = model.NewBoolVar(f"combined_{vehicle_id}_{route_id}_{instance_id}")
                            model.AddBoolAnd([route_assigned_lit, maint_performed[instance_id]]).OnlyEnforceIf(combined_lit)
                            model.AddBoolOr([route_assigned_lit.Not(), maint_performed[instance_id].Not()]).OnlyEnforceIf(combined_lit.Not())
                            
                            # If both conditions are true, the route's end location must match the maintenance assigned depot
                            model.Add(end_location_index == maint_assigned_depot[instance_id]).OnlyEnforceIf(combined_lit)
    
    # Update KM for each shift based on route assignments
    for curr_shift_idx, (day, shift) in enumerate(all_shifts_with_initial[:-1]):  # Exclude the last shift as we don't need to update beyond it
        # Skip the initial state (already handled)
        if day == 0 and shift == "initial":
            continue
            
        # Get routes for this shift
        shift_routes = routes_by_day_shift.get((day, shift), [])
        
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            
            # For each route in this shift
            route_km_terms = []
            for route in shift_routes:
                route_id = route["id"]
                distance_km = route["distance_km"]
                
                # Create a term for this route's contribution to KM
                # If the vehicle is assigned to this route, add the route's distance
                route_assigned_lit = assign_vr[(vehicle_id, route_id)]
                route_km_term = model.NewIntVar(0, distance_km, f"route_km_term_{vehicle_id}_{route_id}")
                
                # route_km_term = distance_km if route is assigned, 0 otherwise
                model.Add(route_km_term == distance_km).OnlyEnforceIf(route_assigned_lit)
                model.Add(route_km_term == 0).OnlyEnforceIf(route_assigned_lit.Not())
                
                route_km_terms.append(route_km_term)
            
            # If no routes in this shift, KM doesn't change
            if not route_km_terms:
                model.Add(km_at_shift_start[(vehicle_id, curr_shift_idx + 1)] == km_at_shift_start[(vehicle_id, curr_shift_idx)])
            else:
                # KM at next shift start = KM at current shift start + sum of route KM terms
                model.Add(km_at_shift_start[(vehicle_id, curr_shift_idx + 1)] == 
                         km_at_shift_start[(vehicle_id, curr_shift_idx)] + sum(route_km_terms))
    
    # C9/C10: Manhour Constraints - Ensure depot manhour capacity is not exceeded
    # For each depot, create a cumulative constraint for manhour resources
    
    # Track maintenance demands by depot and shift
    # Structure: depot_maint_demands[depot_id][shift_idx] = list of (interval_var, demand) tuples
    depot_maint_demands = {}
    for loc_id, loc_data in locations.items():
        if loc_data["type"] == "depot":
            depot_maint_demands[loc_id] = {}
            for idx, (day, shift) in enumerate(all_shifts_with_initial):
                depot_maint_demands[loc_id][idx] = []
    
    # For each maintenance instance, add its manhour demand to the appropriate depot and shifts
    for instance in all_maint_instances:
        instance_id = instance["id"]
        vehicle_id = instance["vehicle_id"]
        maint_id = instance["maint_id"]
        required_manhours = instance["required_manhours"]
        start_idx = instance["start_idx"]
        
        # Get the maintenance type to determine duration
        maint_type = next((mt for mt in maintenance_types if mt["id"] == maint_id), None)
        if not maint_type:
            continue
        
        # Estimate duration based on required manhours (same as in interval creation)
        est_duration = min(max(1, required_manhours // 8), max_maint_duration)  # Rough estimate: 8 hours per shift
        
        # Calculate manhours per shift (divide total manhours evenly across shifts)
        manhours_per_shift = required_manhours / est_duration
        
        # For each potential depot
        for loc_id, loc_data in locations.items():
            if loc_data["type"] == "depot":
                # Get the depot index
                depot_index = location_id_to_index[loc_id]
                
                # Create a Boolean variable that is 1 if this maintenance is performed at this depot
                is_at_depot_var_name = f"is_at_depot_{instance_id}_{loc_id}"
                is_at_depot = model.NewBoolVar(is_at_depot_var_name)
                
                # Link the Boolean variable to the depot assignment
                model.Add(maint_assigned_depot[instance_id] == depot_index).OnlyEnforceIf(is_at_depot)
                model.Add(maint_assigned_depot[instance_id] != depot_index).OnlyEnforceIf(is_at_depot.Not())
                
                # For each shift in the potential maintenance interval
                for s_idx in range(start_idx, min(start_idx + est_duration, len(all_shifts_with_initial))):
                    # Create a Boolean variable that is 1 if maintenance is active at this depot during this shift
                    active_at_depot_var_name = f"active_at_depot_{instance_id}_{loc_id}_{s_idx}"
                    active_at_depot = model.NewBoolVar(active_at_depot_var_name)
                    
                    # active_at_depot is true if and only if:
                    # 1. The maintenance is active during this shift (maint_active_s is true)
                    # 2. The maintenance is assigned to this depot (is_at_depot is true)
                    model.AddBoolAnd([maint_active_s[(instance_id, s_idx)], is_at_depot]).OnlyEnforceIf(active_at_depot)
                    model.AddBoolOr([maint_active_s[(instance_id, s_idx)].Not(), is_at_depot.Not()]).OnlyEnforceIf(active_at_depot.Not())
                    
                    # Create an integer variable for the manhour demand
                    demand_var_name = f"manhour_demand_{instance_id}_{loc_id}_{s_idx}"
                    demand_var = model.NewIntVar(0, int(manhours_per_shift), demand_var_name)
                    
                    # If active_at_depot is true, demand_var = manhours_per_shift, otherwise 0
                    model.Add(demand_var == int(manhours_per_shift)).OnlyEnforceIf(active_at_depot)
                    model.Add(demand_var == 0).OnlyEnforceIf(active_at_depot.Not())
                    
                    # Add to the list of demands for this depot and shift
                    depot_maint_demands[loc_id][s_idx].append(demand_var)
    
    # Add cumulative constraints for each depot and shift
    for loc_id, loc_data in locations.items():
        if loc_data["type"] == "depot":
            manhours_per_shift = loc_data["manhours_per_shift"]
            
            # For each shift in the planning horizon
            for idx, (day, shift) in enumerate(all_shifts_with_initial):
                # Skip the initial state
                if day == 0 and shift == "initial":
                    continue
                
                # Get all demands for this depot and shift
                demands = depot_maint_demands[loc_id][idx]
                
                # If there are demands, add a constraint to ensure total demand <= capacity
                if demands:
                    model.Add(sum(demands) <= manhours_per_shift)
    
    # C8: Force Corrective Maintenance - Ensure at least one instance of each pending corrective task is performed
    # For each vehicle with pending corrective tasks
    for vehicle in vehicles:
        vehicle_id = vehicle["id"]
        
        # For each pending corrective task
        for pending_task in vehicle.get("pending_corrective_tasks", []):
            maint_id = pending_task["maintenance_type_id"]
            
            # Find all maintenance instances for this vehicle and maintenance type
            task_instances = []
            for instance in all_maint_instances:
                if instance["vehicle_id"] == vehicle_id and instance["maint_id"] == maint_id:
                    task_instances.append(instance["id"])
            
            # If there are instances, add a constraint to ensure at least one is performed
            if task_instances:
                # Create a list of Boolean variables for each instance
                performed_vars = [maint_performed[instance_id] for instance_id in task_instances]
                
                # Add constraint: at least one instance must be performed
                model.Add(sum(performed_vars) >= 1)
    
    # Set the objective function: Minimize the sum of deviation variables
    # This minimizes the total deviation from optimal KM for all preventive maintenance tasks
    if deviation_vars:
        model.Minimize(sum(deviation_vars))
    
    # Create a solver and solve the model
    solver = cp_model.CpSolver()
    
    # Set time limit
    solver.parameters.max_time_in_seconds = time_limit_seconds
    
    # Solve the model
    status = solver.Solve(model)
    
    # Process results
    results = {
        "status": solver.StatusName(status),
        "status_code": status,
        "wall_time": solver.WallTime(),
    }
    
    # Add more detailed results if the model is feasible or optimal
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # Extract and format detailed results for visualization
        schedule_results = {}
        
        # 1. Extract route assignments for each vehicle and shift
        route_assignments = {}
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            route_assignments[vehicle_id] = {}
            
            for idx, (day, shift) in enumerate(all_shifts_with_initial):
                # Skip the initial state
                if day == 0 and shift == "initial":
                    continue
                    
                # Find if this vehicle is assigned to any route in this shift
                assigned_route = None
                for route in routes_by_day_shift.get((day, shift), []):
                    route_id = route["id"]
                    if (vehicle_id, route_id) in assign_vr and solver.Value(assign_vr[(vehicle_id, route_id)]):
                        assigned_route = route
                        break
                        
                # Store the assignment for this shift
                shift_key = f"{day}_{shift}"
                if assigned_route:
                    route_assignments[vehicle_id][shift_key] = {
                        "route_id": assigned_route["id"],
                        "start_location": assigned_route["start_location"],
                        "end_location": assigned_route["end_location"],
                        "distance_km": assigned_route["distance_km"]
                    }
                else:
                    route_assignments[vehicle_id][shift_key] = None
        
        # 2. Extract maintenance schedules
        maintenance_schedules = {}
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            maintenance_schedules[vehicle_id] = []
            
            # Find all maintenance activities performed for this vehicle
            for instance in all_maint_instances:
                if instance["vehicle_id"] != vehicle_id:
                    continue
                    
                instance_id = instance["id"]
                if solver.Value(maint_performed[instance_id]):
                    # Get maintenance details
                    maint_type = next((mt for mt in maintenance_types if mt["id"] == instance["maint_id"]), None)
                    start_idx = instance["start_idx"]
                    start_day, start_shift = all_shifts_with_initial[start_idx]
                    
                    # Get assigned depot (convert index back to ID)
                    depot_index = solver.Value(maint_assigned_depot[instance_id])
                    depot_id = index_to_location_id[depot_index]
                    
                    # Get KM at maintenance start
                    km_at_start = solver.Value(km_at_maint_start[instance_id])
                    
                    # Calculate end shift based on estimated duration
                    required_manhours = instance["required_manhours"]
                    est_duration = min(max(1, required_manhours // 8), max_maint_duration)
                    end_idx = min(start_idx + est_duration, len(all_shifts_with_initial) - 1)
                    end_day, end_shift = all_shifts_with_initial[end_idx]
                    
                    # Add to maintenance schedules
                    maintenance_schedules[vehicle_id].append({
                        "maintenance_id": instance["maint_id"],
                        "maintenance_type": maint_type["type"],  # 'preventive' or 'corrective'
                        "start_day": start_day,
                        "start_shift": start_shift,
                        "end_day": end_day,
                        "end_shift": end_shift,
                        "depot": depot_id,
                        "km_at_start": km_at_start,
                        "required_manhours": required_manhours
                    })
        
        # 3. Extract vehicle locations and KM for each shift
        vehicle_states = {}
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            vehicle_states[vehicle_id] = {}
            
            for idx, (day, shift) in enumerate(all_shifts_with_initial):
                # Skip the initial state in the output (but use it for calculations)
                if day == 0 and shift == "initial":
                    continue
                    
                # Get location and KM at this shift
                location_index = solver.Value(loc_start_vs[(vehicle_id, idx)])
                location_id = index_to_location_id[location_index]
                km = solver.Value(km_at_shift_start[(vehicle_id, idx)])
                
                # Determine if the vehicle is idle (not assigned to a route and not under maintenance)
                is_idle = True
                
                # Check if assigned to a route
                shift_key = f"{day}_{shift}"
                if route_assignments[vehicle_id][shift_key] is not None:
                    is_idle = False
                
                # Check if under maintenance
                is_under_maintenance = False
                for maint in maintenance_schedules[vehicle_id]:
                    maint_start_day = maint["start_day"]
                    maint_start_shift = maint["start_shift"]
                    maint_end_day = maint["end_day"]
                    maint_end_shift = maint["end_shift"]
                    
                    # Check if this shift is within the maintenance period
                    if (day > maint_start_day or (day == maint_start_day and shift >= maint_start_shift)) and \
                       (day < maint_end_day or (day == maint_end_day and shift <= maint_end_shift)):
                        is_under_maintenance = True
                        is_idle = False
                        break
                
                # Store the state for this shift
                vehicle_states[vehicle_id][shift_key] = {
                    "location": location_id,
                    "km": km,
                    "is_idle": is_idle,
                    "is_under_maintenance": is_under_maintenance
                }
        
        # 4. Combine all results into the schedule_results structure
        schedule_results = {
            "vehicles": {},
            "optimization_info": {
                "status": solver.StatusName(status),
                "wall_time": solver.WallTime(),
                "objective_value": solver.ObjectiveValue() if status == cp_model.OPTIMAL else None
            }
        }
        
        # Add detailed vehicle schedules
        for vehicle in vehicles:
            vehicle_id = vehicle["id"]
            
            schedule_results["vehicles"][vehicle_id] = {
                "initial_state": {
                    "location": vehicle["initial_location"],
                    "km": vehicle["initial_km"]
                },
                "route_assignments": route_assignments[vehicle_id],
                "maintenance_activities": maintenance_schedules[vehicle_id],
                "states": vehicle_states[vehicle_id]
            }
        
        # Add the schedule results to the output
        results["schedule_results"] = schedule_results
        
        # Save the schedule results to a JSON file for visualization
        import json
        import os
        
        # Ensure the output directory exists
        os.makedirs("output", exist_ok=True)
        
        # Save the schedule results to a JSON file
        with open("output/schedule_results.json", "w") as f:
            json.dump(schedule_results, f, indent=2)
    
    return results

def print_optimization_results(results: Dict[str, Any]) -> None:
    """
    Print the optimization results in a readable format.
    
    Args:
        results: Dictionary containing the optimization results
    """
    print("\nOptimization Results:")
    print(f"Status: {results['status']}")
    print(f"Wall time: {results['wall_time']:.2f} seconds")
    
    # Print more detailed results if available
    if 'schedule_results' in results:
        schedule_results = results['schedule_results']
        
        # Print optimization info
        if 'optimization_info' in schedule_results and schedule_results['optimization_info']['objective_value'] is not None:
            print(f"Objective value: {schedule_results['optimization_info']['objective_value']}")
        
        # Print summary of vehicle assignments
        if 'vehicles' in schedule_results:
            print("\nVehicle Schedule Summary:")
            
            # Count total routes and maintenance activities
            total_routes = 0
            total_maintenance = 0
            maintenance_by_type = {'preventive': 0, 'corrective': 0}
            
            for vehicle_id, vehicle_data in schedule_results['vehicles'].items():
                # Count route assignments
                route_count = sum(1 for r in vehicle_data['route_assignments'].values() if r is not None)
                total_routes += route_count
                
                # Count maintenance activities
                maint_count = len(vehicle_data['maintenance_activities'])
                total_maintenance += maint_count
                
                # Count by maintenance type
                for maint in vehicle_data['maintenance_activities']:
                    maint_type = maint['maintenance_type']
                    maintenance_by_type[maint_type] += 1
                
                print(f"  Vehicle {vehicle_id}: {route_count} routes, {maint_count} maintenance activities")
            
            print("\nOverall Statistics:")
            print(f"  Total route assignments: {total_routes}")
            print(f"  Total maintenance activities: {total_maintenance}")
            print(f"    - Preventive: {maintenance_by_type['preventive']}")
            print(f"    - Corrective: {maintenance_by_type['corrective']}")
        
        print("\nDetailed results saved to 'output/schedule_results.json'")
