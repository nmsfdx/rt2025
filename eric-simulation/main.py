'''
verwendete Python Version : 3.10 -> Wichtig für das Wärmepumpenmodell. Hat bei Pyton 3.11 und 3.12 Probleme gemacht.
Entiwcklungsumgebung : PyCharm Community Edition Version

Das Batteriemodell verwenden um maximale kapazität sowie Lade und entladerate zu ermitteln
als Werte für die optimerung!

Benötigte Python Packages:
    - mosaik            => Simulatiosdurchführung
    - mosaik-heatpump   => Warmwassertankmodell:
                            Bei der installation des Paketes wird eine ältere Version von TESpy installiert als benötigt.
                            => Nach Installation des Paketes direkt die TESpy Version erneuern auf die aktuellste
    - TESpy
    - pvlib             => Simulationstools
    - os                => durchführen von Systemoperationen
    - cvxpy             => berechung der optimierung
    - Pybamm            => Batteriemodell
                            => akutuell wird eine reale Batterie in der Simulation verwendet. Pybamm Model muss noch
                             ergänzt werden.
    - simple-pid        => PID Regler
    - MOSEK              => solver für cvxpy: wird ne Lizenz benötigt: https://www.mosek.com/products/academic-licenses/
'''

import mosaik
import pandas as pd
import pvlib
from pvlib.location import Location
import os
import csv
#-----------------------------------------------------------------------------------------------------------------------
#Globale Variablen
#-----------------------------------------------------------------------------------------------------------------------
data_filename = 'tank_data.csv'  #Daten für die Simulation

#Einfallswinkel der Sonne berechnen Abhängig des gewählten Standortes
CSV_File_SunAngle = 'sonne.csv'  # Dateiname für die Daten des Sonneneinfallwinkels
set_latiutude = 48.7758          # breitengrad Stuttgart
set_longitude = 9.1829           # längengrad Stuttgart
set_altitude = 245               # höhe Stuttgart
set_timezone = 'Europe/Berlin'   # Zeitzone
surface_deg = 45                 # Neigung der  Einstrahlfläche in (°)
surface_azimuth = 180            # Ausrichtung der einstrahlfäche (180 = Süden)

#Anfangswerte
#Ein und- Auslasswassertemperturen des Warmwassertanks
T_Sensor1 = 40
T_Sensor2 = 40
T_Sensor3 = 40
T_Sensor4 = 40
T_Sensor5 = 40
T_Sensor6 = 40
T_Sensor7 = 40
T_Sensor8 = 40

#Schichttemperaturen des Warmwassertanks
T_Layer1 = 40
T_Layer2 = 40
T_Layer3 = 40
T_Layer4 = 40

#Außentemperatur
T_OUTSIDE = 5
#Aktuelle Raumtemperatur
T_current = 10
#Wasser Eingangstemperatur am Heizkessel
T_HeatPumpIn = 60
#benötigte elektrische Leistung
Wh_Pel = 0

#Parameter
F_Building = 0.08   # Volumenstrom des Gebäudes
F_HeatPump = 2      # Volumenstrom der Wärmepumpe
F_PV = 2            # Volumenstrom PV Analge und Wärmebedarf des Haushaltes

#-----------------------------------------------------------------------------------------------------------------------
# Daten aus der CSV Datei Analysieren
#-----------------------------------------------------------------------------------------------------------------------
# Ermitteln des kompletten Dateipfades
HWT_FLOW_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), data_filename)

#CSV-Datei laden um Zeitinformationen zu extrahieren
df = pd.read_csv(HWT_FLOW_DATA, parse_dates=['timestamp'], skiprows=1)

start_time = df['timestamp'].iloc[0]
end_time = df['timestamp'].iloc[-1]

 # Schrittweite automatisch bestimmen
if len(df) >= 2:
    step_size = int((df['timestamp'].iloc[1] - df['timestamp'].iloc[0]).total_seconds())
else:
    step_size = 300 # 5 Minuten Zeitschritte -> in Sekunden angeben!

# Simulationsdauer berechnen
sim_duration = int((end_time - start_time).total_seconds()) + step_size

print(f'Simulation from {start_time} to {end_time} ({sim_duration} s, step = {step_size} s)')


#-----------------------------------------------------------------------------------------------------------------------
# Berechnung des Sonnenstandes über die Simulationszeit
#-----------------------------------------------------------------------------------------------------------------------
site = Location(latitude=set_latiutude, longitude=set_longitude, tz=set_timezone, altitude=set_altitude) #Position

times = pd.date_range(start=start_time, end=end_time, freq=str(step_size) + 's' , tz=site.tz) # Zeitreihe

solpos = site.get_solarposition(times) # Sonnenstand berechnen

theta_z = solpos['apparent_zenith'] # Winkel Sonne → Erdlot (Zenitwinkel)

