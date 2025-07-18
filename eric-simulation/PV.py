'''
    Diese Simulation ermittelt die Wassertemperatur der PV die in den Heizkessel fließt.
    Ebenso Simuliert sie die Wärmeabgabe der vorgegebenen benötigten Wärme des Haushaltes

    Wärme berechnen:

    Q  = V * p * c * dT

    dT = Temperaturdifferenz Wasser vor und nach dem Heizkörper
    V = Volumenstrom
    p =  Wasserdichte
    c = spezifische Wäremkapazität von Wasser
    Q = Wärme in Joule [J]

    => gibt die Wärme Q an die in definierter Zeit t umgesetzt wird. Heißt um die Leistung zu ermitteln, Q durch die
        Zeit teilen die der Erwärmungsprozess dauert da 1 J = 1Ws!

    Parameter:
        - Volumenstrom -> F
        - Wasserdichte -> p
        - spezifische Wäremkapazität von Wasser -> c

    Eingänge:
        - PV Produzierte Wärme -> Q_PV
        - Wärmebedarf haushalt -> Q_H
        - Warmwassertemperatur Eingang PV -> T_IN_PV
        - Warmwassertemperatur Eingang Haushalt -> T_IN_H

    Ausgang:
        - Warmwassertemperatur Ausgang PV -> T_OUT_PV
        - Warmwassertemperatur Ausgang Haushalt -> T_OUT_H
        - Warmwasservolumenstrom IN -> F_IN
        - Warmwasservolumenstrom OUT -> F_OUT
'''

import mosaik_api_v3

# ----------------------------------------------------------------------------------------------------------------------
# Modellsimulation
# ----------------------------------------------------------------------------------------------------------------------

Meta = {
    'api_version': '3.0',
    'type': 'hybrid',
    'models': {
        'PVSim': {
            'public': True,
            'params': ['F'],
            'attrs': ['Q_PV',
                      'Q_H',
                      'T_IN_PV',
                      'T_IN_H',
                      'T_OUT_PV',
                      'T_OUT_H',
                      'F_OUT',
                      'F_IN'],
        }
    },
}
# ---------------------------------------------------------------------------------------------------
class PVSim(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(Meta) #speichert Metadaten im meta-Feld

# ---------------------------------------------------------------------------------------------------
    def init(self, sid, **sim_params ):
        '''
            :param sid:
            :param sim_params: Simulationsparameter
            :return: Metadaten
        '''

        # Ermitteln der Simulationsparameter
        self.step_size = sim_params.get('step_size', 360)
        self.F = sim_params.get('F', 1.0)

        # Konstanten für Wärmeberechnung
        self.p = sim_params.get('p', 1000)  # [kg/m³]
        self.c = sim_params.get('c', 4182)  # [J/kgK]

        #definieren von benötigten Variablen, listen usw.
        self.eid_prefix = 'PVSim'
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
            Q_PV= ent['Q_PV']['CSV-0.HWT_0']# in W
            Q_H = ent['Q_H']['CSV-0.HWT_0']# in W
            T_IN_PV = ent['T_IN_PV']['HotWaterTankSim-0.HotWaterTank_0']
            T_IN_H = ent['T_IN_H']['HotWaterTankSim-0.HotWaterTank_0']

            # ----------------------------------------------------------------------------------------------------------
            # Umrechnen der Wärme von W in Joule -> Zeitabhängig mit self.step_size
            # ----------------------------------------------------------------------------------------------------------
            Q_PV *= self.step_size # W * s = Ws == J
            Q_H *= self.step_size # W * s = Ws == J

            # ----------------------------------------------------------------------------------------------------------
            #Berechne Ausgangswassertemperatur aus Wärme für den Kessel der PV
            T_OUT_PV = T_IN_PV + (Q_PV / (self.F * self.c  *self.p)) #Wärmeaufnahme
            # Berechne Ausgangswassertemperatur aus Wärme für den Kessel des Haushaltes
            T_OUT_H = T_IN_H - (Q_H / (self.F * self.c * self.p)) #Wärmeabgabe

            F_OUT = self.F
            F_IN = self.F * -1 #Kessel negativ

            #print(f"\n--- PV ---")
            #print(f'T Out PV: {T_OUT_PV}')
            #print(f'Wäreme PV: {Q_PV}')
            #print(f'T Out H: {T_OUT_H}')
            #print(f'T IN H: {T_IN_H}')
            #print(f'Wärme Haushalt: {Q_H}')
            #print(f'T Out H: {T_OUT_H}')

            #-----------------------------------------------------------------------------------------------------------
            # Ausgabewerte
            # -----------------------------------------------------------------------------------------------------------
            for eid in self.entities:
                self.output[eid] = {
                    'T_OUT_PV': T_OUT_PV,
                    'T_OUT_H' : T_OUT_H,
                    'F_OUT' : F_OUT,
                    'F_IN' : F_IN
                }

        return time + self.step_size

# ----------------------------------------------------------------------------------------------------------------------
    def get_data(self, outputs):
        return self.output
