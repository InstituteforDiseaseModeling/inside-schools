import numpy as np

__all__ = ['SEIR', 'TransitionMatrix']

class TransitionMatrix:
    def __init__(self):
        pass

    def full(self, p):
        n = int((-1 + np.sqrt( (1 + 8*len(p)) ))/2)
        M = np.zeros((n,n))
        np.put(M, np.ravel_multi_index(np.tril_indices(n), M.shape), p)

        return M

class SEIR:
    def __init__(self, nSteps, dt, EI, IR, C=None):

        self.nSteps = nSteps
        self.dt = dt
        self.EI = EI
        self.IR = IR
        self.C = C

        self._build()
        self.check_controllability()
        self.check_observability()

        self.X = np.matrix(np.zeros((self.A.shape[0], self.nSteps)))

    def _build(self):

        belowEI = np.zeros((self.nIR, self.nEI))
        belowEI[0,:] = 1-np.sum(self.EI, axis=0)
        belowIR = 1-np.sum(self.IR, axis=0)
        nEI = self.EI.shape[0]
        nIR = self.nIR.shape[0]

        # Full SEIR Dynamics
        self.A = np.block( [
            [1,                 np.zeros(nEI),     np.zeros(nIR),       0                   ],
            [np.zeros((nEI,1)), self.EI,           np.zeros((nEI,nIR)), np.zeros((nEI,1))   ],
            [np.zeros((nIR,1)), belowEI,           self.IR,             np.zeros((nIR,1))   ],
            [0,                 np.zeros((1,nEI)), belowIR,             1                   ] ])

        self.B = np.matrix(np.zeros((2+nEI+nIR,1)))
        self.B[0] = -1
        self.B[1] = 1

        if self.C is not None:
            self.C = np.matrix(np.zeros((1,2+nEI+nIR)))
            self.C[:, 1:-1] = 1

    def check_observability(self, EIonly=True):
        # Check EI observability
        inds = np.s_[1:-1] if EIonly else np.s_[:]
        A = self.A[inds, inds]
        C = self.C[:, inds]

        Omats = [C]
        for i in range(1,self.nEIR):
            Omats.append(Omats[-1]*A)
        obs_mat = np.vstack(Omats)
        assert(np.linalg.matrix_rank(obs_mat) == self.nEIR)

        return obs_mat

    ''' TODO
    def check_controllability(self, EIonly=True):
        ctrb = np.matrix(np.zeros((nEI+nIR+1, nEI+nIR+1))) # +1 for error dynamics
        ctrb[:,0] = Bc
        for i in range(nEI+nIR):
            ctrb[:,i+1] = Ac*ctrb[:,i] # columns of controllability matrix
    '''

    def step(self, dt):
        pass
