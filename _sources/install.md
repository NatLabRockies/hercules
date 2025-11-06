# Installation instructions


# Installation

## Root Directory

It is recommended to install Hercules into a root directory.  This root directory can also contain other projects that are often used with Hercules such as the Wind Hybrid Open Controller (WHOC) and the Electrolyzer.

```bash
mkdir -p hercules_root
cd hercules_root
```

## Clone Hercules

```bash
git clone https://github.com/NREL/hercules
cd hercules
```

## Virtual environment

It is recommended that you install Hercules into a virtual environment.

### CONDA

To create a new conda environment for hercules:
```bash
conda create --name hercules python=3.11
conda activate hercules
```

### UV

Alternatively, you can use uv to create a new environment for hercules.  This will create a new environment in the current directory.

```bash
uv venv
source .venv/bin/activate
```

See https://docs.astral.sh/uv/getting-started/installation/ for information in installing uv.

Note, `uvx` is used for in running the gridstatus_download.py script.  So you will need to install if using the gridstatus_download.py script.
See (Grid Status Data Download)[gridstatus_download.md] for more information.

## PIP Install

Install Hercules in editible mode into the active virtual environment.

#### Just Hercules
```bash
pip install -e .
```

#### With Developer and Documentation Dependencies

```bash
pip install -e .[develop,docs]
```

## Setting branch

Can optionally switch to the v2 branch for the latest stable version.

```bash
git fetch --all
git switch v2
```

## Wind Hybrid Open Controller (WHOC)

NREL's Wind Hybrid Open Controller (WHOC) software is used to implement controllers in the Hercules platform. This package is not essential to run Hercules by itself, but is needed to implement any controls in the platform.


To install:
Go back to root

```bash
cd ..
git clone git@github.com:NREL/wind-hybrid-open-controller.git
cd wind-hybrid-open-controller
git fetch --all
pip install -e .
```

## Electrolyzer

A python electrolyzer model is also required for hercules. To install
the electrolyzer, use

```bash
cd ..
git clone git@github.com:NREL/electrolyzer.git
cd electrolyzer
git fetch --all
git switch main
```
