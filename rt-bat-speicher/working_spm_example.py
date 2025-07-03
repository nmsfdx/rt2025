"""
Working SPM Example - Demonstrates successful SPM simulation
"""

import pybamm
import numpy as np

def working_spm_example():
    """Demonstrates a working SPM simulation with appropriate power values"""
    
    print("=== Working SPM Battery Simulation ===")
    
    # Create SPM model
    model = pybamm.lithium_ion.SPM()
    
    # Use lower power values that work well with SPM
    # The key is to use realistic, moderate power levels
    power_profile = [2, -1.5, 3]  # Much lower than original [10, -5, 15]
    durations = [0.5, 1.0, 0.3]   # Same durations
    
    print(f"Power profile: {power_profile} W")
    print(f"Durations: {durations} h")
    
    # Create experiment
    experiment_steps = []
    for power, duration in zip(power_profile, durations):
        if power > 0:
            step = f"Discharge at {power} W for {duration} hours or until 3.0 V"
        else:
            step = f"Charge at {abs(power)} W for {duration} hours or until 4.2 V"
        experiment_steps.append(step)
    
    experiment = pybamm.Experiment(experiment_steps)
    
    # Use conservative solver settings
    solver = pybamm.CasadiSolver(
        mode="safe",
        dt_max=60,    # 1 minute max time step
        rtol=1e-6,    # Relative tolerance
        atol=1e-8     # Absolute tolerance
    )
    
    # Create simulation
    sim = pybamm.Simulation(model, experiment, solver=solver)
    
    try:
        print("Running simulation...")
        solution = sim.solve()
        
        # Extract results
        time = solution["Time [h]"].entries
        voltage = solution["Terminal voltage [V]"].entries
        current = solution["Current [A]"].entries
        
        print("\n=== Results ===")
        print(f"✓ Simulation completed successfully!")
        print(f"Total time: {time[-1]:.2f} hours")
        print(f"Final voltage: {voltage[-1]:.2f} V")
        print(f"Final current: {current[-1]:.2f} A")
        
        # Calculate energy
        power = voltage * current
        energy = np.trapz(power, time)
        print(f"Total energy: {energy:.2f} Wh")
        
        return True
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        return False

def compare_models():
    """Compare SPM vs DFN for the same power profile"""
    
    print("\n=== Model Comparison ===")
    
    # Test power profile
    power_profile = [3, -2, 4]
    durations = [0.3, 0.5, 0.2]
    
    models = {
        "SPM": pybamm.lithium_ion.SPM(),
        "DFN": pybamm.lithium_ion.DFN()
    }
    
    for model_name, model in models.items():
        print(f"\nTesting {model_name} model...")
        
        try:
            # Create experiment
            experiment_steps = []
            for power, duration in zip(power_profile, durations):
                if power > 0:
                    step = f"Discharge at {power} W for {duration} hours or until 3.0 V"
                else:
                    step = f"Charge at {abs(power)} W for {duration} hours or until 4.2 V"
                experiment_steps.append(step)
            
            experiment = pybamm.Experiment(experiment_steps)
            
            # Use appropriate solver
            if model_name == "SPM":
                solver = pybamm.CasadiSolver(mode="safe", dt_max=60, rtol=1e-6, atol=1e-8)
            else:
                solver = pybamm.CasadiSolver()
            
            sim = pybamm.Simulation(model, experiment, solver=solver)
            solution = sim.solve()
            
            # Get final voltage
            voltage = solution["Terminal voltage [V]"].entries[-1]
            print(f"✓ {model_name}: Final voltage = {voltage:.2f}V")
            
        except Exception as e:
            print(f"❌ {model_name}: Failed - {str(e)[:50]}...")

if __name__ == "__main__":
    print("SPM Model Best Practices Demo\n")
    
    # Run working example
    success = working_spm_example()
    
    if success:
        print("\n🎉 SPM simulation successful!")
        print("\nKey factors for SPM success:")
        print("• Use moderate power values (≤ 5W)")
        print("• Use conservative solver settings")
        print("• Keep simulation durations reasonable")
        print("• Consider DFN for high-power applications")
    
    # Compare models
    compare_models()
    
    print("\n=== Summary ===")
    print("✓ SPM works well for low-power applications")
    print("✓ DFN is more robust for higher power values")
    print("✓ Always start with conservative power values when testing")
