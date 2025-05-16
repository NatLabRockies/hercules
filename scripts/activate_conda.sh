#!/bin/bash

echo "Activating Hercules Conda environment..."

# Determine the base path for Conda initialization
if [ -f "/home/$USER/anaconda3/etc/profile.d/conda.sh" ]; then
    # Common path for Anaconda on Linux
    CONDA_PATH="/home/$USER/anaconda3/etc/profile.d/conda.sh"
elif [ -f "/Users/$USER/anaconda3/etc/profile.d/conda.sh" ]; then
    # Common path for Anaconda on macOS
    # CONDA_PATH="/Users/$USER/anaconda3/etc/profile.d/conda.sh"
    CONDA_PATH="/Users/$USER/miniforge3/etc/profile.d/conda.sh"
elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
    # Alternative system-wide installation path
    CONDA_PATH="/opt/anaconda3/etc/profile.d/conda.sh"
elif [ -f "opt/miniconda3/etc/profile.d/conda.sh" ]; then
    # Alternative system-wide installation path
    CONDA_PATH="/opt/miniconda3/etc/profile.d/conda.sh"
elif command -v conda &> /dev/null; then
    # If conda is in PATH, use the which command to find conda location
    CONDA_PATH=$(dirname "$(which conda)")/../etc/profile.d/conda.sh
else
    echo "Conda installation not found. Please ensure Conda is installed and in your PATH."
    exit 1
fi
echo "$CONDA_PATH"

# Source the Conda initialization script
source "$CONDA_PATH"
conda activate hercules-pysam6-whoc