# Spack installation of AMR Wind code
This document outlines the process for installing the high-fidelity wind portion of Hercules onto NREL's Kestrel HPC system using spack package manager. For more information on Spack, see (https://spack.io/)

## Initial steps
1. Log into Kestrel
2. Go to the directory where you want to install spack, for example `/home/{user-name}/repos`

## Installing spack
First, you will need to install spack package manager. This can be achieved by running the following lines:

```
git clone --recursive https://github.com/sandialabs/spack-manager.git
cd spack-manager
```

Next, you need to pull the version of spack set up with the helics module:

```
git fetch origin
git checkout exawind
git pull --recurse-submodules
```

### Adding spack to bash_profile
Although not strictly necessary, it can be handy to add spack manager to your bash_profile for a quick start every time you open a terminal on Kestrel. To do this, run:

```
vim ~/.bash_profile
```

In the VIM editor, do the following:
1. Start inserting text by pressing `i`.
2. Add the following line: `export SPACK_MANAGER=<absolute path to spack-manager>`, e.g. `export SPACK_MANAGER=/home/{user-name}/repos/spack-manager`.
3. Press ESC to stop inserting text
4. Press `:wq` to save and quit.

## Starting spack
The steps described next are to start spack manager. These steps are necessary _every time_ you reopen a terminal on Kestrel and want to run Hercules, as well as for the installation of Hercules. Note that you can also include these in your bash_script if you want spack to automatically start when you open a terminal.

```
source ~/.bash_profile
source $SPACK_MANAGER/start.sh
spack-start
```

## Creating a Hercules environment
The last step to installing Hercules and all its dependencies is creating a Hercules spack environment by following these steps.

```
cd <path to directory where you want to install hercules>
mkdir environment_hercules
cd environment_hercules
bash
quick-create-dev -d . -s "amr-wind@main+helics+openfast helics@3.3.2+mpi openfast@3.4.0+rosco"
```

Note that this last line will take a little while, as spack will clone all repositories necessary for Hercules. Finally, you can install all repos (but be sure you are not in a rush, because this will take some time!) by running:

```
spack install
```

