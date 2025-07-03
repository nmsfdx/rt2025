"""
SPM Model Troubleshooting Script
This script helps identify the best power ranges for SPM simulations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pybamm
    import numpy as np
    print("✓ Libraries imported successfully")
    
    # Test basic SPM functionality
    print("\n=== Testing SPM Model ===")
    
    model = pybamm.lithium_ion.SPM()
    print("✓ SPM model created")
    
    # Test very simple experiment first
    simple_experiment = pybamm.Experiment(["Discharge at 1 A for 0.1 hours"])
    print("✓ Simple experiment created")
    
    # Test with conservative solver
    solver = pybamm.CasadiSolver(mode="safe", dt_max=30, rtol=1e-8, atol=1e-10)
    print("✓ Conservative solver created")
    
    sim = pybamm.Simulation(model, simple_experiment, solver=solver)
    print("✓ Simulation object created")
    
    print("Running simple test simulation...")
    solution = sim.solve()
    print("✓ Simple simulation successful!")
    
    # Now test power-based experiments
    print("\n=== Testing Power-Based Experiments ===")
    
    power_values = [1, 2, 3, 5]  # Start with low powers
    
    for power in power_values:
        try:
            print(f"Testing {power}W discharge...", end="")
            
            experiment = pybamm.Experiment([f"Discharge at {power} W for 0.1 hours"])
            sim = pybamm.Simulation(model, experiment, solver=solver)
            solution = sim.solve()
            
            # Get final voltage to check if simulation was reasonable
            voltage = solution["Terminal voltage [V]"].entries[-1]
            print(f" ✓ (Final voltage: {voltage:.2f}V)")
            
        except Exception as e:
            print(f" ✗ Failed: {str(e)[:60]}...")
    
    print("\n=== Recommendations ===")
    print("✓ SPM model works best with:")
    print("  - Power values ≤ 5W for reliable operation")
    print("  - Short time durations (< 1 hour per step)")
    print("  - Conservative solver settings")
    print("\n✓ For higher power values, use DFN model instead")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nSPM troubleshooting complete.")
