'''
    Modell einer Wärmepumpe mit PID Regler zur Regelung der Warmwassertemperatur welceh zum Heizkessel fließt

    Parameter:
        - Wirkungsgrad (Effizienz) -> Eff
        - evaporationTemp -> EVAP_TEMP
        - condensationTemp -> C_TEMP
        - AirInPressure -> AIR_p
        - WaterInPressure -> WATER_p
        - PID Regler max. value -> TargetTemp_max
        - PID Regler min. value -> TargetTemp_min
        - Ki
        - Kd
        - Kp
        - Zielinnenraumtemperatur des Gebäudes -> T_soll
        - Wärmeübertragung Kondensator in Wasserkreislauf -> Q_C
        - Obere Grenztemperaturdifferenz vom kondensator -> ttd_U_C
        - Obere Grenztemperaturdifferenz vom Verdampfer -> ttd_U_V

    Eingänge:
        - Wassertemperatur einlaufendes Wasser -> WaterTempIn (von Warmwasserspeicher)
        - aktuelle Innenraumtemperatur -> T_current
        - aktuelle Außentemperatur -> T_outside

    Ausgänge
        - benötigte elektrische Leistung -> Wh_Pel
        - Wasservolumenstrom in -> F_IN (negativ)
        - Wasservolumenstrom out -> F_OUT
        - Ausgangswassertemperatur in den Warmwasserspeicher -> WaterTempOut

'''

from tespy.components import Condenser, HeatExchanger, CycleCloser, Compressor, Valve, Source, Sink
from tespy.connections import Connection, Ref
from tespy.networks import Network
import mosaik_api_v3
from simple_pid import PID

