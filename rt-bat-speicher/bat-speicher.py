import pybamm
import numpy as np
import matplotlib.pyplot as plt


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
    
    def plot_results(self, variables=None):
        """
        Plot simulation results
        
        Parameters:
        variables: list of str, variables to plot (default: voltage, current, SOC)
        """
        if self.solution is None:
            print("No simulation results to plot. Run simulate_power_profile first.")
            return
        
        if variables is None:
            variables = [
                "Terminal voltage [V]",
                "Current [A]", 
                "Discharge capacity [A.h]"
            ]
        
        self.simulation.plot(variables)
    
    def plot_detailed_analysis(self):
        """
        Create detailed plots of battery behavior
        """
        if self.solution is None:
            print("No simulation results to plot. Run simulate_power_profile first.")
            return
        
        # Extract data
        time = self.solution["Time [h]"].entries
        voltage = self.solution["Terminal voltage [V]"].entries
        current = self.solution["Current [A]"].entries
        power = voltage * current
        
        # Calculate cumulative energy
        energy_cumulative = np.cumsum(power * np.gradient(time))
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle("Battery Simulation Results", fontsize=16)
        
        # Voltage vs Time
        axes[0, 0].plot(time, voltage, 'b-', linewidth=2)
        axes[0, 0].set_xlabel("Time [h]")
        axes[0, 0].set_ylabel("Voltage [V]")
        axes[0, 0].set_title("Terminal Voltage")
        axes[0, 0].grid(True)
        
        # Current vs Time
        axes[0, 1].plot(time, current, 'r-', linewidth=2)
        axes[0, 1].set_xlabel("Time [h]")
        axes[0, 1].set_ylabel("Current [A]")
        axes[0, 1].set_title("Current")
        axes[0, 1].grid(True)
        
        # Power vs Time
        axes[1, 0].plot(time, power, 'g-', linewidth=2)
        axes[1, 0].set_xlabel("Time [h]")
        axes[1, 0].set_ylabel("Power [W]")
        axes[1, 0].set_title("Power")
        axes[1, 0].grid(True)
        
        # Cumulative Energy vs Time
        axes[1, 1].plot(time, energy_cumulative, 'm-', linewidth=2)
        axes[1, 1].set_xlabel("Time [h]")
        axes[1, 1].set_ylabel("Cumulative Energy [Wh]")
        axes[1, 1].set_title("Energy Storage/Consumption")
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        plt.show()


def main():
    """
    Example usage of the BatterySimulator
    """
    # Create battery simulator
    battery = BatterySimulator(model_type="DFN")
    
    # Define power profile (W) and durations (h)
    # Positive values = discharge, negative values = charge
    power_profile = [10, -5, 15, 0, -8, 20]  # Watts
    time_durations = [0.5, 1.0, 0.3, 0.2, 0.8, 0.4]  # Hours
    
    print("Starting battery simulation...")
    print(f"Power profile: {power_profile} W")
    print(f"Time durations: {time_durations} h")
    
    try:
        # Run simulation
        solution = battery.simulate_power_profile(
            power_values=power_profile,
            time_durations=time_durations,
            initial_soc=0.8  # Start at 80% charge
        )
        
        # Get final battery state
        state = battery.get_battery_state()
        
        print("\n=== Battery State Summary ===")
        print(f"Total simulation time: {state['time_h']:.2f} hours")
        print(f"Final voltage: {state['voltage_V']:.2f} V")
        print(f"Final current: {state['current_A']:.2f} A")
        print(f"Final SOC: {state['soc']:.2f} ({state['soc']*100:.1f}%)")
        print(f"Energy consumed: {state['energy_consumed_Wh']:.2f} Wh")
        print(f"Capacity used: {state['capacity_used_Ah']:.3f} Ah")
        
        # Plot results
        battery.plot_detailed_analysis()
        
    except Exception as e:
        print(f"Simulation failed: {e}")


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


if __name__ == "__main__":
    main()