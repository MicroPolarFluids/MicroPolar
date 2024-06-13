import h5py
from shenfun import *
from mpi4py_fft import fftw 
import matplotlib.pyplot as plt 

moin = np.loadtxt('chan180.xspec.5')

# Use checkpoint data
data = h5py.File('MKM_MP_64_64_32.chk.h5', 'r') # complex data
N = data['U/0'].shape[1:]
D0 = FunctionSpace(N[0], 'C', bc=(0, 0))
F1 = FunctionSpace(N[1], 'F', dtype='D', domain=(0, 4*np.pi))
F2 = FunctionSpace((N[2]-1)*2, 'F', dtype='d', domain=(0, 2*np.pi))
TD = TensorProductSpace(comm, (D0, F1, F2))
v = TD.backward(data['U/0'][1], mesh='uniform')

# Alternatively from stored real data
#data = h5py.File('MKM_MP_64_64_32_U.h5', 'r')
#v = data['/u1/3D/17000']

vj = (v[2] - np.mean(v[2], axis=(0, 1)))
fft = fftw.rfftn(vj.copy(), axes=((0,)))
vk = fft(vj, normalize=True)
Ek = np.mean(np.abs(vk)**2, axis=1)
kx = np.fft.rfftfreq(vj.shape[0], d=2/vj.shape[0])

plt.loglog(kx[1:-1], Ek[1:-1], 'b')
plt.loglog(moin[1:, 0], moin[1:, 1], '--')
plt.show()

