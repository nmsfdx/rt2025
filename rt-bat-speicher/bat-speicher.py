import pybamm
import numpy as np
model = pybamm.lithium_ion.DFN()
experiment = pybamm.Experiment(
    [
        (
            "Discharge at C/10 for 10 hours or until 3.3 V",
            "Rest for 1 minute",
            "Charge at 1 A until 4.1 V",
            "Hold at 4.1 V until 50 mA",
            "Rest for 1 minute",
        )
    ]
    * 3
    + [
        "Discharge at 1C until 3.3 V",
    ]
)
sim = pybamm.Simulation(model, experiment=experiment)
sim.solve()
sim.plot()