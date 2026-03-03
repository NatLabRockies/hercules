# Installation instructions


# Installation

## Root Directory

It is recommended to install Hercules into a root directory.  This root directory can also contain other projects that are often used with Hercules such as Hycon.

```bash
mkdir -p hercules_root
cd hercules_root
```

## Clone Hercules

```bash
git clone https://github.com/NatLabRockies/hercules
cd hercules
```

## Virtual environment

It is recommended that you install Hercules into a virtual environment.

### Conda

To create a new conda environment for hercules:
```bash
conda create --name hercules python=3.13
conda activate hercules
```

### UV

Alternatively, you can use uv to create a new environment for hercules.  This will create a new environment in the current directory.

```bash
uv venv --python 3.13
source .venv/bin/activate
```

See https://docs.astral.sh/uv/getting-started/installation/ for information in installing uv.

Note, `uvx` is used for in running the gridstatus_download.py script.  So you will need to install if using the gridstatus_download.py script.
See (Grid Status Data Download)[gridstatus_download.md] for more information.

## PIP Install

Install Hercules in editible mode into the active virtual environment.

### Just Hercules
```bash
pip install -e .
```

### With developer and documentation Dependencies

```bash
pip install -e .[develop,docs]
```

## Setting branch

Users can simply remain on the `main` branch. Developers should switch to the `develop` branch to get the latest code changes. To change to the `develop` branch, use

```bash
git fetch --all
git switch develop
```

## Hycon

NLR's Hycon software is used to implement controllers in the Hercules platform. This package is not essential to run Hercules by itself, but is needed to implement any controls in the platform.


To install:

```bash
cd .. # To hercules_root
git clone git@github.com:NREL/hycon.git
cd hycon
git fetch --all
pip install -e .
```
