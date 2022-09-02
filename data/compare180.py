from numpy import *
from matplotlib import pyplot as plt
from shenfun import FunctionSpace
import h5py

N = 128
ST = FunctionSpace(N, 'C', bc=(0, 0), quad="GC")
SB = FunctionSpace(N, 'C', bc=(0, 0, 0, 0), quad="GC")

y, w = ST.points_and_weights(N)

kmm = loadtxt('chan180.means')
rss = loadtxt('chan180.reystress')
data = h5py.File('KMM776statsc.h5')
V = array(data['Average/V'])
V = 0.5*(V[:N//2]+ V[N:-N//2-1:-1])
UU = array(data['Reynolds Stress/UU'])
UU = 0.5*(UU[:N//2]+ UU[N:-N//2-1:-1])
VV = array(data['Reynolds Stress/VV'])
VV = 0.5*(VV[:N//2]+ VV[N:-N//2-1:-1])
WW = array(data['Reynolds Stress/WW'])
WW = 0.5*(WW[:N//2]+ WW[N:-N//2-1:-1])
UV = array(data['Reynolds Stress/UV'])

print('Flux', trapz(kmm[:, 2], kmm[:, 0])*(2*pi)**2)

plt.figure()
plt.plot(kmm[:, 0], kmm[:, 2], 'b')
#plt.semilogx(1-y[:N//2], V, 'r')
plt.plot(1-y[:N//2], V, 'r')

plt.figure()
plot = plt.loglog
plot(rss[1:, 0], rss[1:, 2], 'b', rss[1:, 0], rss[1:, 3], 'b', rss[1:, 0], rss[1:, 4], 'b')
plot(1-y[:N//2], UU, 'r', 1-y[:N//2], VV-V*V, 'r', 1-y[:N//2], WW, 'r')

plt.show()