Meta = {
    'api_version': '3.0',
    'type': 'hybrid',
    'models': {
        'HeatPumpSim': {
            'public': True,
            'params': ['Q_C',
                       'Eff',
                       'EVAP_TEMP',
                       'C_TEMP',
                       'AIR_p',
                       'WATER_p',
                       'TargetTemp_max',
                       'TargetTemp_min',
                       'Ki',
                       'kp',
                       'Kd',
                       'T_soll',
                       ' T_current' ,
                       'T_outside',
                       'ttd_U_C',
                       'ttd_U_V',
                       'F'],

            'attrs': ['WaterTempOut',
                      'Wh_Pel',
                      'T_outside',
                      'F_OUT',
                      'F_IN',
                      'WaterTempIn',
                      'T_current'],
        }
    },
}
# ----------------------------------------------------------------------------------------------------------------------
class HeatPumpSim(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(Meta) #speichert Metadaten im meta-Feld

# ----------------------------------------------------------------------------------------------------------------------
#wird nur einmal beim starten der funktion ausgeführt
    def init(self, sid, **sim_params ):
        '''
            :param sid:
            :param sim_params: Simulationsparameter
            :return: Metadaten
        '''
        #Ermitteln der Simulationsparameter
        self.step_size = sim_params.get('step_size', 360)
        self.efficency = sim_params.get('Eff', 1) # Wert von 0..1
        self.evaporationTemp = sim_params.get('EVAP_TEMP', 1)
        self.condensationTemp = sim_params.get('C_TEMP', 1)
        self.AirInPressure = sim_params.get('AIR_p',1)
        self.WaterInPressure= sim_params.get('WATER_p',1)

        #self.Q_condenser = sim_params.get('Q_C', -9100e3)
        self.ttd_U_C = sim_params.get('ttd_U_C',5)
        self.ttd_U_V = sim_params.get('ttd_U_V', 5)

        #Reglerparameter
        Ki = sim_params.get('Ki')
        Kp = sim_params.get('Kp')
        Kd = sim_params.get('Kd')
        T_soll = sim_params.get('T_soll', 20)

        #Begrenzung der Regelung
        self.TargetTemp_min = sim_params.get('TargetTemp_min')
        self.TargetTemp_max = sim_params.get('TargetTemp_max')

        #Wassersolumenstrom vom und zum Tank
        self.F = sim_params.get('F')

        #definieren von benötigten Variablen, listen usw.
        self.eid_prefix = 'HeatPumpSim'
        self.entities = []
        self.results = []
        self.output = {} # Ausgangswerte

        #Definiere Arrays für die optimiernug
        self.Wh_Pel = []
        self.Wh_PV = []
        self.Wh_H = []

        #pid Regler für warmwassertemperatur
        self.PID = PID(Kp, Ki, Kd, setpoint=T_soll)

        #print(f'Schrittweite Pumpe : {self.step_size}')
        #print(f'target temp min : {TargetTemp_min}')
        #print(f'target temp max : {TargetTemp_max}')

        #self.PID.output_limits = (TargetTemp_min, TargetTemp_max)# limits defineren

        self.PID.sample_time = 0

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
            WaterTempIn = ent['WaterTempIn']['HotWaterTankSim-0.HotWaterTank_0']
            T_current = ent['T_current']['RCSim-0.RCBuildingSim_0']
            T_outside = ent['T_outside']['CSV-0.HWT_0']

            # ----------------------------------------------------------------------------------------------------------
            # setze Reglerbegrenzungwerte -> wichtig das Regler nicht weniger Temperatur ausgibt als die
            #   Eingangswassertemperatur da sonst ein negativer Wärmewert entsteht was bedeutet, die Wärmepumpe nimmt
            #   Wärme auf !!!
            # ----------------------------------------------------------------------------------------------------------
            self.PID.output_limits = (WaterTempIn, self.TargetTemp_max)  # limits defineren

            # ----------------------------------------------------------------------------------------------------------
            #berechne ziel Wassertemperatur durch den Regler
            # ----------------------------------------------------------------------------------------------------------
            WaterTempOut = self.PID(T_current)

            # ----------------------------------------------------------------------------------------------------------
            # Wärmepumpenmodell
            # ----------------------------------------------------------------------------------------------------------

            wf = "R600" # Butan als Kühlmittel wo bis ~150°C kann! -> für hohe Warmwassertemperaturen
            nwk = Network(p_unit="bar", T_unit="C", iterinfo=False, fluids=['water', 'air', wf])

            compressor = Compressor("compressor")
            evaporator = HeatExchanger("evaporator")
            condenser = Condenser("condenser")
            valve = Valve("expansion valve")
            cycleCloser = CycleCloser("cycle closer")

            so1 = Source("ambient air source")
            si1 = Sink("ambient air sink")
            so2 = Source("heating source")
            si2 = Sink("heating sink")

            c0 = Connection(valve, "out1", cycleCloser, "in1", label="0")
            c1 = Connection(cycleCloser, "out1", evaporator, "in2", label="1")
            c2 = Connection(evaporator, "out2", compressor, "in1", label="2")
            c3 = Connection(compressor, "out1", condenser, "in1", label="3")
            c4 = Connection(condenser, "out1", valve, "in1", label="4")

            nwk.add_conns(c0, c1, c2, c3, c4)

            c11 = Connection(so1, "out1", evaporator, "in1", label="11")  # Außemtemperatur
            c12 = Connection(evaporator, "out1", si1, "in1", label="12")  # Luftauslass

            c21 = Connection(so2, "out1", condenser, "in2", label="21")  # Wasserrücklauf
            c22 = Connection(condenser, "out2", si2, "in1", label="22")  # Wasserauslauf

            nwk.add_conns(c11, c12, c21, c22)

            condenser.set_attr(pr1=1, pr2=1, ttd_u=self.ttd_U_C)

            evaporator.set_attr(pr1=1, pr2=1, ttd_u=self.ttd_U_V)
            compressor.set_attr(eta_s=self.efficency)

            c2.set_attr(fluid={wf: 1}, x=1.0)

            # Luftkreislauf
            c11.set_attr(fluid={"air": 1}, p=1, T=T_outside)
            c12.set_attr(T=Ref(c11, 1, -2))

            # wasserkreislauf
            c21.set_attr(fluid={"water": 1}, p=3, T=WaterTempIn)
            c22.set_attr(T=WaterTempOut, m=1)

            nwk.solve("design")  # Simulation starten

            Q_W = condenser.Q.val
            Pel = compressor.P.val
            Wh_Pel = Pel * (self.step_size / 3600) # umrechnen in Wh

            #COP = abs(Q_W) / Pel
            #print("COP: " + str(COP))# COP

            #Volumenstrom
            F_IN = round(self.F * -1,4 )#negativ da ablaufvolumenstrom des Warmwasserspeichers
            F_OUT = round(self.F, 4)

            #print(f"\n--- Wärmepumpe ---")
            #print(f'benötigte Leistung für den Kompressor: {Pel} W')
            #print(f'COP der Wärmepumpe: {COP}')
            #print(f'Wasserwärme: {Q_W} W')
            #print(f'Wasservolumenstrom rein: {F_IN} m^3/s')
            #print(f'Wasservolumenstrom raus: {F_OUT} m^3/s')
            #print(f'T_current: ', T_current)
            #print(f'T_IN: ', WaterTempIn)
            #print(f'T_OUT: ', WaterTempOut)

            # ----------------------------------------------------------------------------------------------------------
            # Ausgabewerte
            for eid in self.entities:
                self.output[eid] = {
                    'Wh_Pel': Wh_Pel,
                    'F_OUT': F_OUT,
                    'F_IN': F_IN,
                    'WaterTempOut': WaterTempOut
                }

        return time + self.step_size

# ----------------------------------------------------------------------------------------------------------------------
    #diese Version in der Simulation verwenden um Daten an andere Simulationen zu schicken
    def get_data(self, outputs):
        return self.output

