module purge
module use /nopt/nrel/apps/modules/default/modulefiles
module load helics/helics-3.1.0_openmpi
module load cmake
module load netcdf-c/4.7.3/gcc-mpi

cmake -DAMR_WIND_ENABLE_CUDA:BOOL=OFF \
      -DCMAKE_INSTALL_PREFIX:PATH=./install \
      -DAMR_WIND_ENABLE_MPI:BOOL=ON \
      -DAMR_WIND_ENABLE_OPENMP:BOOL=OFF \
      -DAMR_WIND_TEST_WITH_FCOMPARE:BOOL=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DAMR_WIND_ENABLE_NETCDF:BOOL=ON \
      -DAMR_WIND_ENABLE_OPENFAST:BOOL=OFF \
      -DAMR_WIND_ENABLE_HYPRE:BOOL=OFF \
      -DAMR_WIND_ENABLE_MASA:BOOL=OFF \
      -DAMR_WIND_ENABLE_TESTS:BOOL=OFF \
      -DAMR_WIND_ENABLE_FORTRAN:BOOL=OFF \
      -DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON \
      -DAMR_WIND_ENABLE_ALL_WARNINGS:BOOL=ON \
      -DBUILD_SHARED_LIBS:BOOL=ON \
      -DAMR_WIND_ENABLE_HELICS:BOOL=ON \
      -DHELICS_INSTALL_DIR:PATH="/nopt/nrel/apps/helics/v3.1.0_openmpi/"\
      -DHELICS_DIR:PATH="/nopt/nrel/apps/helics/v3.1.0_openmpi/" .. 

nice make -j16
