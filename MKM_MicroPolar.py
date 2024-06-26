import matplotlib.pyplot as plt
from shenfun import *
from MicroPolar import MicroPolar
import h5py


class MKM(MicroPolar):

    def __init__(self,
                 N=(128, 128, 64),
                 domain=((-1, 1), (0, 4*np.pi), (0, 2*np.pi)),
                 Re=180.,
                 J=1e-5,
                 m=0.001,
                 NP=8.3e4,
                 dt=0.1,
                 conv=0,
                 utau=1,
                 modplot=100,
                 modsave=1e8,
                 moderror=100,
                 sample_stats=1e8,
                 filename='MKM_Polar',
                 family='C',
                 padding_factor=(1, 1.5, 1.5),
                 checkpoint=1000,
                 timestepper='IMEXRK3',
                 probes=None,
                 rand=1e-7):
        MicroPolar.__init__(self, N=N, domain=domain, Re=Re, J=J, m=m, NP=NP, dt=dt, conv=conv, utau=utau, modplot=modplot,
                            modsave=modsave, moderror=moderror, filename=filename, family=family,
                            padding_factor=padding_factor, checkpoint=checkpoint, timestepper=timestepper)
        self.rand = rand
        self.Volume = inner(1, Array(self.TD, val=1))
        self.flux = np.array([2486.56]) # Re_tau=180. This is 16*np.pi**2*15.67, where 15.67 = Umean/utau
        self.sample_stats = sample_stats
        self.stats = Stats(N, self.B0.mesh(), self.TD.local_slice(False), filename=filename+'_stats')
        self.probes = Probe(probes, {'u': self.u_, 'w': self.w_}, filename=filename) if probes is not None else None
        TL = self.TC.get_unplanned()
        TL[0].quad = 'GL'
        self.TL = TensorProductSpace(comm, TL, slab=True) # Use this space to get dvdx on the walls. GL is Gauss-Lobatto, which includes the wall
        self.dvdx = Project(grad(self.u_[1])[0], self.TL) # This is a class used to compute dvdx on GL points

    def initialize(self, from_checkpoint=False):
        if from_checkpoint:
            return self.init_from_checkpoint()

        X = self.X
        Y = np.where(X[0] < 0, 1+X[0], 1-X[0])
        utau = self.nu*self.Re
        Um = 46.9091*utau # For Re=180
        Re = self.Re
        Xplus = Y*Re
        Yplus = X[1]*Re
        Zplus = X[2]*Re
        duplus = Um*0.2/utau  #Um*0.25/utau
        alfaplus = self.F1.domain[1]/200.  # May have to adjust these two for different Re
        betaplus = self.F2.domain[1]/100.  #
        sigma = 0.00055 # 0.00055
        epsilon = Um/200.   #Um/200.
        U = Array(self.BD)
        U[1] = Um*(Y-0.5*Y**2)
        dev = 1+self.rand*np.random.randn(Y.shape[0], Y.shape[1], Y.shape[2])
        #dev = np.fromfile('dev.dat').reshape((64, 64, 64))
        dd = utau*duplus/2.0*Xplus/40.*np.exp(-sigma*Xplus**2+0.5)*np.cos(betaplus*Zplus)*dev[:, slice(0, 1), :]
        U[1] += dd
        U[2] += epsilon*np.sin(alfaplus*Yplus)*Xplus*np.exp(-sigma*Xplus**2)*dev[:, :, slice(0, 1)]
        u_ = U.forward(self.u_)
        u_.mask_nyquist(self.mask)
        U = u_.backward(U)
        u_ = U.forward(self.u_)
        self.g_[:] = 1j*self.K[1]*u_[2] - 1j*self.K[2]*u_[1]
        return 0, 0

    def init_plots(self):
        ub = self.u_.backward(self.ub)
        self.im1 = 1
        if comm.Get_rank() == 0:

            plt.figure(1, figsize=(6, 3))
            self.im1 = plt.contourf(self.X[1][:, :, 0], self.X[0][:, :, 0], ub[0, :, :, 0], 100)
            plt.colorbar(self.im1)
            plt.draw()

            plt.figure(2, figsize=(6, 3))
            self.im2 = plt.contourf(self.X[1][:, :, 0], self.X[0][:, :, 0], ub[1, :, :, 0], 100)
            plt.colorbar(self.im2)
            plt.draw()

            plt.figure(3, figsize=(6, 3))
            self.im3 = plt.contourf(self.X[2][:, 0, :], self.X[0][:, 0, :], ub[0, :, 0, :], 100)
            plt.colorbar(self.im3)
            plt.draw()

            if comm.Get_size() == 1:
                plt.figure(4, figsize=(6, 3))
                self.im4 = plt.plot(self.X[0][:, 0, 0], ub[0, :, 0, 0])[0]
                plt.draw()


    def plot(self, t, tstep):
        if self.im1 is None and self.modplot > 0:
            self.init_plots()

        if tstep % self.modplot == 0 and self.modplot > 0:
            ub = self.u_.backward(self.ub)
            if comm.Get_rank() == 0:
                X = self.X
                self.im1.axes.contourf(X[1][:, :, 0], X[0][:, :, 0], ub[0, :, :, 0], 100)
                self.im1.autoscale()
                plt.figure(1)
                plt.pause(1e-6)
                self.im2.axes.contourf(X[1][:, :, 0], X[0][:, :, 0], ub[1, :, :, 0], 100)
                self.im2.autoscale()
                plt.figure(2)
                plt.pause(1e-6)
                self.im3.axes.contourf(X[2][:, 0, :], X[0][:, 0, :], ub[0, :, 0, :], 100)
                self.im3.autoscale()
                plt.figure(3)
                plt.pause(1e-6)

    def print_energy_and_divergence(self, t, tstep):
        if tstep % self.moderror == 0 and self.moderror > 0:
            ub = self.u_.backward(self.ub)
            wb = self.w_.backward(self.wb)
            e0 = inner(1, ub[0]*ub[0])
            e1 = inner(1, ub[1]*ub[1])
            e2 = inner(1, ub[2]*ub[2])
            d0 = inner(1, wb[0]*wb[0])
            d1 = inner(1, wb[1]*wb[1])
            d2 = inner(1, wb[2]*wb[2])
            q = inner(1, ub[1])
            divu = self.divu().backward()
            e3 = np.sqrt(inner(1, divu*divu))
            # Find utau
            dvdx = self.dvdx().backward()
            utau0 = 0 # at x = -1
            utau1 = 0 # at x = 1
            if self.TL.local_slice(False)[0].start == 0: # The processor that owns the plane x = -1
                utau0 = np.mean(np.sqrt(np.abs(self.nu*dvdx[0])))
            if self.TL.local_slice(False)[0].stop == self.N[0]: # The processors that owns the plane x = 1
                utau1 = np.mean(np.sqrt(np.abs(self.nu*dvdx[-1])))
            utau = comm.reduce(utau0+utau1)
            if comm.Get_rank() == 0:
                utau = utau/2
                if tstep % (10*self.moderror) == 0 or tstep == 0:
                    print(f"{'Time':^11}{'uu':^11}{'vv':^11}{'ww':^11}{'a0*a0':^11}{'a1*a1':^11}{'a2*a2':^11}{'flux':^11}{'div':^11}{'utau':^11}")
                print(f"{t:2.4e} {e0:2.4e} {e1:2.4e} {e2:2.4e} {d0:2.4e} {d1:2.4e} {d2:2.4e} {q:2.4e} {e3:2.4e} {utau:2.4e}")

    def update(self, t, tstep):
        self.plot(t, tstep)
        self.print_energy_and_divergence(t, tstep)
        if self.probes is not None:
            self.probes()

        if tstep % self.sample_stats == 0:        
            ub = self.u_.backward(self.ub)
            wb = self.w_.backward(self.wb)
            self.curly() # Compute y-component of curl. Stored in self.curl[1]
            self.curlz() # Compute z-component of curl. Stored in self.curl[2]
            curl = self.curl.backward()
            self.stats(ub, wb, curl)
            if self.probes is not None:
                self.probes.tofile()

            if comm.Get_size() == 1 and self.modplot > 0:
                stats = self.stats.get_stats()
                u0, w0 = stats[:2]
                x = c.B0.mesh(bcast=False)
                self.im4.axes.plot(x, u0[1], 'b')
                self.im4.axes.plot(x, w0[2], 'r')
                plt.figure(4)
                plt.pause(1e-6)

        # Dynamically adjust flux
        if tstep % 1 == 0:
            ub1 = self.u_[1].backward(self.ub[1])
            beta = inner(1, ub1)
            q = (self.flux[0] - beta)
            if comm.Get_rank() == 0:
                #self.u_[1, 0, 0, 0] += q/self.Volume
                self.u_[1, :, 0, 0] *= (1+q/self.Volume/self.u_[1, 0, 0, 0])


