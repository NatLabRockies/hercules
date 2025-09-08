# Installation on Kestrel

This document outlines the process for install hercules onto NREL's Kestrel
computer.  

The initial steps for running on Kestrel are the same as those outlined in **Local installation instructions**.  Once those steps are complete, 
Running hercules in full requires installing AMR-Wind (likely on Kestrel/HPC).
The steps are detailed in section **HPC Installation**.

## Initial Steps: Accessing Kestrel

  1. Log into Kestrel
  2. Establish a root folder such as /home/{user-name}/herc_root
  3. Enter that root folder
  4. Set up a hercules conda environment

This will be needed for the remaining installations

```
module load anaconda3
conda create --name hercules python=3.11
conda activate hercules
```

Edit your ~/.bashrc file to include a helpful shortcut function based on this:

```
env_hercules()
{
        module purge
        module load craype-x86-spr
        module load intel-oneapi-mpi/2021.10.0-intel
        module load intel-oneapi-compilers/2023.2.0
        module load netcdf-c/4.9.2-intel-oneapi-mpi-intel
        module load git/2.40.0
        # module use /nopt/nrel/apps/modules/test/application
        # module load helics/3.4.0-cray-mpich-intel
        module load anaconda3

        conda activate hercules
}
``` 


## Middle Steps: Creating the Hercules conda enviroment
  ### Install SEAS

Go back to herc_root

#### Install SEAS from public repo

```
pip install https://github.com/NREL/SEAS/blob/v1/SEAS.tar.gz?raw=true
```

If this fails can also try but note need special permissions:

```
git clone https://github.nrel.gov/SEAS/SEAS

cd SEAS
git fetch --all
git switch dv/emuwind
cd ..
pip install -e SEAS
```

### Install Hercules

Go back to herc_root

```
git clone https://github.com/NREL/hercules
pip install -e hercules
```

### Install electrolyzer module

Go back to herc_root

```
git clone git@github.com:NREL/electrolyzer.git
cd electrolyzer
git fetch --all
git switch develop
pip install -e .
```

If you encounter authorization issues cloning the repository, you may need to follow [these](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) steps to generate and add a SSH key to GitHub for your machine, and then set permissions for the SSH keys with:
```
chmod 700 ~/.ssh
chmod 600 ~/.ssh/*
```

### Install PySAM

Note: This section is untested.
Go back to herc_root
```
pip install nrel-pysam==6.0.0
```

If you run hercules and get an error that `pyyaml` is missing, you may also need to install it using
```
conda install -c conda-forge pyyaml
```

### Install the NREL Wind Hybrid Open Controller (WHOC)

This module is used to implement controllers in the Hercules platform. Example 06 has an example of how this is used to control a battery based on wind farm power output.

Note: if you want the newest updates to the WHOC repository, you can checkout the develop branch instead of the main branch.

Installation instructions: 
Go back to herc_root

```
git clone git@github.com:NREL/wind-hybrid-open-controller.git
cd wind-hybrid-open-controller
git fetch --all
pip install -e .
```

## Try an example!

Look at 
herc_root/hercules/example_case_folders/02_amr_wind_standin_only

(May need to edit the port from 32000 to 32001 in bash_script.sh)

```
source bash_script.sh
```

## Final Steps: Setting up AMR-WIND 
The easiest, and currently supported, way to set up AMR-Wind to run on Kestrel is to follow the instructions outlined in **Spack installation of AMR Wind code**.


## Running Hercules
Now that you have successfully installed Hercules, you can start running some simulations. Before starting a simulation, of if you want to submit batch scripts, be sure to activate the spack environment by running the following lines:

```
export SPACK_MANAGER="<absolute path to spack-manager>"
source $SPACK_MANAGER/start.sh
spack-start
quick-activate <absolute path to hercules environment>
PATH=$PATH:<path to where amr-wind is built>
```

The amr-wind build can be found in a spack-build folder inside your hercules enviroment, e.g. in `environment_hercules/amr-wind/spack-build-gsmvjb3`.

Finally, if you want to run simulations with OpenFAST turbine models controlled by ROSCO, you will need to point towards your spack-installed ROSCO library inside your ServoDyn OpenFAST input file. Locating this library can be tricky, for me it lived in `<absolute path to spack-manager> /spack/opt/spack/linux-rhel8-icelake/gcc-8.5.0/ rosco-2.8.0-weyrffl5hydj6eep6ndkezes4iejmzqu/lib/libdiscon.so`. So in your ServoDyn input file, change:

```
<path to where libdiscon is located>/libdiscon.so  DLL_FileName - Name/location of the dynamic library {.dll [Windows] or .so [Linux]} in the Bladed-DLL format (-) [used only with Bladed Interface]
```

## Running a job

For an example of running hercules with AMR-Wind, `cd` to 
hercules/example_case_folders/01_amr_wind_only/. 

Change the line beginning `mpirun` to point to your compiled amr-wind 
executable. This will appear something like:
```
mpirun -n 72 /path/to/amr-wind/build/amr_wind amr_input.inp >> logamr 2>&1
```
Make any other necessary changes to batch_script.sh, and submit it to the 
jobs queue using
```
sbatch batch_script.sh
```

<!--
  ### Setting up AMR-WIND 

First, `deactive` your conda environment using 
```
conda deactivate
```

Then, clone AMR-Wind and install its required submodules. This can be done 
using

EITHER
```
git clone https://github.com/Exawind/amr-wind
cd amr-wind
git submodule update --init
cd ..
``` 
OR
``` 
git clone --recursive https://github.com/Exawind/amr-wind
```

Now, create a new directory `build` within the main AMR-Wind repository
```
mkdir amr-wind/build
```
and copy amr-wind_buildme.sh from hercules into it, naming the copied file 
buildme.sh
```
cp hercules/amr-wind_buildme.sh amr-wind/build/buildme.sh
```

