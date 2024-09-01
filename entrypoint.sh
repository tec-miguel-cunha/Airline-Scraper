#!/bin/sh

if [ "$1" = "Ryanair" ]; then
    shift
    python Ryanair.py "$@"
elif [ "$1" = "EasyJet" ]; then
    shift
    python EasyJet.py "$@"
elif [ "$1" = "AirEuropa" ]; then
    shift
    python AirEuropa.py "$@"
elif [ "$1" = "TAP" ]; then
    shift
    python TAP.py "$@"
elif [ "$1" = "Iberia" ]; then
    shift
    python Iberia.py "$@"
elif [ "$1" = "KLM" ]; then
    shift
    python KLM.py "$@"
elif [ "$1" = "SwissAir" ]; then
    shift
    python SwissAir.py "$@"
elif [ "$1" = "run_airlines" ]; then
    shift
    python run_airlines.py "$@"
else
    echo "Unknown script: $1"
    exit 1
fi