class Probe:
    """Class for probing

    Parameters
    ----------
    probes : np.array
        Must be of shape (D, N), for N probes in D dimensions
    u : dict
        The Functions to probe. All Functions will use the same probes
    fromprobes : str, optional
        If you want to continue appending to a list of values already in the
        h5-file f'{fromprobes}_probes.h5'
    filename : str, optional
        Name of file (f'{filename}_probes.h5') used to store probe values.

    Note
    ----
    You need to call tofile at some point to dump the results to a h5-file.

    Example
    -------
    >>> import numpy as np
    >>> import sympy as sp
    >>> x, y = sp.symbols('x,y')
    >>> D = FunctionSpace(8, 'C')
    >>> T = TensorProductSpace(comm, (D, D))
    >>> u = Function(T, buffer=x+y)
    >>> p = Probe(np.array([[-0.5, 0.5],[-0.1, 0.1]]), {'u': u})
    >>> p()
    >>> p()
    >>> p()
    >>> print(p).U['u']
    [array([-0.6,  0.6]), array([-0.6,  0.6]), array([-0.6,  0.6])]
    """
    def __init__(self, probes, u, fromprobes="", filename=""):
        assert isinstance(u, dict)
        self.x = probes
        self.u = u
        self.fname = filename
        self.U = {name: [] for name in u} # store as lists because they are fast to append
        if fromprobes:
            self.fromfile(filename)

    def fromfile(self):
        if comm.Get_rank() == 0:
            f0 = h5py.File(self.fname+'_probes.h5', "r", driver="mpio", comm=MPI.COMM_SELF)
            for key, val in self.U:
                val[:] = f0[key]
            f0.close()

    def __call__(self):
        for key, val in self.u.items():
            p = val.eval(self.x).tolist()
            if comm.Get_rank() == 0:
                self.U[key].append(p)

    def tofile(self):
        if comm.Get_rank() == 0:
            f0 = h5py.File(self.fname+'_probes.h5', "w", driver="mpio", comm=MPI.COMM_SELF)
            f0.create_dataset('probes', shape=self.x.shape, dtype=float, data=self.x)
            for key, val in self.u.items():
                a = np.array(self.U[key])
                f0.create_dataset(key, shape=a.shape, dtype=val.function_space().forward.input_array.dtype, data=a)
            f0.close()