# Winkel Sonne → Flächennormale (AOI)
aoi = pvlib.irradiance.aoi(
    surface_deg,
    surface_azimuth,
    solpos['apparent_zenith'],
    solpos['azimuth']
)

aoi.index.name = 'timestamp' # fügt Spaltenname für die Zeitstempel ein

#Zeitzonneninformation entfernen
aoi.index = aoi.index.tz_localize(None)
theta_z.index = theta_z.index.tz_localize(None)

df_sun = pd.DataFrame({
    'timestamp': aoi.index,
    'AOI': aoi.values,
    'Zenith': theta_z.values
})

#Daten als CSV speichern mit Überschrift  "SUN"
with open(CSV_File_SunAngle,  mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    writer.writerow(['SUN'])                    #füge Überschrift ein
    writer.writerow(df_sun.columns.tolist())    # Schreibe Spaltenüberschriften

    for index, row in df_sun.iterrows():        #Schreibe Daten
        writer.writerow(row.tolist())

#-----------------------------------------------------------------------------------------------------------------------
#Simulationsparameter und Initialwerte
#-----------------------------------------------------------------------------------------------------------------------
#Parameter für die einzelnen Simulationen festlegen
params = {
    'HotWaterTank':{
        'height': 1000,
        'volume': 100,
        'T_env': 20.0,
        'htc_walls': 0.28,
        'htc_layers': 0.897,
        'n_layers': 4,
        'n_sensors': 5,
        'layers': [
        {'bottom': 0, 'top': 250},
        {'bottom': 250, 'top': 500},
        {'bottom': 500, 'top': 750},
        {'bottom': 750, 'top': 1000}
        ],

        # Die Sensorwerte zeigen nur die Temperatur der Schicht nicht des Wassers wo tatsächlich abfließt!
        'sensors': {
            'sensor_1': {'pos': 10},
            'sensor_2': {'pos': 250},
            'sensor_3': {'pos': 500},
            'sensor_4': {'pos': 750},
            },

        'connections': {
            #Photovoltaik
            'PV_in': {'pos': 800},
            'PV_out': {'pos': 200},
            #Wärmepumpe
            'Wp_in': {'pos': 800},
            'Wp_out': {'pos': 200},
            #Wärmebedarf Heizung
            'WH_in': {'pos': 400},
            'WH_out': {'pos': 900},
            #Wärmebedarf Haushalt
            'H_in': {'pos': 400},
            'H_out': {'pos': 950},
        },
    },
    'battery': {
        'Vmin': 0,
        'Vmax':24,
        'I_SOC': 0.1,
        'step_size' : step_size,
        'Model' : 'SPMe', # Wähle zwischen: DFN, SPM, SPMe
        'Bat_CAP' : 100, #Batteriekapazität in Ah
    },

    'heatPump':{
        'Eff':0.8,                  # Wirkungsgrad des Kompressors der Warmwasserpumpe
        'step_size' : step_size,
        'EVAP_TEMP': 1,
        'C_TEMP' : 1,
        'AIR_p' : 1,
        'WATER_p' : 3,
        'ttd_U_C' : 5,
        'ttd_U_V' : 5,
        'TargetTemp_max' : 100,     # Regelbregrenzung der Ausgangswassertemperatur [°C]
        'TargetTemp_min' : 20,      # Regelbregrenzung der Ausgangswassertemperatur [°C]-> Angabe nicht nötig!
        'Ki' : 0.6,
        'Kp' : 0.425,
        'Kd' : 0,
        'T_soll' : 20,              # Solltemperatur des Raumes [°C]
        'F' : 5                  # Wasservolumenstrom des Wärmepumpen Wasserkreislaufs [m^3]
    },

    'RC':{
        'Ai': 1.45,                 # [m^2]
        'Ci' : 0.99,                # [KWh/°C]
        'Ce' : 20.72,               # [KWh/°C]
        'Ria' : 19.22,              # [°C/kW]
        'Rea' : 15.14,              # [°C/kW]
        'Rie' : 0.99,               # [°C/kW]
        'p' : 977,                  # Dichte von Wasser [kg/m^3]
        'c' : 4190,                 # spezifiche Wärmeleitfähigkeit von Wasser [J/(kg*K)],
        'Ti_INIT' : 10,             # Initiale Raumtemperatur [°C]
        'Te_INIT' : 10,             # Initiale Gebäudetemperatur [°C]
        'A_DEG' : surface_deg,      #
        'refl_b' : 0.2,             # Bodenreflektionsgrad
        'F' : F_Building            # Wasservolumenstrom des Heizkreislaufes
    },
    'OPT':{
        'C_max' : 1000000,           # Ladekapazität der Batterie [Wh]
        'Wh_BAT_max' : 100000,       # Maximlade lade- und entladeenergie auf einmal [Wh]
        'C_INIT' : 0                 # Anfangsladung der Batterie [Wh]
    },

    'PV':{
        'F' : 1.1,                   # Wasservolumenstrom des PV Heizkreislaufes + Haushaltskreislauf [°C]
        'p': 977,                    # Dichte von Wasser [kg/m^3]
        'c': 4190,                   # spezifiche Wärmeleitfähigkeit von Wasser [J/(kg*K)],

    }

}
#Anfangsschichtemperaturen  des Warmwassertanks
init_vals = {
            'layers': {'T': [T_Layer1, T_Layer2, T_Layer3, T_Layer4]}}
#-----------------------------------------------------------------------------------------------------------------------
# Simulationskonfiguration
#-----------------------------------------------------------------------------------------------------------------------
# Definiere die benötigten .py Dateien
sim_config = {
    'HotWaterTankSim': {'python': 'mosaik_components.heatpump.hotwatertank.hotwatertank_mosaik:HotWaterTankSimulator'},
    #'BatterySim': {'python': 'Batterie:BatterySimulator'},
    'HeatPumpSim':{'python': 'HeatPump:HeatPumpSim'},
    'RCSim':{'python': 'RC_Building:RCBuildingSim'},
    'CSV': {'python': 'mosaik_csv:CSV',},
    'CSV_writer': {'python': 'mosaik_csv_writer:CSVWriter'},
    'CSV_SUN' : {'python': 'mosaik_csv:CSV'},
    'OPT' : {'python': 'Optimierung Strompreis:OptimierungSim'},
    'PV' : {'python': 'PV:PVSim'},
    'CSV_writer': {'python': 'mosaik_csv_writer:CSVWriter'},
}
#-----------------------------------------------------------------------------------------------------------------------
world = mosaik.World(sim_config)
#-----------------------------------------------------------------------------------------------------------------------
#Warmwasserspeicher
HotWaterTank_sim = world.start('HotWaterTankSim', config = params['HotWaterTank'], step_size=step_size)
HotWaterTank = HotWaterTank_sim.HotWaterTank.create(num=1,params=params['HotWaterTank'], init_vals = init_vals)
#-----------------------------------------------------------------------------------------------------------------------
#Batterie
#battery_sim = world.start('BatterySim', **params['battery'])
#battery= battery_sim.BatterySimulator.create(num=1)
#-----------------------------------------------------------------------------------------------------------------------
#Wärmepumpe
heatPump_sim = world.start('HeatPumpSim', **params['heatPump'])
heatPump = heatPump_sim.HeatPumpSim.create(num=1)
#-----------------------------------------------------------------------------------------------------------------------
#RC Gebäudemodell
RC_Building_sim = world.start('RCSim', **params['RC'])
RC_Building = RC_Building_sim.RCBuildingSim.create(num=1)
#-----------------------------------------------------------------------------------------------------------------------
#Optimerung
Optimierung_sim = world.start('OPT',**params['OPT'] )
Optimierung = Optimierung_sim.OptimierungSim.create(num=1)
#-----------------------------------------------------------------------------------------------------------------------
#PV Daten
PV_sim = world.start('PV', **params['PV'])
PV_DATA = PV_sim.PVSim.create(num=1)
#-----------------------------------------------------------------------------------------------------------------------
#CSV
#Daten aus CSV lesen
#die Spaltennamen müssen bei world.connect angegeben werden um Daten zu übertragen
# Allgemeine Daten
csv = world.start('CSV', sim_start=start_time, datafile=HWT_FLOW_DATA)
# Instantiate model
csv_data = csv.HWT() #HWT muss als überschrift in der CSV Excel stehen

#Daten in CSV schreiben
csv_sim_writer = world.start('CSV_writer', start_date=start_time, date_format='%d.%m.%Y %H:%M',
                           output_file='results_simulation.csv')
# Instantiate model
csv_writer = csv_sim_writer.CSVWriter(buff_size=360000)
#-----------------------------------------------------------------------------------------------------------------------
#Sonneneinstrahlung für RC Gebäudemodell
csv_sun = world.start('CSV_SUN', sim_start = start_time, datafile = CSV_File_SunAngle)
csv_sun = csv_sun.SUN()

# ----------------------------------------------------------------------------------------------------------------------
# Verbindungen herstellen zwischen den Modellen
# ----------------------------------------------------------------------------------------------------------------------
#Heizleistungsdaten
world.connect(csv_data, PV_DATA[0],
              ('Solarthermie_Erzeugung', 'Q_PV'),
              ('Bedarf_thermisch', 'Q_H'),)

world.connect(PV_DATA[0], HotWaterTank[0],
              ('T_OUT_PV','PV_in.T'),
              ('T_OUT_H','H_in.T'),
              ('F_OUT','PV_in.F'),
              ('F_OUT','H_in.F'),
              ('F_IN','PV_out.F'),
              ('F_IN','H_out.F'),)

world.connect(HotWaterTank[0], PV_DATA[0],
              ('H_out.T','T_IN_H'),
              ('PV_out.T','T_IN_PV'), time_shifted = True,
              initial_data={'PV_out.T' : T_Sensor1,
                            'H_out.T' : T_Sensor4
                    }
              )
# -------------------------------------------------------------------------------------------------------------------------
# Daten für die Optimerung
#-----------------------------------------------------------------------------------------------------------------------
world.connect(csv_data, Optimierung[0],
              ('Strompreis', 'cost_Wh'),
              ('PV_Erzeugung', 'Wh_PV'),
              ('Bedarf_elektrisch', 'Wh_H'))

world.connect(HotWaterTank[0], Optimierung[0],
              ('PV_out.T','T_SENSOR1'),
              ('H_out.T','T_SENSOR2'),
              ('Wp_out.T','T_SENSOR3'),
              ('WH_out.T','T_SENSOR4'),
              ('PV_in.T','T_SENSOR5'),
              ('H_in.T','T_SENSOR6'),
              ('Wp_in.T','T_SENSOR7'),
              ('WH_in.T','T_SENSOR8'),


              time_shifted = True,
              initial_data= {'PV_out.T': T_Sensor1,
                             'H_out.T' : T_Sensor2,
                             'Wp_out.T': T_Sensor3,
                             'WH_out.T' : T_Sensor4,
                             'PV_in.T': T_Sensor5,
                             'H_in.T' : T_Sensor6,
                             'Wp_in.T': T_Sensor7,
                             'WH_in.T' : T_Sensor8,

                             }
              )

world.connect(heatPump[0], Optimierung[0],
              ('Wh_Pel', 'Wh_Pel'), time_shifted=True, initial_data={'Wh_Pel' : Wh_Pel})

world.connect(RC_Building[0], Optimierung[0], ('T', 'T'), time_shifted=True, initial_data= {'T':T_current})

world.connect(Optimierung[0], csv_writer,
              ('Wh_H', 'Gebäudeenergie [Wh]'),
             ('cost_Wh', 'Stromkosten [€/Wh]'),
              ('Wh_PV', 'PV_Energie [Wh]'),
              ('Wh_Pel', 'Wärmepumpenenergie [Wh]'),
              ('T', 'Innenraumtemperatur[°C]')
              )

# ----------------------------------------------------------------------------------------------------------------------
# Wärmepumpe
#-----------------------------------------------------------------------------------------------------------------------
world.connect(heatPump[0], HotWaterTank[0],
              ('WaterTempOut', 'Wp_in.T'),
              ('F_IN', 'Wp_out.F'),
              ('F_OUT', 'Wp_in.F'))

world.connect(HotWaterTank[0], heatPump[0],
              ('Wp_out.T','WaterTempIn'),  time_shifted = True, initial_data={'Wp_out.T': T_Sensor1})

world.connect(csv_data, heatPump[0],
              ('Aussentemperatur' , 'T_outside'))


# ----------------------------------------------------------------------------------------------------------------------
#Daten fürs Gebäude
#-----------------------------------------------------------------------------------------------------------------------
world.connect(csv_data, RC_Building[0],
              ('GHI', 'GHI'),
              ('DHI', 'DHI'),
              ('Aussentemperatur' , 'Ta'))

world.connect(csv_sun, RC_Building[0],('AOI','SUN_DEG'),('Zenith','LOT_DEG')
              )

world.connect(HotWaterTank[0], RC_Building[0],
              ('WH_out.T', 'T_IN'))

world.connect(RC_Building[0], HotWaterTank[0],
              ('F_OUT' , 'WH_in.F'),
              ('F_IN' , 'WH_out.F'),
              ('T_OUT' , 'WH_in.T'), time_shifted=True,
              initial_data={
                'F_OUT' : F_Building,
                'F_IN' : (F_Building * -1),
                'T_OUT' : 60
              })

world.connect(RC_Building[0], heatPump[0],
              ('T','T_current'), time_shifted=True, initial_data={'T' : T_current})


#meta = HotWaterTank_sim.meta['models']['HotWaterTank']
#print(meta)
#-----------------------------------------------------------------------------------------------------------------------
# Simulation starten
#-----------------------------------------------------------------------------------------------------------------------
world.run(until=sim_duration)
#mosaik.util.plot_dataflow_graph(world, folder='util_figures') #Zeigt ein Diagramm mit allen Simulatorenverbindungen an
#mosaik.util.plot_execution_graph(world, folder='util_figures')
#mosaik.util.plot_execution_time(world, folder='util_figures')
#mosaik.util.plot_execution_time_per_simulator(world, folder='util_figures')