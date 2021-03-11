'''
Main file implementing school-based interventions.  The user interface is handled
by the schools_manager() intervention. This primarily uses the School class, of
which there is one instance per school. SchoolTesting orchestrates testing within
a school, while SchoolStats records results. The remaining functions are contact
managers, which handle different cohorting options (and school days).
'''

import covasim as cv
import numpy as np
from .controller import Controller as ct
from .Kalman import Kalman as kf


__all__ = ['controller_intervention']

class controller_intervention(cv.Intervention):
    '''
    Control prevalence to a certain value.
    '''

    def __init__(self, SEIR, targets, pole_loc=None, start_day=0, **kwargs):
        super().__init__(**kwargs) # Initialize the Intervention object
        self._store_args() # Store the input arguments so that intervention can be recreated

        self.verbose = False

        # Store arguments
        self.targets = targets
        self.SEIR = SEIR
        self.u_k =  None

        self.start_day = start_day
        self.end_date = '2099-12-02'

        self.Controller = ct(SEIR, pole_loc=pole_loc)
        self.integrated_err = 0
        return


    def initialize(self, sim):
        self.beta0 = sim.pars['beta']
        self.beta_layer0 = sim.pars['beta_layer'].copy()
        self.u_k = sim.pars['beta'] * np.ones(sim.pars['n_days']+1)

        initial_exposed_pop = np.sum(sim.people.exposed)
        self.Kalman = kf(initial_exposed_pop, self.SEIR)
        self.initialized = True
        return


    def apply(self, sim):
        if self.verbose: print(sim.t, '-'*80)
        #if sim.t == sim.day('2020-11-02'):
        #    import time
        #    r = np.random.rand(int(time.time_ns() % 1e4)) # Pull a random number to mess up the stream

        y = sim.results['n_exposed'][sim.t-1] # np.sum(sim.people.exposed)#
        N = sim.scaled_pop_size # don't really care about N vs alive...
        S = N - np.count_nonzero(~np.isnan(sim.people.date_exposed)) #sim.results['cum_infections'][sim.t-1]
        I = np.sum(sim.people.infectious)#sim.results['n_infectious'][sim.t-1]
        E = y - I

        if self.verbose: print('NEW EXPOSURES:', sim.results['new_infections'][sim.t-1])

        if sim.t < self.start_day or S*I==0:
            u = sim.results['new_infections'][sim.t-1] # S*I/N # np.sum(sim.people.date_exposed == sim.t-1)
            self.Kalman.update(E, I, u)

            '''
            # BEGIN TEMP
            xs = S
            Ihat = self.Kalman.Ihat()
            xi = np.sum(Ihat)
            xi += np.sum(Ihat[:3]) # Double infectivity early
            if xi > 0:
                xi = np.power(xi, self.SEIR.Ipow) # Ipow - do this in SEIR class where Ipow is known?
            SI_by_N = xs*xi / N
            expecting = 18*sim.pars['beta'] * SI_by_N
            if self.verbose: print(f'EXPECTING {expecting}')
            # END TEMP
            '''

        else:

            Xu = np.vstack([self.Kalman.EIhat, self.integrated_err])
            #if self.verbose: print('Covasim Xu\n', Xu)
            u = self.Controller.get_control(Xu)
            u = np.maximum(u,0)

            # Should be in conditional
            self.Kalman.update(E, I, u)

            #if self.verbose: print(f'Covasim E={E:.0f}, I={I:.0f} | SEIR E={np.sum(self.Kalman.Ehat()):.0f}, I={np.sum(self.Kalman.Ihat()):.0f} --> U={u:.1f}, beta={sim.pars["beta"]}')

            # TODO: In SEIR class?
            xs = S
            Ihat = self.Kalman.Ihat()

            xi = np.sum(Ihat)
            xi += np.sum(Ihat[:3]) # Double infectivity early

            if xi > 0:
                xi = np.power(xi, self.SEIR.Ipow) # Ipow - do this in SEIR class where Ipow is known?
                SI_by_N = xs*xi / N
                new_beta = np.maximum(u / SI_by_N, 0)

                if self.verbose: print('WARNING: shrinking beta!')
                new_beta /= 18
            else:
                print(f'WARNING: Estimate of infectious population ({xi}) is negative!')
                new_beta = self.beta0 # Hmm!

            if False:
                # Set beta directly - includes all layers including inside each school
                sim.pars['beta'] = new_beta
            else:
                # Set beta_layer for all "traditional" layers, will include individuals schools if using covid_schools
                for lkey in ['h', 's', 'w', 'c', 'l']:
                    sim.pars['beta_layer'][lkey] = self.beta_layer0[lkey] * new_beta / self.beta0
            self.u_k[sim.t] = new_beta

            if self.verbose:
                print(f'CONTROLLER IS ASKING FOR {u} NEW EXPOSURES')

                print(f'New Error --- y={y}, n_exp={sim.results["n_exposed"][sim.t-1]}, t={self.targets["infected"]}, err={y - self.targets["infected"]} --> int err now {self.integrated_err}')

            self.integrated_err = self.integrated_err + y - self.targets['infected'] # TODO: use ReferenceTrajectory class

        return
