# Direct Numerical Simulations (DNS) of MicroPolar Fluids.

The micropolar equations are given as

$$ 
\begin{align}
\frac{\partial \vec{u}}{\partial t} + (\vec{u} \cdot \nabla)\vec{u} &= -\nabla p + \frac{1}{Re}\nabla^2 \vec{u} + \frac{m}{Re}\nabla \times \vec{w} \\
\frac{JN}{m}\left(\frac{\partial \vec{w}}{\partial t} + (\vec{u} \cdot \nabla)\vec{w}\right) &= \frac{1}{Re}\nabla^2 \vec{w} + \frac{N}{Re}\nabla \times \vec{u} - \frac{2N}{Re}\vec{w}
\end{align}
$$

where $\vec{u} \text{ and } \vec{w}$ are the linear and angular velocity vectors, respectively, $p$ is pressure and $m, J, N \text{ and } Re$ are parameters. The equations are solved in a three-dimensional channel configuration, with orthogonal polynomials (Chebyshev) in the wall-normal direction and Fourier exponentials in the streamwise and spanwise directions. For time-integration we can choose between several IMEX Runge Kutta methods of different order and accuracy. More information about micropolar fluid flow can be found in 

    George Sofadis and Ioannis Sarris "Microrotation viscosity effect on turbulent micropolar fluid channel flow", 
    Phys. Fluids 33, 095126 (2021); doi: 10.1063/5.0063591

The DNS solver is based on [shenfun](https://github.com/spectralDNS/shenfun). Shenfun is a high performance computing platform for solving partial differential equations (PDEs) by the spectral Galerkin method. 
Shenfun has quite a few dependencies 

- [mpi4py](https://bitbucket.org/mpi4py/mpi4py)
- [FFTW](http://www.fftw.org)
- [mpi4py-fft](https://bitbucket.org/mpi4py/mpi4py-fft)
- [cython](http://cython.org)
- [numpy](https://www.numpy.org)
- [sympy](https://www.sympy.org)
- [scipy](https://www.scipy.org)
- [h5py](https://www.h5py.org)
- [pyyaml](https://pypi.org/project/PyYAML/)

that are mostly straight-forward to install, or already installed in
most Python environments. The first two are usually most troublesome.
Basically, for [mpi4py](https://bitbucket.org/mpi4py/mpi4py) you need to 
have a working MPI installation,
whereas [FFTW](http://www.fftw.org) is available on most high performance computer systems.
If you are using [conda](https://conda.io/docs/), which is strongly reccommended, then 
all you need to install a fully functional
shenfun, with all the above dependencies, is

    conda install -c conda-forge shenfun

You probably want to install into a fresh environment, though, which
can be achieved with

    conda create --name shenfun -c conda-forge shenfun
    conda activate shenfun

Note that this gives you shenfun with default settings. This means that
you will probably get the openmpi backend. To make sure that shenfun is
is installed with mpich instead do

    conda create --name shenfun -c conda-forge shenfun mpich

If you do not use [conda](https://conda.io/docs/), then you need to make sure that MPI
and FFTW are installed by some other means. You can then install
any version of shenfun hosted on [pypi](https://pypi.org/project/shenfun/) 
using [pip](https://pypi.org/project/pip/)

    pip install shenfun

whereas the following will install the latest version from github

    pip install git+https://github.com/spectralDNS/shenfun.git@master

Note that a common approach is to install ``shenfun`` from ``conda-forge`` to
get all the dependencies, and then build a local version by (after cloning or
forking to a local folder) running from the top directory

    pip install .

or

    python setup.py build_ext -i

This is required to build all the Cython dependencies locally. To use the local 
version instead of the one installed through conda-forge, you need to add the
folder where shenfun lives to the PYTHONPATH

    export PYTHONPATH='local folder for shenfun':$PYTHONPATH
   
This is the approach used by the main developer of shenfun:-)
