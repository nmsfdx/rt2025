import pybamm
import numpy as np
import matplotlib.pyplot as plt


class BatterySimulator:
    def __init__(self, model_type="SPM", capacity_kwh=10.0, nominal_voltage=400.0):
        """
        Initialize the battery simulator for home energy storage
        
        Parameters:
        model_type: str, battery model type (default: "SPM" for efficiency)
        capacity_kwh: float, battery capacity in kWh (typical home: 5-20 kWh)
        nominal_voltage: float, nominal voltage in V (typical: 400V for home systems)
        """
        if model_type == "DFN":
            self.model = pybamm.lithium_ion.DFN()
        elif model_type == "SPM":
            self.model = pybamm.lithium_ion.SPM()
        elif model_type == "SPMe":
            self.model = pybamm.lithium_ion.SPMe()
        else:
            self.model = pybamm.lithium_ion.DFN()
        
        # Store home battery specifications
        self.capacity_kwh = capacity_kwh
        self.nominal_voltage = nominal_voltage
        self.capacity_ah = (capacity_kwh * 1000) / nominal_voltage  # Convert kWh to Ah
        
        self.simulation = None
        self.solution = None
        
        # Scale battery parameters for home storage capacity
        self._scale_battery_parameters()
    
    def _scale_battery_parameters(self):
        """Scale the battery model to match home storage specifications"""
        # Get default parameters
        param = self.model.default_parameter_values
        
        # Scale capacity-related parameters
        # Typical PyBaMM cell is ~2.5Ah, scale to desired capacity
        scale_factor = self.capacity_ah / 2.5
        
        # Scale electrode areas and volumes proportionally
        param["Electrode height [m]"] = param["Electrode height [m]"] * np.sqrt(scale_factor)
        param["Electrode width [m]"] = param["Electrode width [m]"] * np.sqrt(scale_factor)
        
        # Update the model with scaled parameters
        self.model.default_parameter_values = param
    
    def simulate_power_profile(self, power_values_kw, time_durations, initial_soc=1.0, 
                             solver_kwargs=None, safe_mode=True):
        """
        Simulate home battery with varying power input/output
        
        Parameters:
        power_values_kw: list of float, power values in kW (positive = discharge, negative = charge)
        time_durations: list of float, duration for each power value in hours
        initial_soc: float, initial state of charge (0-1)
        solver_kwargs: dict, additional solver parameters for numerical stability
        safe_mode: bool, whether to use conservative solver settings for stability
        
        Returns:
        solution: PyBaMM solution object
        """
        if len(power_values_kw) != len(time_durations):
            raise ValueError("Power values and time durations must have the same length")
        
        # Convert kW to W for PyBaMM
        power_values_w = [p * 1000 for p in power_values_kw]
        
        # Create experiment steps
        experiment_steps = []
        
        for power_kw, power_w, duration in zip(power_values_kw, power_values_w, time_durations):
            if power_w > 0:
                # Positive power = discharge (home using stored energy)
                step = f"Discharge at {power_w} W for {duration} hours or until 3.0 V"
            elif power_w < 0:
                # Negative power = charge (excess solar/grid charging battery)
                step = f"Charge at {abs(power_w)} W for {duration} hours or until 4.2 V"
            else:
                # Zero power = standby
                step = f"Rest for {duration} hours"
            
            experiment_steps.append(step)
        
        # Create experiment
        experiment = pybamm.Experiment(experiment_steps)
        
        # Set initial SOC parameter
        parameter_values = self.model.default_parameter_values.copy()
        parameter_values["Initial concentration in negative electrode [mol.m-3]"] = (
            parameter_values["Initial concentration in negative electrode [mol.m-3]"] * initial_soc
        )
        
        # Configure solver for better stability with home-scale powers
        if safe_mode:
            # Conservative settings for kW-scale powers
            default_solver_kwargs = {
                "dt_max": 120,  # 2 minutes max time step for home applications
                "rtol": 1e-5,   # Slightly relaxed for larger scale
                "atol": 1e-7,   # Absolute tolerance
            }
        else:
            default_solver_kwargs = {}
            
        if solver_kwargs:
            default_solver_kwargs.update(solver_kwargs)
        
        # Choose appropriate solver based on model type and power scale
        if hasattr(self.model, 'name') and 'SPM' in str(type(self.model)):
            # For SPM models with kW powers, use safe mode
            solver = pybamm.CasadiSolver(mode="safe", **default_solver_kwargs)
        else:
            # For other models, use standard solver
            solver = pybamm.CasadiSolver(**default_solver_kwargs)
        
        # Create and run simulation
        try:
            self.simulation = pybamm.Simulation(
                self.model, 
                experiment=experiment,
                parameter_values=parameter_values,
                solver=solver
            )
            
            self.solution = self.simulation.solve()
            return self.solution
            
        except Exception as e:
            # If simulation fails, try with even more conservative settings
            print(f"First attempt failed: {e}")
            print("Retrying with more conservative solver settings for home battery scale...")
            
            try:
                conservative_solver = pybamm.CasadiSolver(
                    mode="safe",
                    dt_max=60,   # 1 minute time steps
                    rtol=1e-6,
                    atol=1e-8
                )
                
                self.simulation = pybamm.Simulation(
                    self.model, 
                    experiment=experiment,
                    parameter_values=parameter_values,
                    solver=conservative_solver
                )
                
                self.solution = self.simulation.solve()
                return self.solution
                
            except Exception as e2:
                # If still failing, suggest using a different model or reducing power
                print(f"Second attempt also failed: {e2}")
                print("\nSuggestion: Try using 'DFN' model for better stability with kW-scale powers")
                print("Or reduce the power values (consider power limits of your home battery)")
                max_power = self.get_max_safe_power()
                print(f"Recommended max power for this {self.capacity_kwh}kWh battery: {max_power:.1f}kW")
                raise e2
    
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
    
    def get_max_safe_power(self):
        """
        Get recommended maximum power for this battery capacity
        Typical home batteries: 0.5C to 1C discharge rate
        """
        # Conservative estimate: 0.7C rate
        max_power_kw = self.capacity_kwh * 0.7
        return max_power_kw
    
    def get_home_battery_specs(self):
        """
        Get specifications formatted for home battery context
        """
        specs = {
            "capacity_kwh": self.capacity_kwh,
            "capacity_ah": self.capacity_ah,
            "nominal_voltage_v": self.nominal_voltage,
            "max_recommended_power_kw": self.get_max_safe_power(),
            "energy_density_wh_kg": self.capacity_kwh * 1000 / 50,  # Assume ~50kg for home battery
            "typical_daily_cycles": 1,
            "typical_applications": ["Solar energy storage", "Peak shaving", "Backup power"]
        }
        return specs
    
    def simulate_daily_home_usage(self, solar_profile_kw=None, load_profile_kw=None, 
                                 grid_limit_kw=5.0, initial_soc=0.5):
        """
        Simulate typical daily home usage with solar and load profiles
        
        Parameters:
        solar_profile_kw: list, solar generation profile in kW (24 hours)
        load_profile_kw: list, home load profile in kW (24 hours) 
        grid_limit_kw: float, maximum grid import/export in kW
        initial_soc: float, starting state of charge
        
        Returns:
        dict: Daily simulation results
        """
        if solar_profile_kw is None:
            # Default solar profile (peak at midday)
            solar_profile_kw = [0, 0, 0, 0, 0, 0, 0.5, 2, 4, 6, 7, 8,
                               8.5, 8, 7, 6, 4, 2, 0.5, 0, 0, 0, 0, 0]
        
        if load_profile_kw is None:
            # Default residential load profile
            load_profile_kw = [2, 1.5, 1.2, 1, 1, 1.5, 3, 4, 3, 2.5, 2, 2,
                              2.5, 2, 2, 2.5, 3.5, 5, 6, 4.5, 3.5, 3, 2.5, 2]
        
        # Calculate net power (negative = excess solar for charging)
        net_power_kw = []
        for hour in range(24):
            net = load_profile_kw[hour] - solar_profile_kw[hour]
            
            # Limit by battery max power
            max_power = self.get_max_safe_power()
            net = max(-max_power, min(max_power, net))
            
            net_power_kw.append(net)
        
        # Create time durations (1 hour each)
        durations = [1.0] * 24
        
        # Run simulation
        solution = self.simulate_power_profile(
            power_values_kw=net_power_kw,
            time_durations=durations,
            initial_soc=initial_soc,
            safe_mode=True
        )
        
        # Analyze results
        results = {
            "solar_generation_kwh": sum(solar_profile_kw),
            "home_consumption_kwh": sum(load_profile_kw),
            "net_power_profile_kw": net_power_kw,
            "battery_final_soc": self.get_battery_state()["soc"],
            "energy_cycled_kwh": abs(self.get_battery_state()["energy_consumed_Wh"]) / 1000,
            "simulation_successful": True
        }
        
        return results


