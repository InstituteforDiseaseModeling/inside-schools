'''
Introduction analysis sweeping over several prevalence levels.  Similar to run_baseline.py, but this is just for K-5.

Example usage, forcing new results and using a 4 different seeds:

    python run_k5.py --force --n_reps=4

'''

import sys
import os
import matplotlib.pyplot as plt
import utils as ut
import config as cfg
from run import Run

alt_sus = False


class BaselineK5(Run):
    def build_configs(self):
        # Configure alternate sus
        if alt_sus:
            value_labels = {'Yes' if p else 'No':p for p in [True]}
            self.builder.add_level('AltSus', value_labels, ut.alternate_symptomaticity)

        return super().build_configs()


if __name__ == '__main__':

    args = cfg.process_inputs(sys.argv)

    # Optional overrides
    sweep_pars = dict(
        # n_reps = 5,
        # n_prev = 20,
        # screen_keys = ['None'],
        schcfg_keys = ['k5'],
    )
    pop_size = cfg.sim_pars.pop_size

    runner = BaselineK5(sweep_pars=sweep_pars, sim_pars=dict(pop_size=pop_size))
    runner.run(args.force)
    analyzer = runner.analyze()

    runner.regplots(xvar='Prevalence Target', huevar='Dx Screening')

    analyzer.cum_incidence(colvar='Prevalence Target')
    analyzer.introductions_rate_by_stype(xvar='Prevalence Target')
    analyzer.outbreak_size_over_time()
    analyzer.source_pie()
    analyzer.source_dow(figsize=(6.5,5))
    runner.tsplots()
