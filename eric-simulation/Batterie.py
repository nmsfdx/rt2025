'''

Bei gegebener Batteriekapazität die Lade und entladekurve ermitteln -> in CSV speichern.
Daraus gleichung erstellen lassen für den SOC


    Realistische Simulation einer Batterie

    Parameter:
        - minimale Ladespannung -> Vmin
        - maximale Ladespannug -> vmax
        - Batteriekapazität -> Bat_CAP
        - Anzahl der parallelen Batteriezellen- > CellBat
        - initale Batterieladung -> I_SOC
    Eingänge:
        - Lade oder entladeLeistung -> P
    Ausgang:
        - State of Charge -> SOC
        - entladene Batteriekapazität -> C
        - entladene Energie -> P_BAT [Wh]
        - Simulationszeit der Batterie ->tSimBat
'''

import pybamm
import matplotlib.pyplot as plt
import mosaik_api_v3
import numpy as np

Meta = {
    'api_version': '3.0',
    'type': 'time-based',
    'models': {
        'BatterySimulator': {
            'public': True,
            'params': ['Vmin',
                       'Vmax',
                       'Bat_CAP',
                       'CellBat',
                       'I_SOC'
                       ],  #parameter
            'attrs': ['P',
                      'SOC',
                      'C',
                      ' P_BAT',
                      'tSimBat'
                      ]
        }
    },
}
# ---------------------------------------------------------------------------------------------------
class BatterySimulator(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(Meta) #speichert Metadaten im meta-Feld

# ---------------------------------------------------------------------------------------------------

    def init(self, sid, **sim_params ):
        '''
            :param sid:
            :param sim_params: Simulationsparameter
            :return: Metadaten
        '''

        #Ermitteln der übergebenen Simulationsparameter
        self.step_size = sim_params.get('step_size', 60)
        self.Vmin = sim_params.get('Vmin',0)
        self.Vmax = sim_params.get('Vmax',4.2)
        self.SOC_INIT  = sim_params.get('I_SOC',0)
        self.Capacity_BAT = sim_params.get('Bat_CAP', 100)
        self.numberOfCells = sim_params.get('CellBat', 10000)

        model_type = sim_params.get('Model')

        #definiere welches Batteriemodell verwendet werden soll
        if model_type == "DFN":
            self.model = pybamm.lithium_ion.DFN(options={"calculate discharge energy": "true"})
        elif model_type == "SPM":
            self.model = pybamm.lithium_ion.SPM(options={"calculate discharge energy": "true"})
        elif model_type == "SPMe":
            self.model = pybamm.lithium_ion.SPMe(options={"calculate discharge energy": "true"})
        else:
            self.model = pybamm.lithium_ion.DFN()

        #sonstige variablen
        self.eid_prefix = 'BatterySimulator'
        self.entities = []
        self.results = []
        self.output = {}

        return self.meta

# ---------------------------------------------------------------------------------------------------

    def create(self, num, model, **model_params):
        '''
            :param num: Anzahl an entitäten
            :param model: Name des Models
            :param model_params:
            :return: Möglichkeit verschiedene Parameter für Entitäten
        '''
        entities = []
        for i in range(num):
            eid = f'{model}_{i}'
            entities.append({'eid': eid, 'type': model})
            self.entities.append(eid)
        return entities

# ----------------------------------------------------------------------------------------------------------------------

    def step(self, time, inputs, max_advance):
        '''
            :param time: Simulationszeit
            :param inputs: Eingabgewerte für einen Schritt
            :param max_advance: für erweiterte ereignisbasierte Simulatoren relevant
            :return: Simulationsdauer
        '''
        for eid, ent in inputs.items():
            # Ermitteln der Engangswerte
            power = ent['P']['CSV_DATA-0.InputFeeder0'] # [Signalname][Simulatorquelle des Signales]

            # ----------------------------------------------------------------------------------------------------------
            #Modell
            #-----------------------------------------------------------------------------------------------------------
            if power > 0:
                expermient_text = f"Charge at {power} W for {time} s or until {self.Vmax} V"
            elif power < 0:
                expermient_text = f"Discharge at {abs(power)} W for {time} s or until {self.Vmin} V"

            parameter_values = pybamm.ParameterValues("Chen2020")
            # parameter_values["Current function [A]"] = 1200 # negativer Strom lädt und positiver entlädt
            #parameter_values["Lower voltage cut-off [V]"] = 2.5
            parameter_values["Nominal cell capacity [A.h]"] = self.Capacity_BAT
            # parameter_values["Number of cells connected in series to make a battery"] = 10000
            parameter_values["Number of electrodes connected in parallel to make a cell"] = self.numberOfCells  # höhere Ströme möglich
            #parameter_values["Open-circuit voltage at 0% SOC [V]"] = 2.5
            # parameter_values["Open-circuit voltage at 100% SOC [V]"] = 4.2

            model = pybamm.lithium_ion.DFN(options={"calculate discharge energy": "true"})
            sim = pybamm.Simulation(model, parameter_values=parameter_values,
                                    experiment=pybamm.Experiment([expermient_text]))

            sol = sim.solve([0, self.step_size], initial_soc=self.SOC_INIT)
            # sim.plot()

            # Holle Simulationsparameter für komplette Simulation (geeignet um Diagramme zu machen)
            time_bat = sol["Time [h]"].entries
            voltage = sol["Terminal voltage [V]"].entries
            current = sol["Current [A]"].entries
            soc = sol["Discharge capacity [A.h]"].entries
            power = sol['Power [W]'].entries
            energy = sol['Throughput energy [W.h]'].entries  # Wh -> Energie die über die Batterie geflossen ist
            though_cap = sol['Throughput capacity [A.h]'].entries
            initial_voltage = sol["Battery voltage [V]"].entries

            voltage_sim = voltage[-1]
            initial_voltage_sim = voltage[0]
            power_sim = power[-1] if len(power) > 0 else 0
            used_capacity_sim = soc[-1] if len(soc) > 0 else 0
            time_sim = time_bat[-1] if len(time_bat) > 0 else 0
            current_sim = current[-1] if len(current) > 0 else 0
            cons_energy_sim = energy[-1] if len(energy) > 0 else 0
            though_cap_sim = though_cap[-1] if len(though_cap) > 0 else 0

            # SOC = Anfangs-SOC + Geladene Kapazität / Gesamtkapazität
            self.SOC_INIT -= used_capacity_sim / (self.Capacity_BAT * self.numberOfCells)

            if self.SOC_INIT > 1:
                self.SOC_INIT = 1
            elif self.SOC_INIT < 0:
                self.SOC_INIT = 0

            print("Battery Simulation results:")
            print(f'Simulation Time: {time_sim} h')
            print(f'Final Battery voltage: {voltage_sim} V')
            print(f'Startspannung: {initial_voltage_sim} V')
            print(f'current: {current_sim} A')
            print(f'final SOC: {self.SOC_INIT * 100} %')
            print(f'Discharged Battery Capacity: {used_capacity_sim} A.h')
            #print(f'Throughput Capacity: {though_cap_sim} A.h')
            print(f'Consumed Energy: {cons_energy_sim} W.h')

            # ----------------------------------------------------------------------------------------------------------

            # Ausgabewerte
            for eid in self.entities:
                self.output[eid] = {
                    'SOC': self.SOC_INIT,
                    'C': used_capacity_sim,
                    'P_BAT': cons_energy_sim,
                    'tSimBat': time_sim,
}
        return time + self.step_size

# ----------------------------------------------------------------------------------------------------------------------
    def get_data(self, outputs):
        return self.output


'''
Programmcode zum bestimmen der entlade und laderate Abhängig des SOC aus generierten Daten des Laden und entladens einer 
realen Batterie mit Pybamm

-> mit Pybamm am Anfang batterie simulieren -> erzeugen Daten für SOC in Abhängigkeit der Zeit für einmal laden und einmal entladen
-> Daraus formeln erstellen die dann in die constraints der optimierung kommen!
-> SOC muss in Wh angegeben werden. Brauche ebenfalls maximale Kapazität in Wh

Es werden zwei formeln bestimmt die man in die constrains einsetzen kann.
einmal SOC
einmal max entladerate
einmal max laderate

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# 1. Sigmoidfunktion Laden (anstiegend)
def sigmoid_lade(t, L, k, t0):
    return L / (1 + np.exp(-k * (t - t0)))

# 2. Ableitung der Ladekurve (Laderate)
def sigmoid_lade_ableitung(t, L, k, t0):
    exp_term = np.exp(-k * (t - t0))
    return (L * k * exp_term) / ((1 + exp_term) ** 2)

# 3. Sigmoidfunktion Entladen (fallend)
def sigmoid_entlade(t, L, k, t0):
    return L / (1 + np.exp(k * (t - t0)))  # Beachte +k (fallende Sigmoid)

# 4. Ableitung der Entladekurve (Entladerate), immer positiv
def sigmoid_entlade_ableitung(t, L, k, t0):
    exp_term = np.exp(k * (t - t0))
    return (L * k * exp_term) / ((1 + exp_term) ** 2)

# Lade CSV Daten
def lade_daten(pfad_csv):
    df = pd.read_csv(pfad_csv)
    return df

# Sigmoid fitten (allgemein)
def fit_sigmoid(func, zeit, soc):
    initial_guess = [max(soc), 0.005, np.median(zeit)]
    params, _ = curve_fit(func, zeit, soc, p0=initial_guess, maxfev=10000)
    return params

# Max. Rate berechnen (bei t0)
def max_rate(L, k):
    return (L * k) / 4

# ... (restlicher Code bleibt gleich, siehe vorher)

def lineare_approximation_sigmoid(func_soc, func_ableitung, params):
    L, k, t0 = params
    soc_t0 = func_soc(t0, L, k, t0)
    slope_t0 = func_ableitung(t0, L, k, t0)
    m = slope_t0
    b = soc_t0 - m * t0
    return m, b

if __name__ == "__main__":
    # Daten laden
    df = lade_daten("akku_daten.csv")
    zeit = df['Zeit_s'].values
    
    # --- Ladekurve ---
    soc_lade = df['SoC_Lade'].values
    params_lade = fit_sigmoid(sigmoid_lade, zeit, soc_lade)
    L_l, k_l, t0_l = params_lade
    print(f"Ladekurve SoC(t) = {L_l:.2f} / (1 + exp(-{k_l:.6f} * (t - {t0_l:.2f})))")
    print(f"Max. Laderate (Steigung) = {max_rate(L_l, k_l)*60:.2f} %/min")
    print(f"Laderate(t) = (L * k * exp(-k(t - t0))) / (1 + exp(-k(t - t0)))^2")

    # Lineare Approximation Laden um t0
    m_lade, b_lade = lineare_approximation_sigmoid(sigmoid_lade, sigmoid_lade_ableitung, params_lade)
    print(f"Lineare Approx. Laden: SoC(t) ≈ {m_lade:.6f} * t + {b_lade:.2f}")

    # --- Entladekurve ---
    soc_entlade = df['SoC_Entlade'].values
    params_ent = fit_sigmoid(sigmoid_entlade, zeit, soc_entlade)
    L_e, k_e, t0_e = params_ent
    print(f"\nEntladekurve SoC(t) = {L_e:.2f} / (1 + exp({k_e:.6f} * (t - {t0_e:.2f})))")
    print(f"Max. Entladerate (Steigung) = {max_rate(L_e, k_e)*60:.2f} %/min")
    print(f"Entladerate(t) = (L * k * exp(k(t - t0))) / (1 + exp(k(t - t0)))^2")

    # Lineare Approximation Entladen um t0
    m_ent, b_ent = lineare_approximation_sigmoid(sigmoid_entlade, sigmoid_entlade_ableitung, params_ent)
    print(f"Lineare Approx. Entladen: SoC(t) ≈ {m_ent:.6f} * t + {b_ent:.2f}")

    # ... (Plotten wie vorher)



'''