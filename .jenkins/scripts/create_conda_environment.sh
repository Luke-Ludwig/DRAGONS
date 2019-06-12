#!/usr/bin/env bash
#
# Uses `conda  info --envs` to list the existing virtual environments and
# checks if the `$CONDA_ENV_NAME` string is inside the output. If so, it means
# that the `$CONDA_ENV_NAME` virtual environment exists and its creating step
# can be skipped
#

if conda info --envs | grep -q $CONDA_ENV_NAME; then
    echo " Skipping cretiong of existing conda environment: ${CONDA_ENV_NAME}";

else
    conda env create --quiet --file .jenkins/conda_test_environment.yml \
        -n "${CONDA_ENV_NAME}";

fi


