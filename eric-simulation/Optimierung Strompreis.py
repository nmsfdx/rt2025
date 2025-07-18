'''
Die Optimierung sammelt alle Daten und berechnet am Ende in finalize die Optimierung mit allen Daten
Finalize führt einen Plot zum Anzeigen des Ergebniss aus.

Es wird der Gewinn maximiert. Heißt auch die Optimierung kauft Strom bilig ein und verkauft ihn dann wieder!

Die optimierung bestimmt erst mit allen Daten der Simulation wie die Batterie geladen oder entladen wird.
    => Daher keine Einbindung eines Pybamm Batteriemodelles in die Simulation möglich!
    => einbinden einer Gleichung für das Verhalten der Batterie wäre möglich!

Parameter:
    - Batteriekapazität in Wh -> C_max
    - max. Lade- / Entladeleistung in Wh -> Wh_BAT_max
    - Startladung der Batterie -> C_INIT

Eingänge:
    - Strompreis in €/Wh -> cost_Wh
    - Haushaltslast in Wh -> Wh_H
    - PV Leistungsproduktion -> Wh_PV
    - benötigte elektrische Leistung -> Wh_Pel
    - Raumtemperatur -> T
    - Warmwassertemperatur Heizkessel Sensor 1 -> T_SENSOR1
    - Warmwassertemperatur Heizkessel Sensor 2 -> T_SENSOR2
    - Warmwassertemperatur Heizkessel Sensor 3 -> T_SENSOR3
    - ...
    - Warmwassertemperatur Heizkessel Sensor 8 -> T_SENSOR8
    - Wärmebeadarf Hausalt -> Q_H
    - Solarwärme -> Q_PV


Ergänzungsmöglichkeit testen, Autarkie mit in die Optimierung einbinden:

    # Gesamtstrombedarf
    gesamt_last = cp.sum(self.Wh_H + self.Wh_Pel)

    # Gesamt-Netzbezug
    gesamt_einkauf = cp.sum(einkauf)

    # Autarkiegrad (zwischen 0 und 1)
    autarkie = 1 - gesamt_einkauf / gesamt_last

    # Gewinn = Einspeisung - Einkauf (beide in Wh)
    gewinn = cp.sum(cp.multiply(einspeisung, self.cost_Wh) - cp.multiply(einkauf, self.cost_Wh))

    # Gewichtung: α ∈ [0, 1]; z. B. 0.7 = 70% Gewinn, 30% Autarkie
    alpha = 0.7

    # Zielfunktion
    objective = cp.Maximize(
        alpha * gewinn + (1 - alpha) * autarkie * gesamt_last  # optional: * gesamt_last zur Skalierung
    )

    # Sicherstellen, dass Autarkiegrad im gültigen Bereich liegt
    constraints += [
        einkauf >= 0,                # Netzbezug darf nicht negativ werden
        einspeisung >= 0,            # Keine negative Einspeisung
        autarkie >= 0,               # Technisch unnötig, aber manchmal hilfreich für numerische Stabilität
        autarkie <= 1,
    ]
    # Optional: Mindestautarkie erzwingen (z. B. 80%)
    constraints += [
        autarkie >= 0.3
    ]
    print("Autarkiegrad:", 1 - einkauf.value.sum() / (self.Wh_H + self.Wh_Pel).sum())
    print("Gewinn (EUR):", gewinn.value)

'''


import mosaik_api_v3
import numpy as np
import cvxpy as cp
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------------------------------------------------
# Modellsimulation
# ----------------------------------------------------------------------------------------------------------------------

