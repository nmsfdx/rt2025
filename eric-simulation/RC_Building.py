'''
Wäremabgabe durch den Heizkörper
    mit Q  = V * p * c * dT

    dT = Temperaturdifferenz Wasser vor und nach dem Heizkörper
    V = Volumenstrom
    p =  Wasserdichte
    c = spezifische Wäremkapazität von Wasser
    Q = Wärme in Joule [J]

    => gibt die Wärme Q an die in definierter Zeit t erzeugt wird. Heißt um die Leistung zu ermitteln, Q durch die
        Zeit teilen die der Erwärmungsprozess dauert da 1 J = 1Ws!

    Für SFH A Var 3:
        - Heizkörper dT = 50 / 40°C

verwenden eines 3R2C modells für den Gebäudetyp SFH A Var3:
Parameter:
    - Ai = 1.45
    - Ce = 20.72
    - Ci = 2.56
    - Rea = 15.14
    - Ria = 19.22
    - Rie = 0.99

Änderung der Raumtemperatur:
    dTi = [1/(Ci * Rie) * (Te - Ti) + 1/(Ci * Ria) * (Ta - Ti) + Ai/Ci * Ps + 1/Ci * (Ph + Pg)]dt + (sigma dwi)

Änderung der Temperatur der Gebäudehülle:

    dTe = [1/(Ce * Rie) * (Ti - Te) + 1/(Ce * Rea) * (Ta - Te)]dt + (sigma_e d_omega_e)

    (sigma dwi) und (sigma_e d_omega_e) sind thermisches Rauschen!

    => dTi geht dann an die Regelung. Das ist der Fehler der ausgeglichen werden muss

    # Temperaturen (variabel in der Simulation)
    Ti = 20.0  # Innentemperatur in °C
    Te = 18.0  # Temperatur der Gebäudehülle in °C
    Ta = 10.0  # Umgebungstemperatur (Außentemperatur) in °C

    # Leistungen (variabel in der Simulation)
    Ph = 1.5   # Heizleistung in kW (Beispiel: 1500 W) -> berechnen
    Pg = 0.3   # Interne Wärmegewinne in kW (Beispiel: 300 W)
    Ps = 0.2   # Solare Strahlung in kW/m^2 (Beispiel: 200 W/m^2) -> Berechnen mit Einstrahlung

    # Thermische Widerstände (Konstanten, aus Tabelle ableitbar, in °C/kW)
    Ria = 0.20 # Beispielwert: Thermischer Widerstand zwischen Innenraum und Umgebung
    Rie = 0.05 # Beispielwert: Thermischer Widerstand zwischen Innenraum und Gebäudehülle
    Rea = 0.15 # Beispielwert: Thermischer Widerstand zwischen Gebäudehülle und Umgebung

    # Thermische Kapazitäten (Konstanten, in kWh/°C)
    Ci = 0.20  # Beispielwert: Kapazität des Innenraums
    Ce = 0.80  # Beispielwert: Kapazität der Gebäudehülle

    # Flächen (Konstanten, in m^2)
    Ai = 15.0  # Beispielwert: Effektive Fensterfläche für die Absorption solarer Gewinne auf die Innenluft

    # Stochastische Parameter (Konstanten)
    sigma = 0.001 # Inkrementelle Varianz des Wiener-Prozesses (Beispielwert)

    # Zeitschritt (Konstante)
    dt = 60 # Zeitschritt in Sekunden (z.B. 1 Minute) -> step!!


------------------------------------------------------------------------------------------------------------------------
Parameter:
        - Effektive Fensterfläche -> Ai
        - Kapazität des Innenraums -> Ci [
        - Kapazität der Gebäudehülle -> Ce
        - Thermischer Widerstand zwischen Innenraum und Umgebung ->Ria
        - Thermischer Widerstand zwischen Innenraum und Gebäudehülle -> Rie
        - Thermischer Widerstand zwischen Gebäudehülle und Umgebung -> Rea
        - Wasserdichte -> p
        - spezifische Wäremkapazität von Wasser -> c
        - Initiale Raumtemperatur -> Ti_INIT
        - initiale Gebäudehülletemperatur -> Te_INIT
        - Neigung der Einstrahlfläche -> A_DEG
        - Bodenreflexionsgrad -> refl_b
        - Volumenstrom -> F

    Eingänge:
        - Umgebungstemperatur -> Ta
        - Globale horizontale Einstrahlung -> GHI
        - Diffuse horizontale Einstrahlung -> DHI
        - Sonneneinstrahlungswinkel -> SUN_DEG
        - Sonnenlotwinkel -> LOT_DEG
        - Wassertemperatur IN von Warmwasserspeicher -> T_IN

    Ausgang:
        Zu Warmwasserspeeicher. Volumentstrom wird durch Parameter festgelegt
        - Wasservolumenstrom OUT für Warmwasserspeicher ->  F_OUT = -F_IN
        - Wasservolumenstrom IN von Warmwasserspeicher -> F_IN
        - Wassertemperatur OUT für Warmwasserspeicher-> T_OUT
        - Innenraumtemperatur -> T
'''
import mosaik_api_v3
import math
import numpy as np
from scipy.integrate import solve_ivp


