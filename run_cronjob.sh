#!/bin/bash

# Move to the desired directory
cd /mnt/c/Users/mmcun/Desktop/Maastricht/Thesis/Thesis\ 2.0/Airline-Scraper

# Activate the virtual environment
source .venv/bin/activate

# Activate the virtual environment and run the Python script
.venv/bin/python run_airlines.py > /mnt/c/Users/mmcun/Desktop/Maastricht/Thesis/Thesis\ 2.0/Airline-Scraper/run_airlines_logs/$(date +\%Y\%m\%d\%H\%M\%S).log 2>&1

# Deactivate the virtual environment
deactivate