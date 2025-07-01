"""
Simple test of the battery simulator
"""

try:
    import pybamm
    print("✓ PyBaMM imported successfully")
    
    import numpy as np
    print("✓ NumPy imported successfully")
    
    import matplotlib.pyplot as plt
    print("✓ Matplotlib imported successfully")
    
    # Test basic PyBaMM functionality
    model = pybamm.lithium_ion.DFN()
    print("✓ DFN model created successfully")
    
    # Test basic experiment
    experiment = pybamm.Experiment(["Discharge at 1 A for 1 hour"])
    print("✓ Experiment created successfully")
    
    # Test simulation
    sim = pybamm.Simulation(model, experiment=experiment)
    print("✓ Simulation object created successfully")
    
    # Try to solve (this might take a moment)
    print("Running simulation...")
    solution = sim.solve()
    print("✓ Simulation completed successfully")
    
    # Extract some basic data
    time = solution["Time [h]"].entries
    voltage = solution["Terminal voltage [V]"].entries
    
    print(f"✓ Simulation ran for {time[-1]:.2f} hours")
    print(f"✓ Final voltage: {voltage[-1]:.2f} V")
    
    print("\n=== PyBaMM Test Successful ===")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed.")
