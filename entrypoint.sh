#!/bin/sh

if [ "$1" = "Ryanair" ]; then
    shift
    python /app/Ryanair.py "$@"
elif [ "$1" = "EasyJet" ]; then
    shift
    python /app/EasyJet.py "$@"
elif [ "$1" = "AirEuropa" ]; then
    shift
    python /app/AirEuropa.py "$@"
elif [ "$1" = "TAP" ]; then
    shift
    python /app/TAP.py "$@"
elif [ "$1" = "Iberia" ]; then
    shift
    python /app/Iberia.py "$@"
elif [ "$1" = "KLM" ]; then
    shift
    python /app/KLM.py "$@"
elif [ "$1" = "SwissAir" ]; then
    shift
    python /app/SwissAir.py "$@"
elif [ "$1" = "run_airlines" ]; then
    shift
    python /app/run_airlines.py "$@"
else
    echo "Unknown script: $1"
    exit 1
fi