def main():
    """
    Example usage for home battery storage simulation
    """
    print("=== Home Battery Storage Simulation ===")
    
    # Create a typical home battery system (Tesla Powerwall-like)
    battery = BatterySimulator(
        model_type="SPM",      # Efficient for home scale
        capacity_kwh=13.5,     # Tesla Powerwall 2 capacity
        nominal_voltage=400.0   # Typical home battery voltage
    )
    
    # Display battery specifications
    specs = battery.get_home_battery_specs()
    print(f"\nBattery Specifications:")
    print(f"  Capacity: {specs['capacity_kwh']} kWh ({specs['capacity_ah']:.1f} Ah)")
    print(f"  Nominal Voltage: {specs['nominal_voltage_v']} V")
    print(f"  Max Recommended Power: {specs['max_recommended_power_kw']:.1f} kW")
    print(f"  Applications: {', '.join(specs['typical_applications'])}")
    
    # Example 1: Simple power profile in kW (home scale)
    print(f"\n=== Example 1: Basic Home Usage Pattern ===")
    
    # Typical home power profile (in kW, not W!)
    power_profile_kw = [3.0, -5.0, 2.5, 0, -3.0, 4.0]  # kW values
    time_durations = [1.0, 2.0, 1.5, 0.5, 1.0, 1.0]    # hours
    
    print(f"Power profile: {power_profile_kw} kW")
    print(f"Time durations: {time_durations} h")
    print("(Positive = discharge/home consumption, Negative = charge/solar excess)")
    
    try:
        # Run simulation
        solution = battery.simulate_power_profile(
            power_values_kw=power_profile_kw,
            time_durations=time_durations,
            initial_soc=0.5,  # Start at 50% charge
            safe_mode=True
        )
        
        # Get results
        state = battery.get_battery_state()
        
        print(f"\n--- Simulation Results ---")
        print(f"Total simulation time: {state['time_h']:.1f} hours")
        print(f"Initial SOC: 50% → Final SOC: {state['soc']*100:.1f}%")
        print(f"Final voltage: {state['voltage_V']:.2f} V")
        print(f"Energy throughput: {abs(state['energy_consumed_Wh'])/1000:.2f} kWh")
        print(f"Remaining capacity: {state['soc']*battery.capacity_kwh:.1f} kWh")
        
        print("✓ Basic home battery simulation successful!")
        
    except Exception as e:
        print(f"❌ Basic simulation failed: {e}")
    
    # Example 2: Daily solar + home load simulation
    print(f"\n=== Example 2: Daily Solar + Home Load Simulation ===")
    
    try:
        # Create new battery instance for daily simulation
        daily_battery = BatterySimulator(
            model_type="DFN",      # More robust for complex profiles
            capacity_kwh=10.0,     # 10 kWh home battery
            nominal_voltage=400.0
        )
        
        # Custom solar profile (kW) - sunny day
        solar_kw = [0, 0, 0, 0, 0, 0, 0.2, 1.5, 3.5, 5.5, 7.0, 8.0,
                   8.5, 8.0, 7.5, 6.0, 4.0, 2.0, 0.5, 0, 0, 0, 0, 0]
        
        # Home load profile (kW) - typical family
        load_kw = [1.5, 1.0, 0.8, 0.8, 1.0, 2.0, 3.5, 4.0, 3.0, 2.5, 2.0, 2.2,
                  2.5, 2.0, 2.0, 2.5, 3.5, 5.5, 6.0, 4.5, 3.5, 3.0, 2.5, 2.0]
        
        results = daily_battery.simulate_daily_home_usage(
            solar_profile_kw=solar_kw,
            load_profile_kw=load_kw,
            initial_soc=0.2  # Start day at 20%
        )
        
        print(f"Solar generation: {results['solar_generation_kwh']:.1f} kWh")
        print(f"Home consumption: {results['home_consumption_kwh']:.1f} kWh")
        print(f"Net surplus: {results['solar_generation_kwh'] - results['home_consumption_kwh']:.1f} kWh")
        print(f"Battery: 20% → {results['battery_final_soc']*100:.1f}% SOC")
        print(f"Energy cycled through battery: {results['energy_cycled_kwh']:.1f} kWh")
        
        print("✓ Daily home simulation successful!")
        
        # Plot the daily results
        daily_battery.plot_detailed_analysis()
        
    except Exception as e:
        print(f"❌ Daily simulation failed: {e}")
        print("Tip: Try reducing solar/load power values or use DFN model")
    
    print(f"\n=== Home Battery Simulation Complete ===")
    print("Key insights:")
    print("• Home batteries typically handle 1-10 kW power levels")
    print("• Daily cycling helps store solar energy for evening use")
    print("• Battery capacity should match 1-2 days of essential home loads")
    print("• Consider peak shaving and backup power applications")