Meta = {
    'api_version': '3.0',
    'type': 'hybrid',
    'models': {
        'OptimierungSim': {
            'public': True,
            'params': ['C_max',
                       'Wh_BAT_max',
                       'C_INIT'
                       ],
            'attrs': ['cost_Wh',
                      'Wh_H',
                      'Wh_PV',
                      'Wh_Pel',
                      'T',
                      'T_SENSOR1',
                      'T_SENSOR2',
                      'T_SENSOR3',
                      'T_SENSOR4',
                      'T_SENSOR5',
                      'T_SENSOR6',
                      'T_SENSOR7',
                      'T_SENSOR8'
                      ],
        }
    },
}
# ----------------------------------------------------------------------------------------------------------------------
class OptimierungSim(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(Meta) #speichert Metadaten im meta-Feld

# ----------------------------------------------------------------------------------------------------------------------
    def init(self, sid, **sim_params ):
        '''
            :param sid:
            :param sim_params: Simulationsparameter
            :return: Metadaten
        '''
        # Ermitteln der Simulationsparameter
        self.step_size = sim_params.get('step_size', 360)
        self.C_max = sim_params.get('C_max', 100000)
        self.Wh_BAT_max = sim_params.get('Wh_BAT_max', 1000)
        self.C_INIT = sim_params.get('C_INIT', 0)

        #definieren von benötigten Variablen, listen usw.
        self.eid_prefix = 'OptimierungSim'
        self.entities = []
        self.results = []
        self.output = {} # Ausgangswerte

        #Arrays
        self.time = np.array([])# X-zeitachse
        self.cost_Wh = np.array([])
        self.Wh_H = np.array([])
        self.Wh_PV = np.array([])
        self.Wh_Pel = np.array([])
        self.T_ARR = np.array([])

        #variablen
        self.T = 0 # Zähler

        return self.meta

# ----------------------------------------------------------------------------------------------------------------------
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
            :return:
        '''
        for eid, ent in inputs.items():
            # ----------------------------------------------------------------------------------------------------------
            #Eingangswerte
            # ----------------------------------------------------------------------------------------------------------
            cost_Wh = ent['cost_Wh']['CSV-0.HWT_0'] #[Signalname][Simulatorquelle des Signales]
            Wh_H = ent['Wh_H']['CSV-0.HWT_0']
            Wh_PV = ent['Wh_PV']['CSV-0.HWT_0']
            Wh_Pel = ent['Wh_Pel']['HeatPumpSim-0.HeatPumpSim_0']
            T = ent['T']['RCSim-0.RCBuildingSim_0']
            T_SENSOR1 = ent['T_SENSOR1']['HotWaterTankSim-0.HotWaterTank_0']
            T_SENSOR2 = ent['T_SENSOR2']['HotWaterTankSim-0.HotWaterTank_0']
            T_SENSOR3 = ent['T_SENSOR3']['HotWaterTankSim-0.HotWaterTank_0']
            T_SENSOR4 = ent['T_SENSOR4']['HotWaterTankSim-0.HotWaterTank_0']
            T_SENSOR5 = ent['T_SENSOR5']['HotWaterTankSim-0.HotWaterTank_0']
            T_SENSOR6 = ent['T_SENSOR6']['HotWaterTankSim-0.HotWaterTank_0']
            T_SENSOR7 = ent['T_SENSOR7']['HotWaterTankSim-0.HotWaterTank_0']
            T_SENSOR8 = ent['T_SENSOR8']['HotWaterTankSim-0.HotWaterTank_0']

            # ----------------------------------------------------------------------------------------------------------
            #Speichern der eingehenden Parameter (runden auf 2 Nachkommastellen -> einfacher für Optimierung)
            # ----------------------------------------------------------------------------------------------------------
            self.time = np.append(self.time, round((self.step_size / 3600) * self.T , 4)) # X-zeitachse in Stunden
            self.cost_Wh = np.append(self.cost_Wh, round(cost_Wh, 4)) #in €/Wh
            self.Wh_H = np.append(self.Wh_H, round( Wh_H * (self.step_size / 3600), 4)) # Umrechnung in Wh nötigt
            self.Wh_PV = np.append(self.Wh_PV, round(Wh_PV * (self.step_size / 3600), 4)) # Umrechnung in Wh nötigt
            self.Wh_Pel = np.append(self.Wh_Pel, round(Wh_Pel, 4)) #in Wh
            self.T_ARR  = np.append(self.T_ARR, round(T, 4)) # in °C

            #print(f"\n--- Messewerte ---")
            #print(f'T Sensor 1 cc_out', T_SENSOR1)
            #print(f'T Sensor 2 H_out', T_SENSOR2)
            #print(f'T Sensor 3 hp_out', T_SENSOR3)
            #print(f'T Sensor 4 RQ out', T_SENSOR4)
            #print(f'T Sensor 5 cc_in', T_SENSOR5)
            #print(f'T Sensor 6 H_in', T_SENSOR6)
            #print(f'T Sensor 7 hp_in', T_SENSOR7)
            #print(f'Raumtemperatur:', T)

            self.T += 1 # hochzählen für Anzahl der Werte

            for eid in self.entities:
                self.output[eid] = {
                    'T': T,
                    'cost_Wh': cost_Wh,
                    'Wh_H' : Wh_H,
                    'Wh_PV': Wh_PV,
                    'Wh_Pel': Wh_Pel
                }
            # ----------------------------------------------------------------------------------------------------------
        return time + self.step_size

    def get_data(self, outputs):
        return self.output

    #-------------------------------------------------------------------------------------------------------------------
    #diese Funktion wird am Ende ausgeführt zur Berechnung der Optimierung
    # -------------------------------------------------------------------------------------------------------------------
    def finalize(self):
        entlade = cp.Variable(self.T)
        lade = cp.Variable(self.T)
        einspeisung = cp.Variable(self.T)
        einkauf = cp.Variable(self.T)
        soc = cp.Variable(self.T + 1)

        # --------------------------------------------------------------------------------------------------------------
        # Start SoC
        # --------------------------------------------------------------------------------------------------------------
        constraints = [soc[0] == self.C_INIT]
        '''
        for t in range(self.T):
            # Strombilanz: PV + Einkauf + Entladung = Last + WP + Einspeisung + Laden
            constraints += [
                self.Wh_PV[t] + einkauf[t] + entlade[t] == self.Wh_H[t] + self.Wh_Pel[t] + einspeisung[t] + lade[t],
                einkauf[t] >= 0,
                einspeisung[t] >= 0,
                entlade[t] >= 0,
                entlade[t] <= self.Wh_BAT_max,
                lade[t] >= 0,
                lade[t] <= self.Wh_BAT_max,
                soc[t + 1] == soc[t] + lade[t] - entlade[t],
                soc[t + 1] >= 0,
                soc[t + 1] <= self.C_max,
            ]
        '''
        # Strombilanz
        constraints += [
            self.Wh_PV + einkauf + entlade == self.Wh_H + self.Wh_Pel + einspeisung + lade
        ]

        # Begrenzungen für Ein-/Ausspeisung, Lade/Entladeleistung
        constraints += [
            einkauf >= 0,
            einspeisung >= 0,
            entlade >= 0,
            entlade <= self.Wh_BAT_max,
            lade >= 0,
            lade <= self.Wh_BAT_max,
        ]

        # SoC Entwicklung: soc[t+1] = soc[t] + lade[t] - entlade[t]
        # → ergibt T Gleichungen: soc[1:] == soc[:-1] + lade - entlade
        constraints += [
            soc[1:] == soc[:-1] + lade - entlade,
            soc[1:] >= 0,
            soc[1:] <= self.C_max,
        ]
        # Zielfunktion: Gewinn maximieren (Einspeisung * Preis - Einkauf * Preis)
        gewinn = cp.sum(cp.multiply(einspeisung, self.cost_Wh) - cp.multiply(einkauf, self.cost_Wh))
        objective = cp.Maximize(gewinn)

        # Problem lösen
        prob = cp.Problem(objective, constraints)
        prob.solve(solver=cp.MOSEK, verbose=True) # Solver OSQP findet bei 10000 Werten keine Lösung mehr!

        # --------------------------------------------------------------------------------------------------------------
        # Ausgabe des Ergebnisses der Simulation
        # --------------------------------------------------------------------------------------------------------------

        if prob.status != "optimal":
            print(f"Optimierung nicht erfolgreich: {prob.status}")
        else:
            print("Optimierung erfolgreich. Erstelle Diagramme")

            #berechnen der Autarkie
            pv_sum= np.sum(self.Wh_PV)
            net_sum = np.sum(einspeisung.value)
            home_sum = np.sum(self.Wh_H)
            wp_sum = np.sum(self.Wh_Pel)
            lade_sum = np.sum(lade.value)
            #entlade_sum = np.sum(entlade.value)
            einkauf_sum = np.sum(einkauf.value)

            #Die PV Energie wird komplett für den haushalt verwendet nur die benötigte Differenz wird eingekauft!!
            # Der Haushalt verbraucht viel mehr als die PV liefert
            print("Autarkiegrad: ", (pv_sum / (home_sum + wp_sum)) * 100)
            print("Autarkiegrad aus eingekaufter Energie: ", (1 - (einkauf_sum - net_sum) / (home_sum + wp_sum)) * 100)


            print(f"Gewinn (Euro): {prob.value:.2f}")
            #print(f"einkauf: {einkauf.value}")
            #print(f"einspeisung: {einspeisung.value}")
            #print(f"time ar: {self.T_ARR}")
            #print(f"cost: {self.cost_Wh}")
            #print(f"time: {self.time}")

            #Optimierungsergebnisse in CSV Eintragen


            #Plotten des Ergebnisses
            x = self.time
            fig, axs = plt.subplots(2, 2, figsize=(16, 16))
            axs = axs.flatten()

            axs[0].plot(x, self.Wh_Pel)
            axs[0].set_title("Wärmepumpenenergie")
            axs[0].set_xlabel("h")
            axs[0].set_ylabel("Wh")
            axs[0].grid(True)

            axs[1].plot(x, self.cost_Wh)
            axs[1].set_title("Stromkosten")
            axs[1].set_xlabel("h")
            axs[1].set_ylabel("€/Wh")
            axs[1].grid(True)

            axs[2].plot(x, self.T_ARR)
            axs[2].set_title("Innenraumtemperatur")
            axs[2].set_xlabel("h")
            axs[2].set_ylabel("°C")
            axs[2].grid(True)

            axs[3].plot(x, self.Wh_PV)
            axs[3].set_title("PV_Energie")
            axs[3].set_xlabel("h")
            axs[3].set_ylabel("Wh")
            axs[3].grid(True)

            '''
            #Plotten der Ergebnisse
            # Erstelle 4x2 Subplots
            fig, axs = plt.subplots(4, 2, figsize=(14, 16))
            axs = axs.flatten()
            
            axs[0].plot(x, einkauf.value)
            axs[0].set_title("Engekaufte Energie")
            axs[0].set_xlabel("min")
            axs[0].set_ylabel("Wh")
            axs[0].grid(True)

            axs[1].plot(x, einspeisung.value)
            axs[1].set_title("Eingespeiste Energie")
            axs[1].set_xlabel("min")
            axs[1].set_ylabel("Wh")
            axs[1].grid(True)

            axs[2].plot(x, self.Wh_Pel)
            axs[2].set_title("Wärmepumpenenergie")
            axs[2].set_xlabel("h")
            axs[2].set_ylabel("Wh")
            axs[2].grid(True)

            axs[3].plot(x, self.cost_Wh)
            axs[3].set_title("Stromkosten")
            axs[3].set_xlabel("h")
            axs[3].set_ylabel("€/Wh")
            axs[3].grid(True)
            

            axs[4].plot(x, entlade.value)
            axs[4].set_title("Batterieentladung")
            axs[4].set_xlabel("h")
            axs[4].set_ylabel("Wh")
            axs[4].grid(True)

            axs[5].plot(x, lade.value)
            axs[5].set_title("Batterieladung")
            axs[5].set_xlabel("h")
            axs[5].set_ylabel("Wh")
            axs[5].grid(True)

            axs[6].plot(x, self.T_ARR)
            axs[6].set_title("Raumtemperatur")
            axs[6].set_xlabel("Zeit [h]")
            axs[6].set_ylabel("°C")
            axs[6].grid(True)

            axs[7].plot(x, self.Wh_PV)
            axs[7].set_title("PV Leistung")
            axs[7].set_xlabel("W")
            axs[7].set_ylabel("°C")
            axs[7].grid(True)
            '''
            # Layout anpassen
            plt.tight_layout()
            plt.show()