`cd` into the build directory, set executable permissions for buildme.sh, and
run buildme.sh
```
cd amrwind/build
chmod +x buildme.sh
./buildme.sh
```

This will begin compiling an AMR-Wind executable. The process could take 
several minutes, during which progress updates will print to the terminal. 
Once complete, the build directory will contain an executable named amr_wind.

### Running a job

For an example of running hercules with AMR-Wind, `cd` to 
hercules/example_case_folders/example_sim_06/. 

Change the line beginning `mpirun` to point to your compiled amr-wind 
executable. This will appear something like:
```
mpirun -n 72 /path/to/amr-wind/build/amr_wind amr_input.inp >> logamr 2>&1
```
Make any other necessary changes to batch_script.sh, and submit it to the 
jobs queue using
```
sbatch batch_script.sh
```



## Install openfast

(Note this approach mainly follows the instruction set for "CMake with Make for Linux/macOS")
https://openfast.readthedocs.io/en/dev/source/install/index.html#cmake-with-make-for-linux-macos


Then to install the relevent branch:

```
git clone https://github.com/OpenFAST/OpenFAST.git
cd OpenFAST
git checkout tags/v3.4.1
git switch -c v3.4.1
mkdir build
cd build 
```

Now run the following set of commands:

```
module purge
module load craype-x86-spr
module load intel-oneapi-mkl/2023.2.0-intel
module load intel-oneapi-mpi/2021.10.0-intel
module load intel-oneapi-compilers/2023.2.0

export OMP_PROC_BIND=spread
export KMP_AFFINITY=balanced

cmake .. -DBUILD_SHARED_LIBS=ON -DDOUBLE_PRECISION:BOOL=OFF -DCMAKE_INSTALL_PREFIX:PATH=./install

make -j 36
make install
```



## Install ROSCO

With the same shell which has the above mentioned modules already loaded

(Now following the instructions in the full ROSCO installation)
https://rosco.readthedocs.io/en/latest/source/install.html#full-rosco-installation

Starting from the ''herc_root'' folder:

```
git clone https://github.com/NREL/ROSCO.git
cd ROSCO
git checkout develop

cd ROSCO #Note entering 2nd level ROSCO
mkdir build
cd build
cmake ..
make
```

## Install AMR-Wind

TODO: This is not yet succesfull

```
git clone git@github.com:Exawind/amr-wind.git
cd amr-wind
git checkout d917dca2

git submodule update --init --recursive

git switch -c hercules-build
```

Next you are going to paste the following code into a file ''build_script'' in the top-level folder of amr_wind.  

**It is important that before running the script you edit the locaiton of openfast to match your location**

```
#!/bin/bash -l

rm -rf build
mkdir build
cd build

module purge
module load craype-x86-spr
module load intel-oneapi-mpi/2021.10.0-intel
module load intel-oneapi-compilers/2023.2.0
module load netcdf-c/4.9.2-intel-oneapi-mpi-intel
module load git/2.40.0
module use /nopt/nrel/apps/modules/test/application
module load helics/3.4.0-cray-mpich-intel


module load cmake

cmake -DAMR_WIND_ENABLE_CUDA:BOOL=OFF \
      -DAMR_WIND_ENABLE_MPI:BOOL=ON \
      -DAMR_WIND_ENABLE_OPENMP:BOOL=OFF \
      -DAMR_WIND_TEST_WITH_FCOMPARE:BOOL=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DAMR_WIND_ENABLE_NETCDF:BOOL=ON \
      -DNETCDF_DIR:PATH=/nopt/nrel/ecom/hpacf/software/2020-07/spack/opt/spack/linux-centos7-skylake_avx512/gcc-8.4.0/netcdf-c-4.7.3-533s5vfhvbbvpgxambbzk66vtlcce2u6  \
      -DnetCDF_DIR:PATH=/nopt/nrel/ecom/hpacf/software/2020-07/spack/opt/spack/linux-centos7-skylake_avx512/gcc-8.4.0/netcdf-c-4.7.3-533s5vfhvbbvpgxambbzk66vtlcce2u6  \
      -DAMR_WIND_ENABLE_OPENFAST:BOOL=ON \
      -DOpenFAST_ROOT:PATH=/home/pfleming/herc_root/OpenFAST/build/install/ \
      -DAMR_WIND_ENABLE_HYPRE:BOOL=OFF \
      -DAMR_WIND_ENABLE_MASA:BOOL=OFF \
      -DAMR_WIND_ENABLE_HELICS:BOOL=ON \
      -DAMR_WIND_ENABLE_TESTS:BOOL=ON \
      -DAMR_WIND_ENABLE_FORTRAN:BOOL=OFF \
      -DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON \
      -DAMR_WIND_ENABLE_ALL_WARNINGS:BOOL=ON \
      -DBUILD_SHARED_LIBS:BOOL=ON \
      ..

nice make -j32
```

Run via:

```
bash build_script
```

## Set up a hercules conda environment

This will be needed for the remaining installations

```
module load anaconda3
conda create --name hercules python=3.11
conda activate hercules
```

Edit your ~/.bashrc file to include a helpful shortcut function based on this:

```
env_hercules()
{
        module purge
        module load craype-x86-spr
        module load intel-oneapi-mpi/2021.10.0-intel
        module load intel-oneapi-compilers/2023.2.0
        module load netcdf-c/4.9.2-intel-oneapi-mpi-intel
        module load git/2.40.0
        # module use /nopt/nrel/apps/modules/test/application
        # module load helics/3.4.0-cray-mpich-intel
        module load anaconda3

        conda activate hercules
}
```
-->

