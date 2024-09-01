import argparse
import datetime
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

    start_time = datetime.datetime.now()

    airlines_file_name = args.airlines_file

    log_filenames = []
    outputs_filenames_to_upload = []
    outputs_filenames_to_delete = []

    with open(airlines_file_name, 'r') as f:

        airlines = f.readlines()
        airlines = [x.strip() for x in airlines]
        
        for airline in airlines:
            if airline in ['Ryanair', 'TAP', 'SwissAir', 'Iberia', 'EasyJet', 'AirEuropa', 'KLM']:

                airline_start_time = datetime.datetime.now()

                now = datetime.datetime.now()
                yesterday = now - datetime.timedelta(days=1)
                two_days_ago = now - datetime.timedelta(days=2)

                yesterday_file_name = airline + '/' + 'outputs' + '/' + airline + '_' + yesterday.strftime('%d-%m-%Y') + '.csv'
                outputs_filenames_to_upload.append(yesterday_file_name)
                yesterday_file_name_economy = airline + '/' + 'outputs' + '/' + airline + '_' + yesterday.strftime('%d-%m-%Y') + '_' + 'Economy' + '.csv'
                outputs_filenames_to_upload.append(yesterday_file_name_economy)
                yesterday_file_name_business = airline + '/' + 'outputs' + '/' + airline + '_' + yesterday.strftime('%d-%m-%Y') + '_' + 'Business' + '.csv'
                outputs_filenames_to_upload.append(yesterday_file_name_business)

                two_days_ago_file_name = airline + '/' + 'outputs' + '/' + airline + '_' + two_days_ago.strftime('%d-%m-%Y') + '.csv'
                outputs_filenames_to_delete.append(two_days_ago_file_name)
                two_days_ago_file_name_economy = airline + '/' + 'outputs' + '/' + airline + '_' + two_days_ago.strftime('%d-%m-%Y') + '_' + 'Economy' + '.csv'
                outputs_filenames_to_delete.append(two_days_ago_file_name_economy)
                two_days_ago_file_name_business = airline + '/' + 'outputs' + '/' + airline + '_' + two_days_ago.strftime('%d-%m-%Y') + '_' + 'Business' + '.csv'
                outputs_filenames_to_delete.append(two_days_ago_file_name_business)

                if not os.path.isdir(airline):
                    if inputs.input_print_ > -1:
                        print(f'Creating directory for {airline}')
                    os.mkdir(airline)

                if not os.path.isdir(airline + '/' + 'logs'):
                    if inputs.input_print_ > -1:
                        print(f'Creating logs directory for {airline}')
                    os.mkdir(airline + '/' + 'logs')

                if not os.path.isdir(airline + '/' + 'outputs'):
                    if inputs.input_print_ > -1:
                        print(f'Creating outputs directory for {airline}')
                    os.mkdir(airline + '/' + 'outputs')
                
                filename = airline + '_' + 'routes' + '.csv'
                
                df = pd.read_csv(filename)
                if inputs.input_print_ > -1:
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

                    try:
                        if inputs.input_print_ > -1:
                            print(f'Running main function for {airline} for index: {row_index}')
                        run_time_start = datetime.datetime.now()
                        with open(log_filename, 'w') as log_file:
                            subprocess.run([environment, script, '--origin', origin_code, '--origin-name', origin_name, '--destination', destination_code, '--destination-name', destination_name, '--date', date], 
                                        stdout=log_file, 
                                        stderr=subprocess.STDOUT)
                        run_time_end = datetime.datetime.now()
                        run_time = run_time_end - run_time_start
                        if inputs.input_print_ > -1:
                            print(f'{airline} route from {origin_name} to {destination_name} on {date} was run: in {run_time}')
                    except Exception as e:
                        run_time_end = datetime.datetime.now()
                        run_time = run_time_end - run_time_start
                        if inputs.input_print_ > -1:
                            print(f'Error running main function for {airline} for index {row_index} during {run_time}: {str(e)}')
                        continue
                
                airline_end_time = datetime.datetime.now()
                airline_time = airline_end_time - airline_start_time
                if inputs.input_print_ > -1:
                    print(f'Time taken for {airline}: {str(airline_time)}')
        
            else:
                if inputs.input_print_ > -1:
                    print(f'Airline {airline} not found')
                continue

        end_time = datetime.datetime.now()
        total_time = end_time - start_time
        if inputs.input_print_ > -1:
            print(f'Total time taken: {str(total_time)}')


        # # Send log files to S3.
        # # Delete all the logs after sending them to S3.
        # for log_file in log_filenames:
        #     if inputs.input_print_ > -1:
        #         print(f'Sending log file {log_file} to S3')
        #     s3_client = boto3.client('s3')

        #     # if file exists, send it to S3
        #     if os.path.isfile(log_file):
        #         try:
        #             s3_client.upload_file(log_file, 'airline_scrapper_files', os.path.basename(log_file))
        #             if inputs.input_print_ > -1:
        #                 print(f'Log file {log_file} sent to S3')
                    
        #             os.remove(log_file)
        #             if inputs.input_print_ > -1:
        #                 print(f'Log file {log_file} deleted')
        #         except Exception as e:
        #             if inputs.input_print_ > -1:
        #                 print(f'Error sending log file {log_file} to S3: {str(e)}')
        #             continue
        #     else:
        #         if inputs.input_print_ > -1:
        #             print(f'Log file {log_file} does not exist')
        #         continue


        # # Send output files to S3. 
        # #   The files will be in the outputs directory of each airline. 
        # #   Only bring the ones that are dated from yesterday. 
        # #   Delete the ones from 2 days ago.
        # #   Send the ones from yesterday to S3.
        # #   Keep todays files in the outputs directory.
        # for upload_filename in outputs_filenames_to_upload:
        #     if inputs.input_print_ > -1:
        #         print(f'Sending output file {upload_filename} to S3')
        #     s3_client = boto3.client('s3')

        #     # if file exists, send it to S3
        #     if os.path.isfile(upload_filename):
        #         try:
        #             s3_client.upload_file(upload_filename, 'airline_scrapper_files', os.path.basename(upload_filename))
        #             if inputs.input_print_ > -1:
        #                 print(f'Output file {upload_filename} sent to S3')
        #         except Exception as e:
        #             if inputs.input_print_ > -1:
        #                 print(f'Error sending output file {upload_filename} to S3: {str(e)}')
        #             continue
        #     else:
        #         if inputs.input_print_ > -1:
        #             print(f'Output file {upload_filename} does not exist')
        #         continue
        
        # for delete_filename in outputs_filenames_to_delete:
        #     if inputs.input_print_ > -1:
        #         print(f'Deleting output file {delete_filename}')
        #     if os.path.isfile(delete_filename):
        #         try:
        #             os.remove(delete_filename)
        #             if inputs.input_print_ > -1:
        #                 print(f'Output file {delete_filename} deleted')
        #         except Exception as e:
        #             if inputs.input_print_ > -1:
        #                 print(f'Error deleting output file {delete_filename}: {str(e)}')
        #             continue
        #     else:
        #         if inputs.input_print_ > -1:
        #             print(f'Output file {delete_filename} does not exist')
        #         continue




    



        



    

    
    
    