class Stats:

    def __init__(self, N, x, s, fromstats="", filename=""):
        self.N = N # global shape
        self.x = x # mesh
        self.s = s # local slice
        M = self.s[0].stop-self.s[0].start # local x shape
        self.Q = (self.s[1].stop-self.s[1].start)*(self.s[2].stop-self.s[2].start)
        self.Umean = np.zeros((3, M))
        self.Wmean = np.zeros((3, M))
        self.Curlmean = np.zeros((3, M))
        self.Curlvar = np.zeros(M)
        self.UU = np.zeros((6, M))
        self.WW = np.zeros((6, M))
        self.UW = np.zeros((9, M)) # Not symmetric
        self.Ry = np.zeros((6, N[1]//2, M))
        self.Rz = np.zeros((6, N[2]//2, M))
        self.R = (self.Ry, self.Rz)
        self.helicity_pdf = np.zeros((M, 36))
        self.helicity_prime_pdf = np.zeros((M, 36))
        self.helicity_micro_pdf = np.zeros((M, 36))
        self.helicity_micro_prime_pdf = np.zeros((M, 36))
        self.H_mean = np.zeros(M)
        self.H_prime_mean = np.zeros(M)
        self.H_micro_mean = np.zeros(M)
        self.H_micro_prime_mean = np.zeros(M)
        self.H_var = np.zeros(M)
        self.H_prime_var = np.zeros(M)
        self.H_micro_var = np.zeros(M)
        self.H_micro_prime_var = np.zeros(M)
        self.bins = np.linspace(-1, 1, 37)
        self.symind = ((0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2))
        self.num_samples = 0
        self.fname = filename
        self.f0 = None
        if fromstats:
            self.fromfile(filename=fromstats)

    def create_statsfile(self):
        self.f0 = h5py.File(self.fname+".h5", "w", driver="mpio", comm=comm)
        self.f0.create_dataset('x', shape=(self.N[0],), dtype=float, data=self.x)
        self.f0.create_group("Average Velocity")
        self.f0.create_group("Reynolds Stress Velocity")
        self.f0.create_group("Average Angular Velocity")
        self.f0.create_group("Reynolds Stress Angular Velocity")
        self.f0.create_group("Cross Velocity Angular Velocity")
        self.f0.create_group("Two-point Y Correlations Velocity")
        self.f0.create_group("Two-point Z Correlations Velocity")
        self.f0.create_group("Helicity")
        self.f0.create_group("Helicity_Prime")
        self.f0.create_group("Helicity_Micro")
        self.f0.create_group("Helicity_Micro_Prime")
        self.f0.create_group("Curl")

        for i in ("U", "V", "W"):
            self.f0["Average Velocity"].create_dataset(i, shape=(self.N[0],), dtype=float)
            self.f0["Average Angular Velocity"].create_dataset(i, shape=(self.N[0],), dtype=float)
            self.f0["Curl"].create_dataset(i, shape=(self.N[0],), dtype=float)
        self.f0["Curl"].create_dataset("Var", shape=(self.N[0],), dtype=float)

        # Note that all components have names UU, UV, UW etc. But her U, V and W simply indicate vector component
        # number 0, 1 and 2. So even though the angular velocity is stored as UU, UV, ..., it is still the angular
        # components. And for cross the first item represents velocity and the second angular velocity.
        for i in ("UU", "VV", "WW", "UV", "UW", "VW"):
            self.f0["Reynolds Stress Velocity"].create_dataset(i, shape=(self.N[0],), dtype=float)
            self.f0["Reynolds Stress Angular Velocity"].create_dataset(i, shape=(self.N[0],), dtype=float)
            self.f0["Two-point Y Correlations Velocity"].create_dataset(i, shape=(self.N[1]//2, self.N[0]), dtype=float)
            self.f0["Two-point Z Correlations Velocity"].create_dataset(i, shape=(self.N[2]//2, self.N[0]), dtype=float)
        for i in ("UU", "UV", "UW", "VU", "VV", "VW", "WU", "WV", "WW"):
            self.f0["Cross Velocity Angular Velocity"].create_dataset(i, shape=(self.N[0],), dtype=float)

        self.f0["Helicity"].create_dataset("PDF", shape=(self.N[0], 36), dtype=float)
        self.f0["Helicity"].create_dataset("Hmean", shape=(self.N[0],), dtype=float)
        self.f0["Helicity"].create_dataset("Hvar", shape=(self.N[0],), dtype=float)

        self.f0["Helicity_Prime"].create_dataset("PDF", shape=(self.N[0], 36), dtype=float)
        self.f0["Helicity_Prime"].create_dataset("Hmean", shape=(self.N[0],), dtype=float)
        self.f0["Helicity_Prime"].create_dataset("Hvar", shape=(self.N[0],), dtype=float)

        self.f0["Helicity_Micro"].create_dataset("PDF", shape=(self.N[0], 36), dtype=float)
        self.f0["Helicity_Micro"].create_dataset("Hmean", shape=(self.N[0],), dtype=float)
        self.f0["Helicity_Micro"].create_dataset("Hvar", shape=(self.N[0],), dtype=float)

        self.f0["Helicity_Micro_Prime"].create_dataset("PDF", shape=(self.N[0], 36), dtype=float)
        self.f0["Helicity_Micro_Prime"].create_dataset("Hmean", shape=(self.N[0],), dtype=float)
        self.f0["Helicity_Micro_Prime"].create_dataset("Hvar", shape=(self.N[0],), dtype=float)



    def __call__(self, U, W, curl):
        self.num_samples += 1
        self.Umean += np.sum(U, axis=(2, 3))
        self.Wmean += np.sum(W, axis=(2, 3))
        self.UU[0] += np.sum(U[0]*U[0], axis=(1, 2))
        self.UU[1] += np.sum(U[1]*U[1], axis=(1, 2))
        self.UU[2] += np.sum(U[2]*U[2], axis=(1, 2))
        self.UU[3] += np.sum(U[0]*U[1], axis=(1, 2))
        self.UU[4] += np.sum(U[0]*U[2], axis=(1, 2))
        self.UU[5] += np.sum(U[1]*U[2], axis=(1, 2))
        self.WW[0] += np.sum(W[0]*W[0], axis=(1, 2))
        self.WW[1] += np.sum(W[1]*W[1], axis=(1, 2))
        self.WW[2] += np.sum(W[2]*W[2], axis=(1, 2))
        self.WW[3] += np.sum(W[0]*W[1], axis=(1, 2))
        self.WW[4] += np.sum(W[0]*W[2], axis=(1, 2))
        self.WW[5] += np.sum(W[1]*W[2], axis=(1, 2))
        self.UW[0] += np.sum(U[0]*W[0], axis=(1, 2))
        self.UW[1] += np.sum(U[0]*W[1], axis=(1, 2))
        self.UW[2] += np.sum(U[0]*W[2], axis=(1, 2))
        self.UW[3] += np.sum(U[1]*W[0], axis=(1, 2))
        self.UW[4] += np.sum(U[1]*W[1], axis=(1, 2))
        self.UW[5] += np.sum(U[1]*W[2], axis=(1, 2))
        self.UW[6] += np.sum(U[2]*W[0], axis=(1, 2))
        self.UW[7] += np.sum(U[2]*W[1], axis=(1, 2))
        self.UW[8] += np.sum(U[2]*W[2], axis=(1, 2))
        for i in (0, 1): # y/z directions
            for j in range(6): # UU, VV, WW, UV, UW, VW
                R = self.R[i][j]
                k, l = self.symind[j]
                for n in range(R.shape[0]): # n*dy/n*dz
                    R[n] += np.sum(U[k].take(range(0, self.N[i+1]), axis=i+1, mode='wrap')*U[l].take(range(n, self.N[i+1]+n), axis=i+1, mode='wrap'), axis=(1, 2))

        Nd = self.num_samples*self.Q
        self.Curlmean += np.sum(curl, axis=(2, 3))
        self.Curlvar += np.sum(curl*curl, axis=(0, 2, 3))

        ###########-- Fluctuations --############################
        Up = U-self.Umean[:, :, None, None]/Nd          #Hydrod. Velocity fluct.
        Vorp = curl-self.Curlmean[:, :, None, None]/Nd  #Vorticity fluct.
        Wp = W - self.Wmean[:, :, None, None]/Nd        #Microp. Velocity fluct.
        
        ###########-- Helicity Density --#########################
        H = np.sum(U*curl, axis=0)          #Hydrod. Helicity Density
        Hm = np.sum(U*W, axis=0)            #Microp. Helicity Density
        H_prime = np.sum(Up*Vorp, axis=0)   #Hydrod. Prime Helicity Density
        Hm_prime = np.sum(Up*Wp, axis=0)    #Microp. Prime Helicity Density

        ###########-- Magnitudes --#########################
        Umag = np.sqrt(np.sum(U*U, axis=0))
        Vormag = np.sqrt(np.sum(curl*curl, axis=0)) 
        Wmag = np.sqrt(np.sum(W*W, axis=0))

        Upmag = np.sqrt(np.sum(Up*Up, axis=0))
        Vorpmag = np.sqrt(np.sum(Vorp*Vorp, axis=0)) 
        Wpmag = np.sqrt(np.sum(Wp*Wp, axis=0))   

        ###########-- Theta Values --#########################
        theta = H / (Umag*Vormag)
        for i in range(theta.shape[0]):
            self.helicity_pdf[i] += np.histogram(theta[i], self.bins)[0]
        self.H_mean += np.sum(H, axis=(1, 2))
        self.H_var += np.sum(H**2, axis=(1, 2))
        self.get_stats()

        theta_prime = H_prime / (Upmag*Vorpmag)
        for i in range(theta_prime.shape[0]):
            self.helicity_prime_pdf[i] += np.histogram(theta_prime[i], self.bins)[0]
        self.H_prime_mean += np.sum(H_prime, axis=(1, 2))
        self.H_prime_var += np.sum(H_prime**2, axis=(1, 2))
        self.get_stats()

        theta_micro = Hm / (Umag*Wmag)
        for i in range(theta_micro.shape[0]):
            self.helicity_micro_pdf[i] += np.histogram(theta_micro[i], self.bins)[0]
        self.H_micro_mean += np.sum(Hm, axis=(1, 2))
        self.H_micro_var += np.sum(Hm**2, axis=(1, 2))
        self.get_stats()

        theta_micro_prime = Hm_prime / (Upmag*Wpmag)
        for i in range(theta_micro_prime.shape[0]):
            self.helicity_micro_prime_pdf[i] += np.histogram(theta_micro_prime[i], self.bins)[0]
        self.H_micro_prime_mean += np.sum(Hm_prime, axis=(1, 2))
        self.H_micro_prime_var += np.sum(Hm_prime**2, axis=(1, 2))
        self.get_stats()

        #########################################################



    def get_stats(self, tofile=True):
        s = self.s[0]
        Nd = self.num_samples*self.Q
        comm.barrier()
        if tofile:
            if self.f0 is None:
                self.create_statsfile()
            else:
                self.f0 = h5py.File(self.fname+".h5", "a", driver="mpio", comm=comm)

            for i, name in enumerate(("U", "V", "W")):
                self.f0["Average Velocity/"+name][s] = self.Umean[i]/Nd
                self.f0["Average Angular Velocity/"+name][s] = self.Wmean[i]/Nd
                self.f0["Curl/"+name][s] = self.Curlmean[i]/Nd
            self.f0["Curl/Var"][s] = self.Curlvar/Nd

            sl = (slice(None), s)
            for i, name in enumerate(("UU", "VV", "WW", "UV", "UW", "VW")):
                self.f0["Reynolds Stress Velocity/"+name][s] = self.UU[i]/Nd
                self.f0["Reynolds Stress Angular Velocity/"+name][s] = self.WW[i]/Nd
                self.f0["Two-point Y Correlations Velocity/"+name][sl] = self.Ry[i]/Nd
                self.f0["Two-point Z Correlations Velocity/"+name][sl] = self.Rz[i]/Nd

            for i, name in enumerate(("UU", "UV", "UW", "VU", "VV", "VW", "WU", "WV", "WW")):
                self.f0["Cross Velocity Angular Velocity/"+name][s] = self.UW[i]/Nd

            self.f0["Helicity/PDF"][s] = self.helicity_pdf/Nd
            self.f0["Helicity/Hmean"][s] = self.H_mean/Nd
            self.f0["Helicity/Hvar"][s] = self.H_var/Nd

            self.f0["Helicity_Prime/PDF"][s] = self.helicity_prime_pdf/Nd
            self.f0["Helicity_Prime/Hmean"][s] = self.H_prime_mean/Nd
            self.f0["Helicity_Prime/Hvar"][s] = self.H_prime_var/Nd

            self.f0["Helicity_Micro/PDF"][s] = self.helicity_micro_pdf/Nd
            self.f0["Helicity_Micro/Hmean"][s] = self.H_micro_mean/Nd
            self.f0["Helicity_Micro/Hvar"][s] = self.H_micro_var/Nd

            self.f0["Helicity_Micro_Prime/PDF"][s] = self.helicity_micro_prime_pdf/Nd
            self.f0["Helicity_Micro_Prime/Hmean"][s] = self.H_micro_prime_mean/Nd
            self.f0["Helicity_Micro_Prime/Hvar"][s] = self.H_micro_prime_var/Nd


            self.f0["Curl/Var"][s] = self.Curlvar/Nd

            self.f0.attrs.create("num_samples", self.num_samples)
            self.f0.close()

        if comm.Get_size() == 1:
            return self.Umean/Nd, self.Wmean/Nd, self.UU/Nd, self.WW/Nd, self.UW/Nd

        if comm.Get_rank() == 0:
            # Return the whole, collected array on rank 0
            f0 = h5py.File(self.fname+".h5", "r", driver='mpio', comm=MPI.COMM_SELF)
            data = (np.array([f0[f'Average Velocity/{name}'] for name in 'UVW']),
                    np.array([f0[f'Average Angular Velocity/{name}'] for name in 'UVW']),
                    np.array([f0[f'Reynolds Stress Velocity/{name}'] for name in ('UU', 'VV', 'WW', 'UV', 'UW', 'VW')]),
                    np.array([f0[f'Reynolds Stress Angular Velocity/{name}'] for name in ('UU', 'VV', 'WW', 'UV', 'UW', 'VW')]),
                    np.array([f0[f'Cross Velocity Angular Velocity/{name}'] for name in ('UU', 'UV', 'UW', 'VU', 'VV', 'VW', 'WU', 'WV', 'WW')]),
                    np.array([f0[f'Two-point Y Correlations Velocity/{name}'] for name in ('UU', 'VV', 'WW', 'UV', 'UW', 'VW')]),
                    np.array([f0[f'Two-point Z Correlations Velocity/{name}'] for name in ('UU', 'VV', 'WW', 'UV', 'UW', 'VW')]),
                    np.array([f0['Helicity/PDF']]),
                    np.array([f0['Helicity/Hmean']]),
                    np.array([f0['Helicity/Hvar']]),
                    np.array([f0['Helicity_Prime/PDF']]),
                    np.array([f0['Helicity_Prime/Hmean']]),
                    np.array([f0['Helicity_Prime/Hvar']]),
                    np.array([f0['Helicity_Micro/PDF']]),
                    np.array([f0['Helicity_Micro/Hmean']]),
                    np.array([f0['Helicity_Micro/Hvar']]),
                    np.array([f0['Helicity_Micro_Prime/PDF']]),
                    np.array([f0['Helicity_Micro_Prime/Hmean']]),
                    np.array([f0['Helicity_Micro_Prime/Hvar']]),
                    np.array([f0[f'Curl/{name}'] for name in 'UVW']),
                    np.array([f0['Curl/Var']]))

            f0.close()
            return data

    def reset_stats(self):
        self.num_samples = 0
        self.Umean[:] = 0
        self.Wmean[:] = 0
        self.UU[:] = 0
        self.WW[:] = 0
        self.UW[:] = 0
        self.Ry[:] = 0
        self.Rz[:] = 0
        self.helicity_pdf[:] = 0
        self.H_mean[:] = 0
        self.H_var[:] = 0
        self.helicity_prime_pdf[:] = 0
        self.H_prime_mean[:] = 0
        self.H_prime_var[:] = 0
        self.helicity_micro_pdf[:] = 0
        self.H_micro_mean[:] = 0
        self.H_micro_var[:] = 0
        self.helicity_micro_prime_pdf[:] = 0
        self.H_micro_prime_mean[:] = 0
        self.H_micro_prime_var[:] = 0
        self.Curlmean[:] = 0
        self.Curlvar[:] = 0

    def fromfile(self, filename="stats"):
        self.fname = filename
        self.f0 = h5py.File(filename+".h5", "a", driver="mpio", comm=comm)
        self.num_samples = self.f0.attrs["num_samples"]
        M = (self.s[1].stop-self.s[1].start)*(self.s[2].stop-self.s[2].start)
        Nd = self.num_samples*M
        s = self.s[0]
        for i, name in enumerate(("U", "V", "W")):
            self.Umean[i, :] = self.f0["Average Velocity/"+name][s]*Nd
            self.Wmean[i, :] = self.f0["Average Angular Velocity/"+name][s]*Nd
            self.Curlmean[i, :] = self.f0["Curl/"+name][s]*Nd
        for i, name in enumerate(("UU", "VV", "WW", "UV", "UW", "VW")):
            self.UU[i, :] = self.f0["Reynolds Stress Velocity/"+name][s]*Nd
            self.WW[i, :] = self.f0["Reynolds Stress Angular Velocity/"+name][s]*Nd
        for i, name in enumerate(("UU", "UV", "UW", "VU", "VV", "VW", "WU", "WV", "WW")):
            self.UW[i, :] = self.f0["Cross Velocity Angular Velocity/"+name][s]*Nd
        for j, name in enumerate(("UU", "VV", "WW", "UV", "UW", "VW")):
            self.R[0][j, :] = self.f0['Two-point Y Correlations Velocity/'+name][s]*Nd
            self.R[1][j, :] = self.f0['Two-point Z Correlations Velocity/'+name][s]*Nd
        self.helicity_pdf[:] = self.f0['Helicity/PDF'][s]*Nd
        self.H_mean[:] = self.f0['Helicity/Hmean'][s]*Nd
        self.H_var[:] = self.f0['Helicity/Hvar'][s]*Nd
        self.helicity_prime_pdf[:] = self.f0['Helicity_Prime/PDF'][s]*Nd
        self.H_prime_mean[:] = self.f0['Helicity_Prime/Hmean'][s]*Nd
        self.H_prime_var[:] = self.f0['Helicity_Prime/Hvar'][s]*Nd
        self.helicity_micro_pdf[:] = self.f0['Helicity_Micro/PDF'][s]*Nd
        self.H_micro_mean[:] = self.f0['Helicity_Micro/Hmean'][s]*Nd
        self.H_micro_var[:] = self.f0['Helicity_Micro/Hvar'][s]*Nd
        self.helicity_micro_prime_pdf[:] = self.f0['Helicity_Micro_Prime/PDF'][s]*Nd
        self.H_micro_prime_mean[:] = self.f0['Helicity_Micro_Prime/Hmean'][s]*Nd
        self.H_micro_prime_var[:] = self.f0['Helicity_Micro_Prime/Hvar'][s]*Nd
        self.Curlvar[:] = self.f0['Curl/Var'][s]*Nd
        self.f0.close()

if __name__ == '__main__':
    from time import time
    from mpi4py_fft import generate_xdmf
    t0 = time()
    N = (128, 128, 64)
    d = {
        'N': N,
        'Re': 180.,
        'dt': 0.001,
        'utau': 1.0,
        'filename': f'MKM_MP_{N[0]}_{N[1]}_{N[2]}',
        'conv': 1,
        'm': 0.01,
        'modplot': -100,
        'modsave': 100,
        'moderror': 100,
        'family': 'C',
        'checkpoint': 100,
        'sample_stats': 100,
        'padding_factor': (1.5, 1.5, 1.5),
        'probes': None, #np.array([[0.1, 0.2], [0, 0], [0, 0]]), # Two probes at (0.1, 0, 0) and (0.2, 0, 0).
        'timestepper': 'IMEXRK222', # IMEXRK222, IMEXRK443, IMEXRK3
        }
    c = MKM(**d)
    t, tstep = c.initialize(from_checkpoint=True)
    c.solve(t=0, tstep=0, end_time=30)
    #print('Computing time %2.4f'%(time()-t0))
    #print(c.TB.local_slice(False), c.ub.shape)
    if comm.Get_rank() == 0:
        generate_xdmf('_'.join((d['filename'], 'U'))+'.h5')
        generate_xdmf('_'.join((d['filename'], 'W'))+'.h5')
    stats = c.stats.get_stats()
    if comm.Get_rank() == 0:
        u0, w0, uu, ww, uw = stats
        x = c.B0.mesh(bcast=False)
        plt.figure()
        plt.semilogx((1-x[:32])*180, u0[1, :32], 'r', (1+x[32:])*180, u0[1, 32:], 'b')
        plt.figure()
        plt.semilogx((1+x[32:])*180, w0[2, 32:], 'b', (1-x[:32])*180, -w0[2, :32], 'r')
        plt.figure()
        # multiply by utau=0.0635 to get the same scaling as fig 7
        plt.semilogx((x[32:] + 1)*180, np.sqrt(ww[1, 32:])*0.0635, 'b', (1 - x[:32])*180, np.sqrt(ww[1, :32])*0.0635, 'r')
        #plt.show()