def simulate_custom_power(power_values_kw, durations, initial_soc=1.0, model_type="SPM", 
                         capacity_kwh=10.0, safe_mode=True):
    """
    Convenience function to quickly simulate home battery with custom power profile
    
    Parameters:
    power_values_kw: list of power values in kW (+ = discharge, - = charge)
    durations: list of time durations in hours
    initial_soc: initial state of charge (0-1)
    model_type: str, battery model type ("SPM", "DFN", "SPMe")
    capacity_kwh: float, battery capacity in kWh
    safe_mode: bool, whether to use conservative solver settings
    
    Returns:
    BatterySimulator object with results
    """
    battery = BatterySimulator(model_type=model_type, capacity_kwh=capacity_kwh)
    battery.simulate_power_profile(power_values_kw, durations, initial_soc, safe_mode=safe_mode)
    return battery


def simulate_home_battery_day(capacity_kwh=10.0, solar_peak_kw=8.0, max_load_kw=6.0, 
                             model_type="DFN", initial_soc=0.3):
    """
    Simulate a typical day for a home battery system
    
    Parameters:
    capacity_kwh: float, battery capacity in kWh
    solar_peak_kw: float, peak solar generation in kW
    max_load_kw: float, maximum home load in kW
    model_type: str, battery model type
    initial_soc: float, starting state of charge
    
    Returns:
    dict: Daily simulation results and battery object
    """
    print(f"Simulating {capacity_kwh}kWh home battery for 24 hours...")
    
    battery = BatterySimulator(
        model_type=model_type, 
        capacity_kwh=capacity_kwh,
        nominal_voltage=400.0
    )
    
    # Generate realistic profiles
    # Solar: peak at noon, zero at night
    solar_profile = []
    for hour in range(24):
        if 6 <= hour <= 18:
            # Parabolic solar curve
            solar = solar_peak_kw * (1 - ((hour - 12) / 6) ** 2)
            solar = max(0, solar)
        else:
            solar = 0
        solar_profile.append(solar)
    
    # Load: higher in morning/evening, lower at night
    load_profile = []
    base_load = max_load_kw * 0.3  # Base load (always on appliances)
    for hour in range(24):
        if 6 <= hour <= 9 or 17 <= hour <= 22:
            # Peak usage times
            load = base_load + max_load_kw * 0.7
        elif 10 <= hour <= 16:
            # Daytime usage
            load = base_load + max_load_kw * 0.4
        else:
            # Night usage
            load = base_load
        load_profile.append(load)
    
    # Run daily simulation
    results = battery.simulate_daily_home_usage(
        solar_profile_kw=solar_profile,
        load_profile_kw=load_profile,
        initial_soc=initial_soc
    )
    
    results["battery"] = battery
    results["solar_profile"] = solar_profile
    results["load_profile"] = load_profile
    
    return results


def test_model_stability(model_type="SPM", test_powers=[1, 5, 10, 15, 20], 
                        duration=0.1, initial_soc=0.8):
    """
    Test which power values work well with a given model
    
    Parameters:
    model_type: str, battery model type to test
    test_powers: list, power values to test (positive = discharge)
    duration: float, test duration in hours
    initial_soc: float, initial state of charge
    
    Returns:
    dict: Results showing which power values worked
    """
    print(f"Testing {model_type} model stability...")
    results = {"successful": [], "failed": []}
    
    for power in test_powers:
        try:
            print(f"  Testing {power}W discharge...", end="")
            battery = BatterySimulator(model_type=model_type)
            battery.simulate_power_profile([power], [duration], initial_soc, safe_mode=True)
            results["successful"].append(power)
            print(" ✓")
        except Exception as e:
            results["failed"].append(power)
            print(" ✗")
    
    print(f"\nResults for {model_type}:")
    print(f"  Successful powers: {results['successful']} W")
    print(f"  Failed powers: {results['failed']} W")
    
    if results["successful"]:
        max_safe = max(results["successful"])
        print(f"  Recommended max power: {max_safe} W")
    
    return results


if __name__ == "__main__":
    main()