"""
Home Battery Storage Examples
Demonstrates realistic home energy storage scenarios
"""

import pybamm
import numpy as np
import matplotlib.pyplot as plt

# Import the updated BatterySimulator
exec(open('bat-speicher.py').read())

def tesla_powerwall_example():
    """Simulate a Tesla Powerwall-like system"""
    print("=== Tesla Powerwall 2 Simulation ===")
    
    # Tesla Powerwall 2 specs
    battery = BatterySimulator(
        model_type="DFN",       # Robust model for home applications
        capacity_kwh=13.5,      # Powerwall 2 capacity
        nominal_voltage=400.0   # Typical voltage
    )
    
    specs = battery.get_home_battery_specs()
    print(f"Battery: {specs['capacity_kwh']} kWh, Max Power: {specs['max_recommended_power_kw']:.1f} kW")
    
    # Typical usage: morning discharge, solar charging, evening discharge
    scenario = [
        # Morning (7-9 AM): High consumption, no solar
        (4.0, 2.0),   # 4kW discharge for 2 hours
        
        # Day (9 AM-4 PM): Solar charging excess
        (-3.0, 7.0),  # 3kW charge for 7 hours (solar excess)
        
        # Evening (4-10 PM): High consumption
        (5.0, 6.0),   # 5kW discharge for 6 hours
        
        # Night (10 PM-7 AM): Low consumption
        (1.0, 9.0),   # 1kW discharge for 9 hours
    ]
    
    powers = [p[0] for p in scenario]
    durations = [p[1] for p in scenario]
    
    print(f"Daily scenario: {powers} kW over {durations} hours")
    
    try:
        battery.simulate_power_profile(
            power_values_kw=powers,
            time_durations=durations,
            initial_soc=0.9  # Start at 90%
        )
        
        state = battery.get_battery_state()
        print(f"Day result: 90% → {state['soc']*100:.1f}% SOC")
        print(f"Energy cycled: {abs(state['energy_consumed_Wh'])/1000:.1f} kWh")
        
        return True
        
    except Exception as e:
        print(f"Failed: {e}")
        return False

def solar_home_example():
    """Simulate home with solar panels and battery"""
    print("\n=== Solar Home with 10kWh Battery ===")
    
    # Run a full day simulation
    results = simulate_home_battery_day(
        capacity_kwh=10.0,      # Medium home battery
        solar_peak_kw=8.0,      # 8kW solar system
        max_load_kw=5.0,        # 5kW max home load
        model_type="DFN",
        initial_soc=0.2         # Start day with low battery
    )
    
    print(f"Solar generated: {results['solar_generation_kwh']:.1f} kWh")
    print(f"Home consumed: {results['home_consumption_kwh']:.1f} kWh")
    print(f"Battery: 20% → {results['battery_final_soc']*100:.1f}% SOC")
    print(f"Self-sufficiency: {(1 - abs(min(0, results['solar_generation_kwh'] - results['home_consumption_kwh'])) / results['home_consumption_kwh']) * 100:.1f}%")
    
    return results

def compare_battery_sizes():
    """Compare different home battery sizes"""
    print("\n=== Comparing Battery Sizes ===")
    
    sizes = [5, 10, 15, 20]  # kWh
    
    for capacity in sizes:
        print(f"\n--- {capacity} kWh Battery ---")
        
        battery = BatterySimulator(
            model_type="SPM",  # Faster for comparison
            capacity_kwh=capacity,
            nominal_voltage=400.0
        )
        
        specs = battery.get_home_battery_specs()
        
        # Test with standard 6 hours of 3kW discharge
        try:
            battery.simulate_power_profile(
                power_values_kw=[3.0],
                time_durations=[6.0],
                initial_soc=1.0
            )
            
            state = battery.get_battery_state()
            remaining_kwh = state['soc'] * capacity
            used_kwh = (1 - state['soc']) * capacity
            
            print(f"  Max power: {specs['max_recommended_power_kw']:.1f} kW")
            print(f"  After 6h @ 3kW: {remaining_kwh:.1f} kWh remaining ({state['soc']*100:.0f}%)")
            print(f"  Backup time @ 2kW: {remaining_kwh/2:.1f} hours")
            
        except Exception as e:
            print(f"  Simulation failed: {e}")

def peak_shaving_example():
    """Demonstrate peak shaving to reduce electricity costs"""
    print("\n=== Peak Shaving Example ===")
    print("Strategy: Charge during off-peak hours, discharge during peak hours")
    
    battery = BatterySimulator(
        model_type="DFN",
        capacity_kwh=15.0,  # Large home battery
        nominal_voltage=400.0
    )
    
    # Time-of-use electricity rates simulation
    # Off-peak: 11 PM - 7 AM (charge battery)
    # Peak: 4 PM - 9 PM (discharge battery)
    # Standard: All other times
    
    daily_pattern = [
        # Off-peak charging (11 PM - 7 AM) - 8 hours
        (-7.0, 8.0),   # Charge at 7kW for 8 hours
        
        # Standard hours (7 AM - 4 PM) - 9 hours  
        (2.0, 9.0),    # Light discharge at 2kW for 9 hours
        
        # Peak hours (4 PM - 9 PM) - 5 hours
        (8.0, 5.0),    # Heavy discharge at 8kW for 5 hours
        
        # Evening transition (9 PM - 11 PM) - 2 hours
        (3.0, 2.0),    # Moderate discharge at 3kW for 2 hours
    ]
    
    powers = [p[0] for p in daily_pattern]
    durations = [p[1] for p in daily_pattern]
    
    print(f"Pattern: {powers} kW over {durations} hours")
    
    try:
        battery.simulate_power_profile(
            power_values_kw=powers,
            time_durations=durations,
            initial_soc=0.1  # Start with empty battery
        )
        
        state = battery.get_battery_state()
        energy_shifted = abs(state['energy_consumed_Wh']) / 1000
        
        print(f"Battery: 10% → {state['soc']*100:.1f}% SOC")
        print(f"Energy shifted from off-peak to peak: {energy_shifted:.1f} kWh")
        print(f"Potential daily savings: ${energy_shifted * 0.25:.2f} (assuming $0.25/kWh difference)")
        
    except Exception as e:
        print(f"Peak shaving simulation failed: {e}")

if __name__ == "__main__":
    print("Home Battery Storage Simulation Examples\n")
    
    # Run examples
    tesla_powerwall_example()
    solar_results = solar_home_example()
    compare_battery_sizes()
    peak_shaving_example()
    
    print("\n=== Summary ===")
    print("✓ Home batteries typically range from 5-20 kWh")
    print("✓ Power ratings usually 3-10 kW for residential")
    print("✓ Main applications:")
    print("  • Solar energy storage")
    print("  • Peak demand shaving")
    print("  • Backup power during outages")
    print("  • Time-of-use optimization")
    print("✓ Daily cycling is normal and expected")
    
    # Plot the solar home results if successful
    if 'solar_results' in locals() and solar_results.get('simulation_successful'):
        try:
            solar_results['battery'].plot_detailed_analysis()
        except:
            pass
