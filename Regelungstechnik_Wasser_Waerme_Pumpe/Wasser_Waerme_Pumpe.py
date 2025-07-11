# wp_sim.py

from tespy.components import SimpleHeatExchanger, CycleCloser, Compressor, Valve
from tespy.connections import Connection
from tespy.networks import Network
import mosaik_api_v3

# MOSAIK-Metadaten
META = {
    'models': {
        'Wärmepumpe': {
            'public': True,
            'params': ['fluessigkeit', 'Q_waerme', 'T_evap', 'T_cond', 'eta_s'],
            'attrs': ['T_aussen', 'Leistung_input', 'Q_out', 'P_el', 'COP'],
        }
    }
}


# TESPy Wärmepumpe als Klasse
class Waermepumpe:
    def __init__(self, fluessigkeit="R290", Q_waerme=-9100, T_evap=2, T_cond=40, eta_s=0.8):
        self.wf = fluessigkeit
        self.nwk = Network(p_unit="bar", T_unit="C", iterinfo=False)

        self.cp = Compressor("compressor")
        self.ev = SimpleHeatExchanger("evaporator")
        self.cd = SimpleHeatExchanger("condenser")
        self.va = Valve("expansion valve")
        self.cc = CycleCloser("cycle closer")

        self.c0 = Connection(self.va, "out1", self.cc, "in1")
        self.c1 = Connection(self.cc, "out1", self.ev, "in1")
        self.c2 = Connection(self.ev, "out1", self.cp, "in1")
        self.c3 = Connection(self.cp, "out1", self.cd, "in1")
        self.c4 = Connection(self.cd, "out1", self.va, "in1")

        self.nwk.add_conns(self.c0, self.c1, self.c2, self.c3, self.c4)

        self.c2.set_attr(T=T_evap, fluid={self.wf: 1}, x=1.0)
        self.c4.set_attr(T=T_cond, x=0.0)

        self.cp.set_attr(eta_s=eta_s)
        self.cd.set_attr(Q=Q_waerme, pr=1)
        self.ev.set_attr(pr=1)

    def run(self, t_aussen, leistung_input):
        T_evap = t_aussen - 5
        self.c2.set_attr(T=T_evap)
        self.nwk.solve("design")
        cop = self.get_COP()
        P_el = min(leistung_input, self.cp.P.val)
        Q_out = cop * P_el
        return Q_out, P_el, cop

    def get_COP(self):
        return abs(self.cd.Q.val) / self.cp.P.val if self.cp.P.val != 0 else 0


# MOSAIK-kompatibler Simulator
class WP_Simulator(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(META)
        self.entities = {}
        self.step_size = 300  # z. B. 15 Minuten

    def init(self, sid, **sim_params):
        self.step_size = sim_params.get('step_size', 300)
        return self.meta

    def create(self, num, model, **params):
        entities = []
        for i in range(num):
            eid = f'{model}_{i}'
            wp = Waermepumpe(**params)
            self.entities[eid] = {
                'model': wp,
                'inputs': {
                    'T_aussen': 2.0,
                    'Leistung_input': 15000
                },
                'outputs': {
                    'Q_out': 0,
                    'P_el': 0,
                    'COP': 0
                }
            }
            entities.append({'eid': eid, 'type': model})
        return entities

    def step(self, time, inputs):
        for eid, entity in self.entities.items():
            ent_inputs = inputs.get(eid, {})
            T_aussen = ent_inputs.get('T_aussen', [entity['inputs']['T_aussen']])[0]
            Leistung_input = ent_inputs.get('Leistung_input', [entity['inputs']['Leistung_input']])[0]

            Q_out, P_el, COP = entity['model'].run(t_aussen=T_aussen, leistung_input=Leistung_input)

            entity['inputs']['T_aussen'] = T_aussen
            entity['inputs']['Leistung_input'] = Leistung_input
            entity['outputs'] = {
                'Q_out': Q_out,
                'P_el': P_el,
                'COP': COP
            }

        return time + self.step_size

    def get_data(self, outputs):
        return {
            eid: {attr: self.entities[eid]['outputs'][attr] for attr in attrs}
            for eid, attrs in outputs.items()
        }


# Optional für lokalen Test (nicht im MOSAIK-Betrieb nötig)
#if __name__ == '__main__':
#    sim = WP_Simulator()
#   sim.init('sim1')
#    sim.create(1, 'Wärmepumpe')
#    sim.step(0, {})
#    print(sim.get_data({'Wärmepumpe_0': ['Q_out', 'P_el', 'COP']}))
