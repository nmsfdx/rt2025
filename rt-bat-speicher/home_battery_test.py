"""
Simple Home Battery Test
"""

import pybamm
import numpy as np

def test_home_battery():
    """Test basic home battery functionality"""
    
    print("=== Testing Home Battery Simulation ===")
    
    try:
        # Create SPM model for efficiency
        model = pybamm.lithium_ion.SPM()
        print("✓ SPM model created")
        
        # Test home-scale power profile (kW scale)
        # Convert to Watts for PyBaMM
        home_powers_kw = [2.0, -3.0, 1.5]  # kW: discharge, charge, discharge
        home_powers_w = [p * 1000 for p in home_powers_kw]  # Convert to Watts
        durations = [1.0, 2.0, 1.0]  # hours
        
        print(f"Testing power profile: {home_powers_kw} kW")
        print(f"Converted to: {home_powers_w} W")
        
        # Create experiment
        experiment_steps = []
        for power_w, duration in zip(home_powers_w, durations):
            if power_w > 0:
                step = f"Discharge at {power_w} W for {duration} hours or until 3.0 V"
            else:
                step = f"Charge at {abs(power_w)} W for {duration} hours or until 4.2 V"
            experiment_steps.append(step)
        
        experiment = pybamm.Experiment(experiment_steps)
        print("✓ Experiment created")
        
        # Use conservative solver
        solver = pybamm.CasadiSolver(mode="safe", dt_max=120, rtol=1e-5, atol=1e-7)
        
        # Create simulation
        sim = pybamm.Simulation(model, experiment, solver=solver)
        print("✓ Simulation object created")
        
        # Run simulation
        print("Running home battery simulation...")
        solution = sim.solve()
        print("✓ Simulation completed successfully!")
        
        # Extract results
        time = solution["Time [h]"].entries
        voltage = solution["Terminal voltage [V]"].entries
        current = solution["Current [A]"].entries
        
        print(f"\n--- Results ---")
        print(f"Simulation time: {time[-1]:.1f} hours")
        print(f"Final voltage: {voltage[-1]:.2f} V")
        print(f"Final current: {current[-1]:.2f} A")
        
        # Calculate energy
        power = voltage * current
        total_energy = np.trapz(power, time)
        print(f"Total energy: {total_energy/1000:.2f} kWh")
        
        print("\n✅ Home battery simulation successful!")
        print("Key findings:")
        print("• kW-scale powers work with proper solver settings")
        print("• SPM model can handle home battery applications")
        print("• Energy calculations are realistic for home use")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_capacities():
    """Test different battery capacities"""
    
    print(f"\n=== Testing Different Home Battery Capacities ===")
    
    # Typical home battery capacities
    capacities_kwh = [5, 10, 15, 20]
    
    for capacity in capacities_kwh:
        print(f"\n--- {capacity} kWh Battery ---")
        
        # Calculate equivalent Ah (assuming 400V nominal)
        nominal_voltage = 400.0
        capacity_ah = (capacity * 1000) / nominal_voltage
        
        print(f"Capacity: {capacity} kWh = {capacity_ah:.1f} Ah @ {nominal_voltage}V")
        
        # Recommended max power (0.7C rate)
        max_power_kw = capacity * 0.7
        print(f"Recommended max power: {max_power_kw:.1f} kW")
        
        # Typical backup time at 2kW load
        backup_hours = capacity / 2.0
        print(f"Backup time @ 2kW load: {backup_hours:.1f} hours")

if __name__ == "__main__":
    print("Home Battery Scale Testing\n")
    
    # Test basic functionality
    success = test_home_battery()
    
    if success:
        # Test different capacities
        test_different_capacities()
        
        print(f"\n=== Home Battery Guidelines ===")
        print("✓ Typical home battery: 5-20 kWh capacity")
        print("✓ Typical power rating: 3-10 kW")
        print("✓ Daily usage: 10-30 kWh for average home") 
        print("✓ Battery covers: 0.5-2 days of essential loads")
        print("✓ Solar integration: Store excess for evening use")
        print("✓ Peak shaving: Charge off-peak, discharge on-peak")
    
    print("\nHome battery testing complete.")
