"""
Example usage of the BatterySimulator for power profile simulation
"""

import pybamm
import numpy as np
import matplotlib.pyplot as plt

# Include the BatterySimulator class and functions directly
class BatterySimulator:
    def __init__(self, model_type="DFN"):
        """
        Initialize the battery simulator
        
        Parameters:
        model_type: str, battery model type (default: "DFN" - Doyle-Fuller-Newman)
        """
        if model_type == "DFN":
            self.model = pybamm.lithium_ion.DFN()
        elif model_type == "SPM":
            self.model = pybamm.lithium_ion.SPM()
        elif model_type == "SPMe":
            self.model = pybamm.lithium_ion.SPMe()
        else:
            self.model = pybamm.lithium_ion.DFN()
        
        self.simulation = None
        self.solution = None
    
    def simulate_power_profile(self, power_values, time_durations, initial_soc=1.0):
        """
        Simulate battery with varying power input/output
        
        Parameters:
        power_values: list of float, power values in Watts (positive = discharge, negative = charge)
        time_durations: list of float, duration for each power value in hours
        initial_soc: float, initial state of charge (0-1)
        
        Returns:
        solution: PyBaMM solution object
        """
        if len(power_values) != len(time_durations):
            raise ValueError("Power values and time durations must have the same length")
        
        # Create experiment steps
        experiment_steps = []
        
        for power, duration in zip(power_values, time_durations):
            if power > 0:
                # Positive power = discharge
                step = f"Discharge at {power} W for {duration} hours or until 3.0 V"
            elif power < 0:
                # Negative power = charge
                step = f"Charge at {abs(power)} W for {duration} hours or until 4.2 V"
            else:
                # Zero power = rest
                step = f"Rest for {duration} hours"
            
            experiment_steps.append(step)
        
        # Create experiment
        experiment = pybamm.Experiment(experiment_steps)
        
        # Set initial SOC parameter
        parameter_values = self.model.default_parameter_values
        parameter_values["Initial concentration in negative electrode [mol.m-3]"] = (
            parameter_values["Initial concentration in negative electrode [mol.m-3]"] * initial_soc
        )
        
        # Create and run simulation
        self.simulation = pybamm.Simulation(
            self.model, 
            experiment=experiment,
            parameter_values=parameter_values
        )
        
        self.solution = self.simulation.solve()
        return self.solution
    
    def get_battery_state(self):
        """
        Get current battery state information
        
        Returns:
        dict: Battery state with SOC, voltage, current, energy, etc.
        """
        if self.solution is None:
            return None
        
        # Extract key variables
        time = self.solution["Time [h]"].entries
        voltage = self.solution["Terminal voltage [V]"].entries
        current = self.solution["Current [A]"].entries
        soc = self.solution["Discharge capacity [A.h]"].entries
        
        # Calculate energy (integrate power over time)
        power = voltage * current
        energy = np.trapz(power, time)  # Wh
        
        # Get final values
        final_state = {
            "time_h": time[-1] if len(time) > 0 else 0,
            "voltage_V": voltage[-1] if len(voltage) > 0 else 0,
            "current_A": current[-1] if len(current) > 0 else 0,
            "soc": 1 - (soc[-1] / soc[0]) if len(soc) > 0 and soc[0] != 0 else 1.0,
            "energy_consumed_Wh": energy,
            "capacity_used_Ah": soc[-1] if len(soc) > 0 else 0
        }
        
        return final_state

def simulate_custom_power(power_values, durations, initial_soc=1.0):
    """
    Convenience function to quickly simulate battery with custom power profile
    
    Parameters:
    power_values: list of power values in Watts (+ = discharge, - = charge)
    durations: list of time durations in hours
    initial_soc: initial state of charge (0-1)
    
    Returns:
    BatterySimulator object with results
    """
    battery = BatterySimulator()
    battery.simulate_power_profile(power_values, durations, initial_soc)
    return battery

def simple_example():
    """Simple example with basic power profile"""
    print("=== Simple Battery Simulation Example ===")
    
    # Create battery simulator
    battery = BatterySimulator()
    
    # Define a simple power profile
    # Positive = discharge, negative = charge, 0 = rest
    power_profile = [5, -3, 8, 0, -5]  # Watts
    durations = [0.5, 1.0, 0.3, 0.2, 0.8]  # Hours
    
    print(f"Power profile: {power_profile} W")
    print(f"Durations: {durations} h")
    
    try:
        # Run simulation starting at 90% charge
        solution = battery.simulate_power_profile(
            power_values=power_profile,
            time_durations=durations,
            initial_soc=0.9
        )
        
        # Get battery state
        state = battery.get_battery_state()
        
        if state:
            print("\n--- Simulation Results ---")
            print(f"Total time: {state['time_h']:.2f} hours")
            print(f"Final voltage: {state['voltage_V']:.2f} V")
            print(f"Final SOC: {state['soc']*100:.1f}%")
            print(f"Energy: {state['energy_consumed_Wh']:.2f} Wh")
            
            # Plot results (optional - comment out if you don't want plots)
            # battery.plot_detailed_analysis()
        else:
            print("Failed to get battery state")
            
    except Exception as e:
        print(f"Simulation error: {e}")

def charging_example():
    """Example focused on charging scenarios"""
    print("\n=== Charging Scenario Example ===")
    
    # Start with low battery and charge
    power_profile = [-10, -5, 0, 2]  # Negative = charging
    durations = [0.5, 1.0, 0.1, 0.3]
    
    battery = simulate_custom_power(power_profile, durations, initial_soc=0.2)
    state = battery.get_battery_state()
    
    if state:
        print(f"Started at 20% SOC, ended at {state['soc']*100:.1f}% SOC")
        print(f"Energy charged: {abs(state['energy_consumed_Wh']):.2f} Wh")

def discharging_example():
    """Example focused on discharging scenarios"""
    print("\n=== Discharging Scenario Example ===")
    
    # Start with full battery and discharge
    power_profile = [15, 10, 5]  # Positive = discharging
    durations = [0.3, 0.5, 0.8]
    
    battery = simulate_custom_power(power_profile, durations, initial_soc=1.0)
    state = battery.get_battery_state()
    
    if state:
        print(f"Started at 100% SOC, ended at {state['soc']*100:.1f}% SOC")
        print(f"Energy discharged: {state['energy_consumed_Wh']:.2f} Wh")

def interactive_power_input():
    """Interactive example where user can input power values"""
    print("\n=== Interactive Power Input ===")
    print("Enter power values (positive = discharge, negative = charge)")
    print("Enter 'done' when finished")
    
    powers = []
    durations = []
    
    while True:
        try:
            power_input = input("Enter power (W) or 'done': ")
            if power_input.lower() == 'done':
                break
                
            power = float(power_input)
            duration = float(input("Enter duration (hours): "))
            
            powers.append(power)
            durations.append(duration)
            
        except ValueError:
            print("Please enter valid numbers")
            
    if powers and durations:
        print(f"\nSimulating power profile: {powers} W")
        print(f"Durations: {durations} h")
        
        battery = simulate_custom_power(powers, durations, initial_soc=0.8)
        state = battery.get_battery_state()
        
        if state:
            print(f"\nFinal state:")
            print(f"SOC: {state['soc']*100:.1f}%")
            print(f"Voltage: {state['voltage_V']:.2f} V")
            print(f"Energy: {state['energy_consumed_Wh']:.2f} Wh")

if __name__ == "__main__":
    # Run examples
    simple_example()
    charging_example()
    discharging_example()
    
    # Uncomment for interactive mode:
    # interactive_power_input()
