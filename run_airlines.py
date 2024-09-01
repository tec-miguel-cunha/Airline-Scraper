import argparse
from datetime import datetime
import os
import subprocess
import time
import pandas as pd
import Ryanair
import TAP
import SwissAir
import Iberia
import EasyJet
import AirEuropa
import KLM
import inputs
import boto3


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Get information from airline websites')

    parser.add_argument('--airlines-file', type=str, required=False, default='airlines.csv', help='CSV file with names of Airlines to check')

    args = parser.parse_args()

    start_time = time.time()

    airlines_file_name = args.airlines_file

    log_filenames = []

    with open(airlines_file_name, 'r') as f:

        airlines = f.readlines()
        airlines = [x.strip() for x in airlines]
        
        for airline in airlines:
            if airline in ['Ryanair', 'TAP', 'SwissAir', 'Iberia', 'EasyJet', 'AirEuropa', 'KLM']:

                airline_start_time = time.time()

                if not os.path.isdir(airline):
                    if inputs.input_print_ > 0:
                        print(f'Creating directory for {airline}')
                    os.mkdir(airline)

                if not os.path.isdir(airline + '/' + 'logs'):
                    if inputs.input_print_ > 0:
                        print(f'Creating logs directory for {airline}')
                    os.mkdir(airline + '/' + 'logs')

                if not os.path.isdir(airline + '/' + 'outputs'):
                    if inputs.input_print_ > 0:
                        print(f'Creating outputs directory for {airline}')
                    os.mkdir(airline + '/' + 'outputs')
                
                filename = airline + '_' + 'routes' + '.csv'
                
                df = pd.read_csv(filename)
                if inputs.input_print_ > 0:
                    print(f'Number of routes found for {airline}: {len(df)}')
                for index, row in df.iterrows():
                    origin_code = row['origin_code']
                    origin_name = row['origin_name']
                    destination_code = row['destination_code']
                    destination_name = row['destination_name']
                    date = row['date']
                    row_index = index
                    
                    environment = '.venv/bin/python'
                    script = airline + '.py'
                    log_filename = airline + '/' + 'logs' + '/' + time.strftime('%Y-%m-%d__%H:%M:%S') + '.log'

                    log_filenames.append(log_filename)

                    if inputs.input_print_ > 0:
                        print(f'Running main function for {airline} for index: {row_index}')

                    with open(log_filename, 'w') as log_file:
                        subprocess.run([environment, script, '--origin', origin_code, '--origin-name', origin_name, '--destination', destination_code, '--destination-name', destination_name, '--date', date], 
                                    stdout=log_file, 
                                    stderr=subprocess.STDOUT)
                    
                    if inputs.input_print_ > 0:
                        print(f'{airline} route from {origin_name} to {destination_name} on {date} was run')
                
                airline_end_time = time.time()
                airline_time = airline_end_time - airline_start_time
                if inputs.input_print_ > 0:
                    print(f'Time taken for {airline}: {str(datetime.timedelta(seconds=airline_time))}')
        
            else:
                if inputs.input_print_ > 0:
                    print(f'Airline {airline} not found')
                continue

        end_time = time.time()
        total_time = end_time - start_time
        if inputs.input_print_ > 0:
            print(f'Total time taken: {str(datetime.timedelta(seconds=total_time))}')


    # Send log files to S3.
    # Delete all the logs after sending them to S3.
    for log_file in log_filenames:
        if inputs.input_print_ > 0:
            print(f'Sending log file {log_file} to S3')
        s3_client = boto3.client('s3')
        
        os.remove(log_file)


    # Send output files to S3. 
    #   The files will be in the outputs directory of each airline. 
    #   Only bring the ones that are dated from yesterday. 
    #   Delete the ones from 2 days ago.
    #   Send the ones from yesterday to S3.
    #   Keep todays files in the outputs directory.
    

    
    
    