Meta = {
    'api_version': '3.0',
    'type': 'hybrid',
    'models': {
        'RCBuildingSim': {
            'public': True,
            'params': ['Ai',
                       'Ci',
                       'Ce',
                       'Ria',
                       'Rie',
                       'Rea',
                       'p',
                       'c',
                       's',
                       'Ti_INIT',
                       'Te_INIT'
                       ], #parameter
            'attrs': ['Ta',
                      'T_OUT',
                      'F_OUT',
                      'F_IN',
                      'T_IN',
                      'SUN_DEG',
                      'LOT_DEG',
                      'T',
                      'GHI',
                      'DHI',
                      'T_OUT'
                      ],
        }
    },
}
# ----------------------------------------------------------------------------------------------------------------------
class RCBuildingSim(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(Meta) #speichert Metadaten im meta-Feld

# ----------------------------------------------------------------------------------------------------------------------
    def init(self, sid, **sim_params ):
        '''
            :param sid:
            :param sim_params: Simulationsparameter
            :return: Metadaten
        '''

        #Ermitteln der Simulationsparameter
        self.step_size = sim_params.get('step_size', 360)
        self.Ai = sim_params.get('Ai',1.45 ) # [m^2]

        #Werte in W/°C, umgerechnet aus kWh/°C
        self.Ci = sim_params.get('Ci',0.99) / (self.step_size / 3600)
        self.Ce = sim_params.get('Ce', 20.72) / (self.step_size / 3600)

        #Werte in °C/kW
        self.Ria = sim_params.get('Ria',19.22)
        self.Rea = sim_params.get('Rea',15.14)
        self.Rie = sim_params.get('Rie', 0.99)

        #Konstanten für Wärmeberechnung
        self.p = sim_params.get('p',1000 ) #in kg/m³
        self.c = sim_params.get('c',4182 ) #J/kgK

        self.Ti_INIT = sim_params.get('Ti_INIT',10)
        self.Te_INIT = sim_params.get('Te_INIT',10)
        self.refl_b = sim_params.get('refl_b',0.2)
        self.A_DEG = sim_params.get('A_DEG', 10)
        self.F = sim_params.get('F', 2e-5)

        self.T_OUT = 40     # Ausgangswassetemperatur
        self.Qg = 0         # interner Wärmegewinn durch Personen
        self.sigma_i = 0    # thermisches Rauschen
        self.sigma_e = 0    #thermischen Rauschen


        #definieren von benötigten Variablen, listen usw.
        self.eid_prefix = 'RCBuildingSim'
        self.entities = []
        self.results = []
        self.output = {} # Ausgangswerte



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
            :return: Simulationsdauer
        '''

        for eid, ent in inputs.items():
            # ----------------------------------------------------------------------------------------------------------
            #Eingangswerte
            # ----------------------------------------------------------------------------------------------------------
            GHI = ent['GHI']['CSV-0.HWT_0'] # [Signalname][Simulatorquelle des Signales]
            DHI = ent['DHI']['CSV-0.HWT_0']
            SUN_DEG = ent['SUN_DEG']['CSV_SUN-0.SUN_0']
            LOT_DEG = ent['LOT_DEG']['CSV_SUN-0.SUN_0']
            Ta = ent['Ta']['CSV-0.HWT_0']
            T_IN = ent['T_IN']['HotWaterTankSim-0.HotWaterTank_0']

            # ----------------------------------------------------------------------------------------------------------
            #Eingehende Wärme vom Warmwasserspeicher bestimmen
            # ----------------------------------------------------------------------------------------------------------
            if T_IN > self.T_OUT:
                Qh = (self.F * self.p * self.c * (T_IN - self.T_OUT))# [J = Ws]
                Qh /= self.step_size # [W]
                Qh /= 1000 # [kW]

            else:
                Qh = 0 # nur Wärme vorhanden wenn Eingangswassertemperatur höher ist als Ausgang -> kein negativer Wert!

            # ----------------------------------------------------------------------------------------------------------
            # solare Einstrahlung
            # ----------------------------------------------------------------------------------------------------------
            '''
              Parameter:
                - GHI: Global Horizontal Irradiance (W/m²)
                - DHI: Diffuse Horizontal Irradiance (W/m²)
                - SUN_DEG: Einfallswinkel zwischen Sonnenstrahl und Flächennormale (°) -> Daten aus CSV 
                - A_DEG: Neigung der Fläche (z.B. 90° für Fassade) (°) -> neigung der Einstahlfläche. Bekannt!
                - LOT_DEG: Sonnenzenitwinkel (0° = Sonne im Zenit) (°) -> Daten aus CSV
                - refl_b: Bodenreflexionsgrad (typisch 0.2)

            '''
            # Winkel in Radiant umrechnen
            theta = math.radians(SUN_DEG)   #Winkel Sonne → Flächennormale (AOI)
            beta = math.radians(self.A_DEG) #Neigung der Einstrahlfläche
            theta_z = math.radians(LOT_DEG) #Winkel Sonne → Erdlot (Zenitwinkel)

            # DNI berechnen
            cos_theta_z = max(math.cos(theta_z), 0.01)  # Schutz gegen Division durch 0
            DNI = (GHI - DHI) / cos_theta_z

            # Komponenten berechnen
            Q_dir = DNI * max(math.cos(theta), 0)
            Q_diff = DHI * (1 + math.cos(beta)) / 2
            Q_refl = GHI * self.refl_b * (1 - math.cos(beta)) / 2

            # Gesamtbestrahlung
            Qs = (Q_dir + Q_diff + Q_refl) / 1000 # Solare Strahlung [kW/m^2]
            #-----------------------------------------------------------------------------------------------------------
            #RC Gebäudemodell
            # - integration über Zeitbereich self.step
            #-----------------------------------------------------------------------------------------------------------
            # Zeitbereich
            t_span = (0, self.step_size)
            t_eval = np.linspace(*t_span, 10)

            def dTdt(t, y):
                Ti, Te = y
                dTi = (1 / (self.Ci * self.Rie)) * (Te - Ti) + 1 / (self.Ci * self.Ria) * (Ta - Ti) + \
                      self.Ai / self.Ci * Qs + 1 / self.Ci * (Qh + self.Qg)

                dTe = 1 / (self.Ce * self.Rie) * (Ti - Te) + 1 / (self.Ce * self.Rea) * (Ta - Te)

                # Optional: thermisches Rauschen
                noise_i = self.sigma_i * np.random.randn()
                noise_e = self.sigma_e * np.random.randn()

                return [dTi + noise_i, dTe + noise_e]

            # Anfangswerte: [Ti0, Te0] Anfangstemperaturen
            y0 = [self.Ti_INIT,self.Te_INIT]

            # Berechne --- Integration ---
            solution = solve_ivp(dTdt, t_span, y0, t_eval=t_eval)

            dTi = solution.y[0]
            dTe = solution.y[1]

            # Endwerte der Simulation (neue Raumtemperatur!)
            Ti_end = dTi[-1]
            Te_end = dTe[-1]

            #Definiere  Wasservolumenstrom
            F_OUT = self.F
            F_IN = F_OUT * -1

            #-----------------------------------------------------------------------------------------------------------
            #Ausgabewerte
            # -----------------------------------------------------------------------------------------------------------
            for eid in self.entities:
                self.output[eid] = {
                    'T': Ti_end,
                    'F_OUT': F_OUT ,
                    'F_IN' : F_IN,
                    'T_OUT': self.T_OUT
                }

            #print(f"\n--- Gebäude ---")
            #print(f"\nWasservolumenstrom: {F_OUT:.10f} m³/s")
            #print(f'Wassertemperatur Eingang: {T_IN} °C')
            #print(f'Wassertemperatur Ausgang: {self.T_OUT} °C')
            print(f'\nRaumtemperatur am Ende: {Ti_end:.2f} °C')
            #print(f'Gebäudehüllentemperatur: {Te_end:.2f} °C')
            #print(f'Einstrahlwärme: {Qs:.2f} kW')
            #print(f'Heizwärme: {Qh:.2f} kW\n')

        return time + self.step_size

# ----------------------------------------------------------------------------------------------------------------------
    def get_data(self, outputs):
        return self.output
