# import libraries
import argparse
import os
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import threading
import urllib3
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import chromedriver_autoinstaller
import json
import inputs
import re
from datetime import datetime
import csv

# arg 1 before arg 2
compare_positions = """
var Element1 = arguments[0];
var Element2 = arguments[1];
var position = Element1.compareDocumentPosition(Element2);
if (position & Node.DOCUMENT_POSITION_FOLLOWING) {
    return true;
} else if (position & Node.DOCUMENT_POSITION_PRECEDING) {
    return false;
} else {
    return false;
}
"""

current_origin_name = ''
current_origin_code = ''
current_destination_name = ''
current_destination_code = ''
current_date = ''

def flatten_dict(d, parent_key='', sep='_'):
    if inputs.aireuropa_print_ > 1:
        print('Flattening dictionary')
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            if len(v) == 1 and isinstance(v[0], dict):
                # Flatten the single dictionary element in the list
                items.extend(flatten_dict(v[0], new_key, sep=sep).items())
            else:
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                    else:
                        items.append((f"{new_key}_{i}", item))
        else:
            items.append((new_key, v))
    if inputs.aireuropa_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def flatten_dict_with_na(d, parent_key='', sep='_'):
    if inputs.aireuropa_print_ > 1:
        print('Flattening dictionary')
    items = []
    for k, v in d.items():
        if k in {'current_time', 'airliner', 'flight_id', 'observation_id', 'departure_city_name', 'departure_city_code','arrival_city_name', 'arrival_city_code'}:
            items.append((k, v))
            continue
        if k == 'details':
            flattened_details = flatten_dict(v)
            items.append((k, flattened_details))
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            if len(v) == 1 and isinstance(v[0], dict):
                # Flatten the single dictionary element in the list
                items.extend(flatten_dict(v[0], new_key, sep=sep).items())
            else:
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                    else:
                        items.append((f"{new_key}_{i}", 'N/A'))
        else:
            items.append((new_key, 'N/A'))
    if inputs.aireuropa_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def write_to_csv_row(writer, data, first=False, sold_out=False):
    if inputs.aireuropa_print_ > 1:
        print('Writing to CSV row')
    # Flatten the details and seats data
    if sold_out:
        flattened_data = flatten_dict_with_na(data)
        flattened_data = flatten_dict(flattened_data)
    else:
        flattened_data = flatten_dict(data)
    if first:
        if inputs.aireuropa_print_ > 1:
            print('Writing header row')
        # Write the header row
        header = list(flattened_data.keys())
        writer.writerow(header)
    
    row = list(flattened_data.values())
    # Write the row to the CSV file
    writer.writerow(row)
    if inputs.aireuropa_print_ > 1:
        print('Wrote flattened data')

def check_and_close_popup(driver):
    if inputs.aireuropa_print_ > 1:
        print('Checking and closing popup')
    try:
        # Check for overlay element
        overlay = WebDriverWait(driver, timeout=inputs.aireuropa_timeout_cookies).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='rtm-overlay']")))
        if overlay:
            # Find and click the close button
            close_button = overlay.find_element(By.CSS_SELECTOR, "[class*='close-sc closeStyle1-sc']")
            if close_button:
                close_button.click()
                if inputs.aireuropa_print_ > 1:
                    print('Overlay closed')
        else:
            if inputs.aireuropa_print_ > 1:
                print('No overlay found')
    except Exception as e:
        if inputs.aireuropa_print_ > 0:
            print(f'Exception occurred: {e}')

def is_element_in_view(driver, element):
    if inputs.aireuropa_print_ > 1:
        print('Checking if element is in view')
    # Check if the element is displayed
    if element.is_displayed():
        if inputs.aireuropa_print_ > 1:
            print('Element is displayed')
        return True
    else:
        # Scroll the element into view
        if inputs.aireuropa_print_ > 1:
            print('Trying to scroll element into view')
        driver.execute_script("arguments[0].scrollIntoView();", element)
        if inputs.aireuropa_print_ > 1:
            print('Scrolled element into view')
        # Check again if the element is displayed after scrolling
        return element.is_displayed()

def check_element_exists_by_ID(driver, id, timeout=inputs.aireuropa_timeout_checks):
    element_exists = False
    if inputs.aireuropa_print_ > 1:
        print(f'Checking if element exists by ID: {id}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.ID, id)))
        if inputs.aireuropa_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.aireuropa_print_ > 0:
            print(f'No element by ID: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_CSS_SELECTOR(driver, css, timeout=inputs.aireuropa_timeout_checks):
    element_exists = False
    if inputs.aireuropa_print_ > 1:
        print(f'Checking if element exists by CSS: {css}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if inputs.aireuropa_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.aireuropa_print_ > 0:
            print(f'No element by CSS Selector: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_TAG_NAME(driver, tag, timeout=inputs.aireuropa_timeout_checks):
    element_exists = False
    if inputs.aireuropa_print_ > 1:
        print(f'Checking if element exists by Tag Name: {tag}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.TAG_NAME, tag)))
        if inputs.aireuropa_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.aireuropa_print_ > 0:
            print(f'No element by Tag Name: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_XPATH(driver, xpath, timeout=inputs.aireuropa_timeout_checks):
    element_exists = False
    if inputs.aireuropa_print_ > 1:
        print(f'Checking if element exists by XPATH: {xpath}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
        if inputs.aireuropa_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.aireuropa_print_ > 0:
            print(f'No element by XPATH: {e}')
        element_exists = False
    return element_exists


def check_and_wait_for_URL(driver, url, timeout=inputs.aireuropa_timeout):
    if inputs.aireuropa_print_ > 1:
        print(f'Checking and waiting for URL: {url}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.url_to_be(url))
        if inputs.aireuropa_print_ > 1:
            print("Passed WebDriverWait")
        return True
    except Exception as e:
        if inputs.aireuropa_print_ > 0:
            print(f'URL not found: {e}')
        return False

def wait_for_loading_to_close(driver, field):
    if inputs.aireuropa_print_ > 1:
        print('Waiting for loading to close')
    try:
        if check_element_exists_by_CSS_SELECTOR(driver, field, timeout=inputs.aireuropa_timeout_micro):
            if inputs.aireuropa_print_ > 1:
                print('Found loading')
            WebDriverWait(driver, timeout=inputs.aireuropa_timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, field)))
            if inputs.aireuropa_print_ > 1:
                print('Loading closed')
    except Exception as e:
        if inputs.aireuropa_print_ > 0:
            print(f'Loading not closed: {e}')

class AirEuropa:

    def __init__(self, headless=False):

        self.timeout = inputs.aireuropa_timeout
        self.timeout_cookies = inputs.aireuropa_timeout_checks
        self.timeout_little = inputs.aireuropa_timeout_little
        self.timeout_implicitly_wait = inputs.aireuropa_timeout_implicitly_wait
        self.cookies = inputs.aireuropa_cookies
        self.print_ = inputs.aireuropa_print_
        self.closed_popup_cabin_bags = False
        self.new_tab_opened = False
        self.closed_fares_overlay = 0
        self.retries = inputs.aireuropa_retries

        self.buttons = []

        if self.print_ > 1:
            print('Initializing AirEuropa')
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # No GUI will be opened
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("window-size=1280x752")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.86 Safari/537.36")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-dev-shm-usage")
            self.driver = uc.Chrome(options=chrome_options)
        else:
            self.driver = uc.Chrome()
        if self.print_ > 1:
            print('Initialized AirEuropa')

    def click_with_retry(self, element, retries=3, delay=1):
        if self.print_ > 1:
            print('Clicking with retry')
        for attempt in range(retries):
            try:
                # Check if the element is clickable
                WebDriverWait(self.driver, timeout=self.timeout_little).until(EC.element_to_be_clickable(element))
                self.driver.execute_script("arguments[0].click();", element)
                if self.print_ > 1:
                    print(f'Successfully clicked on element: {element}')
                return True
            except Exception as e:
                if self.print_ > 0:
                    print(f'Attempt {attempt + 1} to click element {element} failed: {e}')
                time.sleep(delay)
        if self.print_ > 0:
            print(f'Failed to click element {element} after {retries} retries')
        return False

    def click_buttons_in_reverse_order(self):
        if self.print_ > 1:
            print('Clicking buttons in reverse order')
        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        n = len(self.buttons)
        for i in range(n):
            for attempt in range(3):
                if self.print_ > 2:
                    print(f'Attempt {attempt + 1} to click buttons from index {n-i-1} to {n-1}')
                success = True
                for j in range(n-i-1, n):
                    if not self.click_with_retry(self.buttons[j]):
                        if self.print_ > 1:
                            print(f'Failed to click button at index {j}')
                        success = False
                        break
                if success:
                    if self.print_ > 1:
                        print(f'Successfully clicked buttons from index {n-i-1} to {n-1}')
                    return True
        if self.print_ > 0:
            print('Failed to click all buttons after retries')
        return False

    def fill_home_page_form(self, flyout, origin_name, origin_code, destination_name, destination_code, repeat=False, retries=0):

        if self.print_ > 1:
            print('Entering Fill Form Function')
        # set url
        url = f'https://www.aireuropa.com/pt/en/home'
        # get the page
        self.driver.get(url)
        if self.print_ > 1:    
            print('Opened AirEuropa homepage')
        self.driver.implicitly_wait(self.timeout_implicitly_wait)

        if self.cookies == "not accepted":
            try:
                if self.print_ > 1:
                    print('Accepting cookies')
                if check_element_exists_by_ID(self.driver, 'ensAcceptAll', timeout = self.timeout_cookies):
                    self.driver.find_element(By.CSS_SELECTOR, "[id*='ensAcceptAll']").click()
                    self.cookies = "accepted"
                    if self.print_ > 1:
                        print('Accepted cookies on cookie banner')
                else:
                    if self.print_ > 1:
                        print('No cookies banner found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error accepting cookies: {e}')
                if retries < 3:
                    if self.fill_home_page_form(flyout, origin_name, origin_code, destination_name, destination_code, retries=retries+1) == "Abort":
                        return "Abort"
                else:
                    return "Abort"

        try:
            if self.print_ > 1:
                print('Clicking on apply language')
            if check_element_exists_by_ID(self.driver, 'market-language-popup', timeout = self.timeout_little):
                language_popup = self.driver.find_element(By.ID, 'market-language-popup')
                apply_button = language_popup.find_element(By.TAG_NAME, 'button')
                self.click_with_retry(apply_button)
                if self.print_ > 1:
                    print('Clicked on apply language')
            else:
                if self.print_ > 1:
                    print('No apply language button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on apply language: {e}. Trying to solve the problem')
            if retries < 3:
                if self.fill_home_page_form(flyout, origin_name, origin_code, destination_name, destination_code, retries=retries+1) == "Abort":
                    return "Abort"
            else:
                return "Abort"

        wait_for_loading_to_close(self.driver, "[id='ph-refx-spinner-bottom']")

        try:
            if self.print_ > 1:
                print('Getting the form')
            if check_element_exists_by_TAG_NAME(self.driver, 'form'):
                form = self.driver.find_element(By.TAG_NAME, 'form')
                if self.print_ > 1:
                    print('Got the form')
            else:
                if self.print_ > 1:
                    print('No form found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting the form: {e}. Trying to solve the problem')
            if retries < 3:
                if self.fill_home_page_form(flyout, origin_name, origin_code, destination_name, destination_code, retries=retries+1) == "Abort":
                    return "Abort"
            else:
                return "Abort"

        try:
            if self.print_ > 1:
                print('Clicking on dropdown one way')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='mat-form-field-flex']"):
                self.click_with_retry(form.find_element(By.CSS_SELECTOR, "[class*='mat-form-field-flex']"))
                if self.print_ > 1:
                    print('Clicked to open one-way dropdown')
            else:
                if self.print_ > 1:
                    print('No One Way dropdwon found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on One Way dropdown: {e}. Trying to solve the problem')
            if retries < 3:
                if self.fill_home_page_form(flyout, origin_name, origin_code, destination_name, destination_code, retries=retries+1) == "Abort":
                    return "Abort"
            else:
                return "Abort"


        try:
            if self.print_ > 1:
                print('Selecting one way')
            if check_element_exists_by_ID(self.driver, 'mat-option-1'):
                self.click_with_retry(self.driver.find_element(By.ID, 'mat-option-1'))
                if self.print_ > 1:
                    print('Selected One Way')
            else:
                if self.print_ > 1:
                    print('No One Way option found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting One Way: {e}. Trying to solve the problem')

        try:
            if self.print_ > 1:
                print('Entering origin')
            if check_element_exists_by_ID(self.driver, 'departure'):
                self.driver.find_element(By.ID, 'departure').send_keys(origin_name)
                time.sleep(1)
                self.driver.find_element(By.ID, 'departure').send_keys(Keys.RETURN)
                if self.print_ > 1:
                    print('Entered origin')
            else:
                if self.print_ > 1:
                    print('No origin field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering origin: {e}. Trying to solve the problem')

        time.sleep(2)
            
        try:
            if self.print_ > 1:
                print('Entering destination')
            if check_element_exists_by_ID(self.driver, 'mat-autocomplete-2', timeout = self.timeout):
                time.sleep(3)
                if self.print_ > 1:
                    print('Found overlay for dropdown menu')
                if check_element_exists_by_ID(self.driver, 'arrival', timeout = self.timeout):
                    self.driver.find_element(By.ID, 'arrival').send_keys(destination_name)
                    time.sleep(3)
                    self.driver.find_element(By.ID, 'arrival').send_keys(Keys.RETURN)
                    if self.print_ > 1:
                        print('Entered destination')
                else:
                    if self.print_ > 1:
                        print('No destination field found')
            else:
                if self.print_ > 1:
                    print('No overlay for dropdown menu found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering destination: {e}. Trying to solve the problem')

        try:
            if self.print_ > 1:
                print('Entering departure date')
            parsed_date = datetime.strptime(flyout, '%Y/%m/%d')
            formatted_date = f' {parsed_date.day} {parsed_date.month} {parsed_date.year}'
            aria_label = f"[aria-label='{formatted_date}']"
            if check_element_exists_by_CSS_SELECTOR(self.driver, aria_label):
                self.click_with_retry(form.find_element(By.CSS_SELECTOR, aria_label))
                if self.print_ > 1:
                    print('Entered departure date')
            else:
                if self.print_ > 1:
                    print('No departure date found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering departure date: {e}. Trying to solve the problem')
        
        try:
            if self.print_ > 1:
                print('Clicking on search button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='searcher-button']"):
                button_wrapper = self.driver.find_element(By.CSS_SELECTOR, "[class='searcher-button']")
                if check_element_exists_by_TAG_NAME(button_wrapper, 'button'):
                    button = button_wrapper.find_element(By.TAG_NAME, 'button')
                    self.click_with_retry(button)
                    if self.print_ > 1:
                        print('Clicked on search button')
                else:
                    if self.print_ > 1:
                        print('No search button found')
                    return "Abort"
            else:
                if self.print_ > 1:
                    print('No search button wrapper found')
                return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on search button: {e}. Trying to solve the problem')
            self.driver.refresh()
            time.sleep(1)
            if retries < 3:
                if self.fill_home_page_form(flyout, origin_name, origin_code, destination_name, destination_code, retries=retries+1) == "Abort":
                    return "Abort"
            else:
                return "Abort"
        
        if self.print_ > 1:
            print('Exiting Fill Form Function')
            print('Going to next page')

    def get_flights(self):

        if self.print_ > 1:
            print('Getting Flights')

        page_url = "https://digital.aireuropa.com/booking/availability/0"

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In flight results page')
            else:
                if self.print_ > 1:
                    print('Not in flight results page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.fill_home_page_form(flyout=current_date, origin_code=current_origin_code, origin_name=current_origin_name, destination_code=current_destination_code, destination_name=current_destination_name, repeat=True)
                    if state == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to flight results page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flights: {e}')

        wait_for_loading_to_close(self.driver, "[id='ph-refx-spinner-bottom']")

        try:
            if check_element_exists_by_TAG_NAME(self.driver, 'mat-accordion', timeout=self.timeout):
                if self.print_ > 1:
                    print('Found mat-accordion: div with flights')
                flights_div = self.driver.find_element(By.TAG_NAME, 'mat-accordion')
            else:
                if self.print_ > 1:
                    print('No mat-accordion found')
                self.get_flights()
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flights: {e}')
        
        try:
            if self.print_ > 1:
                print('Getting flight cards')
            if check_element_exists_by_TAG_NAME(flights_div, 'refx-upsell-premium-row-pres'):
                if self.print_ > 1:
                    print('Found flight cards')
                flights = flights_div.find_elements(By.TAG_NAME, 'refx-upsell-premium-row-pres')
            else:
                if self.print_ > 1:
                    print('No flight cards found')
                self.get_flights()
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flight cards: {e}')
        
        
        return flights
    
    def get_flight_details(self, flights, index, repeat=False):

        if self.print_ > 1:
            print('Getting flight details')
        
        if repeat:
            flights = self.get_flights()
            if index < len(flights):
                flight = flights[index]
            else:
                if self.print_ > 0:
                    print('Index out of range. Using the last flight')
                flight = flights[-1]
        else:
            if index < len(flights):
                flight = flights[index]
            else:
                if self.print_ > 0:
                    print('Index out of range. Using the last flight')
                flight = flights[-1]

        departure_flyout_time = 'No time found'
        
        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class='refx-display-1 bound-departure-datetime']"):
                if self.print_ > 1:
                    print('Found flight departure time')
                departure_flyout_time = flight.find_element(By.CSS_SELECTOR, "[class='refx-display-1 bound-departure-datetime']").text
                if self.print_ > 1:
                    print(f'Departure flyout time: {departure_flyout_time}')
            else:
                if self.print_ > 1:
                    print('No departure flyout time found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting departure flyout time: {e}')
            
        arrival_flyout_time = 'No time found'

        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class='refx-display-1 bound-arrival-datetime']"):
                if self.print_ > 1:
                    print('Found flight arrival time')
                arrival_flyout_time = flight.find_element(By.CSS_SELECTOR, "[class='refx-display-1 bound-arrival-datetime']").text
                if self.print_ > 1:
                    print(f'Arrival flyout time: {arrival_flyout_time}')
            else:
                if self.print_ > 1:
                    print('No arrival flyout time found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting arrival flyout time: {e}')

        price = 'No price found'
        
        try:
            if self.print_ > 1:
                print('Getting flight price')
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='price-amount']"):
                if self.print_ > 1:
                    print('Found flight price')
                price = flight.find_element(By.CSS_SELECTOR, "[class*='price-amount']").text.replace('.', ',')
                if self.print_ > 1:
                    print(f'Flight price: {price}')
            else:
                if self.print_ > 1:
                    print('No flight price found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flight price: {e}')

        airliner = 'No airliner found'

        time.sleep(1)

        try:
            if self.print_ > 1:
                print('Getting airliner')
            if check_element_exists_by_TAG_NAME(flight, 'refx-flight-details'):
                if self.print_ > 1:
                    print('Found flight details')
                flight_details = flight.find_element(By.TAG_NAME, 'refx-flight-details')
                if self.print_ > 1:
                    print('Found flight details')
                if check_element_exists_by_CSS_SELECTOR(flight_details, "[class='operating-airline-name']"):
                    if self.print_ > 1:
                        print('Found airliner')
                    airliner = flight_details.find_element(By.CSS_SELECTOR, "[class='operating-airline-name']").text
                    if self.print_ > 1:
                        print(f'Airliner: {airliner}')
                else:
                    if self.print_ > 1:
                        print('No airliner found')
            else:
                if self.print_ > 1:
                    print('No flight details found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting airliner: {e}')                    
        
        details = {
            'departure_time': departure_flyout_time,
            'arrival_time': arrival_flyout_time,
            'price_economy': price
        }

        return airliner, details
    
    def advance_to_your_selection_page(self, flights, index, fare_name, repeat=False):

        if self.print_ > 1:
            print(f'Advancing to form page for index: {index} and fare name: {fare_name}')

        if repeat:
            flights = self.get_flights()
            if index < len(flights):
                flight = flights[index]
            else:
                if self.print_ > 0:
                    print('Index out of range. Using the last flight')
                flight = flights[-1]
        else:
            if index < len(flights):
                flight = flights[index]
            else:
                if self.print_ > 0:
                    print('Index out of range. Using the last flight')
                flight = flights[-1]

        page_url = "https://digital.aireuropa.com/booking/availability/0"

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In flight results page')
            else:
                if self.print_ > 1:
                    print('Not in flight results page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.fill_home_page_form(flyout=current_date, origin_code=current_origin_code, origin_name=current_origin_name, destination_code=current_destination_code, destination_name=current_destination_name, repeat=True)
                    if state == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to flight results page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error advancing to form page: {e}')

        wait_for_loading_to_close(self.driver, "[id='ph-refx-spinner-bottom']")

        try:
            if self.print_ > 1:
                print('Finding flight card button section')
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='flight-card-button-section']"):
                if self.print_ > 1:
                    print('Found flight card button section')
                button_section = flight.find_element(By.CSS_SELECTOR, "[class*='flight-card-button-section']")
                if self.print_ > 1:
                    print('Found button section')
            else:
                if self.print_ > 1:
                    print('No flight card button section found')
                return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding flight button section: {e}')
        
        try:
            if self.print_ > 1:
                print('Finding flight card button')
            if check_element_exists_by_CSS_SELECTOR(button_section, "[class*='flight-card-button']"):
                if self.print_ > 1:
                    print('Found flight card button')
                button = button_section.find_element(By.CSS_SELECTOR, "[class*='flight-card-button']")
                if self.print_ > 1:
                    print('Found button')
                self.click_with_retry(button)
            else:
                if self.print_ > 1:
                    print('No flight card button found')
                self.advance_to_form_page(flight)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding flight button: {e}')
        
        try:
            if self.print_ > 1:
                print('Finding flight fares list')
            if check_element_exists_by_TAG_NAME(flight, 'ul'):
                if self.print_ > 1:
                    print('Found ul')
                ul = flight.find_element(By.TAG_NAME, 'ul')
                if self.print_ > 1:
                    print('Found ul')
            else:
                if self.print_ > 1:
                    print('No ul found')
                self.advance_to_form_page(flight)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding ul: {e}')

        try:
            if self.print_ > 1:
                print('Finding flight fares')
            
            if check_element_exists_by_XPATH(ul, "./*"):
                if self.print_ > 1:
                    print('Found li')
                fares_divs = ul.find_elements(By.XPATH, "./*")
                if self.print_ > 1:
                    print('Found li')
            else:
                if self.print_ > 1:
                    print('No li found')
                self.advance_to_form_page(flight)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding li: {e}')

        fares = []
        
        try:
            if self.print_ > 1:
                print('Getting fares')
            for i in range(len(fares_divs)):
                fare = {'name': 'N/A', 'price': 'N/A'}
                if self.print_ > 1:
                    print('Getting fare')
                if i == 0 and fare_name == 'Economy':
                    if self.print_ > 1:
                        print('Getting economy button')
                    if check_element_exists_by_CSS_SELECTOR(fares_divs[i], "[class*='mat-flat-button']"):
                        if self.print_ > 1:
                            print('Found economy button')
                        button_to_continue = fares_divs[i].find_element(By.CSS_SELECTOR, "[class*='mat-flat-button']")
                        if self.print_ > 1:
                            print('Found economy button')
                    else:
                        if self.print_ > 1:
                            print('No econonmy button found')

                if check_element_exists_by_CSS_SELECTOR(fares_divs[i], "[class*='price-card-title-label']"):
                    if self.print_ > 1:
                        print('Found fare name')
                    name = fares_divs[i].find_element(By.CSS_SELECTOR, "[class*='price-card-title-label']").text
                    fare['name'] = name
                    if self.print_ > 2:
                        print(f'Fare name: {name}')
                    if "Business" in name and fare_name == 'Business':
                        if self.print_ > 1:
                            print('Getting business button')
                        if check_element_exists_by_CSS_SELECTOR(fares_divs[i], "[class*='mat-flat-button']"):
                            if self.print_ > 1:
                                print('Found business button')
                            button_to_continue = fares_divs[i].find_element(By.CSS_SELECTOR, "[class*='mat-flat-button']")
                            if self.print_ > 1:
                                print('Found business button')
                        else:
                            if self.print_ > 1:
                                print('No business button found')
                else:
                    if self.print_ > 1:
                        print('No fare name found')
                if check_element_exists_by_CSS_SELECTOR(fares_divs[i], "[class*='price-amount']"):
                    if self.print_ > 1:
                        print('Found fare price')
                    price = fares_divs[i].find_element(By.CSS_SELECTOR, "[class*='price-amount']").text.replace('.', ',')
                    fare['price'] = price
                    if self.print_ > 2:
                        print(f'Fare price: {price}')
                else:
                    if self.print_ > 1:
                        print('No fare price found')
                if self.print_ > 1:
                    print(f'Fare: {fare}')
                fares.append(fare)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting fares: {e}')
        
        try:
            if self.print_ > 1:
                print('Clicking on fare button')
            if self.click_with_retry(button_to_continue):
                if self.print_ > 1:
                    print('Clicked on fare button')
            else:
                if self.print_ > 1:
                    print('Failed to click on fare button')
                return "Continue"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on fare button: {e}')

        time.sleep(2)

        if self.print_ > 1:
            print('Closing dialog')
        try:
            if check_element_exists_by_TAG_NAME(self.driver, 'custom-refx-fare-comparison-dialog-pres'):
                if self.print_ > 1:
                    print('Found dialog')
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if self.print_ > 1:
                    print('Closed dialog')
                self.closed_fares_overlay += 1
            else:
                if self.print_ > 1:
                    print('No dialog found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing dialog: {e}')

        if self.print_ > 1:
            print('Exiting flights page')
            print('Going to next page')

        return fares

    def advance_to_form_page(self, flights, index, fare_name, repeat=False):

        page_url = "https://digital.aireuropa.com/booking/shopping-cart"

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In shopping cart page')
            else:
                if self.print_ > 1:
                    print('Not in shopping cart page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.advance_to_form_page(flights, index, fare_name, repeat=True)
                    if state == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to shopping cart page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to shopping cart page: {e}')

        wait_for_loading_to_close(self.driver, "[id='ph-refx-spinner-bottom']")

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='shopping-cart-buttons']"):
                if self.print_ > 1:
                    print('Found shopping cart buttons')
                button_div = self.driver.find_element(By.CSS_SELECTOR, "[class='shopping-cart-buttons']")
                if self.print_ > 1:
                    print('Click New Page Button')
                self.click_with_retry(button_div.find_element(By.CSS_SELECTOR, "[class*='next-step-button']"))
                if self.print_ > 1:
                    print('Clicked New Page Button')
            else:
                if self.print_ > 1:
                    print('No shopping cart buttons found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on New Page Button: {e}')
        
        if self.print_ > 1:
            print('Exiting shopping cart page')
            print('Going to next page')

    
    def fill_text_input_fields(self, field, input, tab=False):

        if self.print_ > 1:
            print(f'Filling text input field with {input}')
        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, field):
                if self.print_ > 1:
                    print('Found text input field')
                text_input = self.driver.find_element(By.CSS_SELECTOR, field)
                backspaces = len(text_input.get_attribute('value')) + 1
                text_input.send_keys(backspaces * Keys.BACKSPACE)
                time.sleep(0.5)
                text_input.send_keys(input)
                time.sleep(0.5)
                if tab:
                    text_input.send_keys(Keys.TAB)
                if self.print_ > 1:
                    print('Filled text input field')
            else:
                if self.print_ > 1:
                    print('No text input field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error filling text input field: {e}')

    def fill_passenger_form(self, flights, index, fare_name):

        if self.print_ > 1:
            print('Filling passenger form')

        page_url = "https://digital.aireuropa.com/booking/traveler/0"

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In flight results page')
            else:
                if self.print_ > 1:
                    print('Not in flight results page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.advance_to_your_selection_page(flights, index, fare_name, repeat=True)
                    if state == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to flight results page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to flight results page: {e}')
            return "Abort"
        
        wait_for_loading_to_close(self.driver, "[id='ph-refx-spinner-bottom']")

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='mat-tooltip-trigger']"):
                form_title_field = self.driver.find_element(By.CSS_SELECTOR, "[class*='mat-tooltip-trigger']")
                div_to_click = form_title_field.find_element(By.CSS_SELECTOR, "[class*='mat-form-field-flex']")
                self.click_with_retry(div_to_click)
                if self.print_ > 1:
                    print('Clicked on form title field to open dropdown')
                if check_element_exists_by_ID(self.driver, 'mat-option-283'):
                    self.click_with_retry(self.driver.find_element(By.ID, 'mat-option-283'))
                    if self.print_ > 1:
                        print('Selected Mr title')
                else:
                    if self.print_ > 1:
                        print('No Mr title found')
            else:
                if self.print_ > 1:
                    print('No form title field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error filling form title field: {e}')
            
        try:
            if self.print_ > 1:
                print('Filling text fields')
            self.fill_text_input_fields("[formcontrolname='firstName']", 'Miguel')
            self.fill_text_input_fields("[formcontrolname='lastName']", 'Cunha')
            self.fill_text_input_fields("[id*='-0email']", 'micascunha@hotmail.com')
            self.fill_text_input_fields("[id*='-0confirmedEmail']", 'micascunha@hotmail.com')
            self.fill_text_input_fields("[id*='-0phoneCountryCode']", '+351', tab=True)
            self.driver.switch_to.active_element.send_keys('911111111')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error filling text fields: {e}')
        
        try:
            if self.print_ > 1:
                print('Filling GDPR Field')
            if check_element_exists_by_ID(self.driver, 'gdprConsent-input'):
                gdpr_checkbox = self.driver.find_element(By.ID, 'gdprConsent-input')
                self.click_with_retry(gdpr_checkbox)
                if self.print_ > 1:
                    print('Clicked on GDPR checkbox')
            else:
                if self.print_ > 1:
                    print('No GDPR checkbox found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error filling GDPR checkbox: {e}')

        try: # Click on class contains this "nextBtn mat-flat-button"
            if self.print_ > 1:
                print('Clicking on Next Button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='nextBtn mat-flat-button']"):
                next_button = self.driver.find_element(By.CSS_SELECTOR, "[class*='nextBtn mat-flat-button']")
                self.click_with_retry(next_button)
                if self.print_ > 1:
                    print('Clicked on Next Button')
            else:
                if self.print_ > 1:
                    print('No Next Button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Next Button: {e}')
        
        if self.print_ > 1:
            print('Exiting passenger form')
            print('Going to next page')

    def get_bags_and_info(self, flights, index, fare_name):

        if self.print_ > 1:
            print('Getting bags and info')

        page_url = "https://digital.aireuropa.com/booking/shopping-cart"

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In shopping cart page')
            else:
                if self.print_ > 1:
                    print('Not in shopping cart page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.fill_passenger_form(flights, index, fare_name)
                    if state == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to shopping cart page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to shopping cart page: {e}')
            return "Abort"

        wait_for_loading_to_close(self.driver, "[id='ph-refx-spinner-bottom']")

        time.sleep(5)

        try:
            if self.print_ > 1:
                print('Finding elements of services info')
            if check_element_exists_by_TAG_NAME(self.driver, 'custom-refx-service-catalog-pres'):
                services_div = self.driver.find_element(By.TAG_NAME, 'custom-refx-service-catalog-pres')
                if self.print_ > 1:
                    print('Found services div')
                ul = services_div.find_element(By.TAG_NAME, 'ul')
                if self.print_ > 1:
                    print('Found ul')
                services = ul.find_elements(By.XPATH, "./*")
                if self.print_ > 1:
                    print(f'Found li: {len(services)}')
            else:
                if self.print_ > 1:
                    print('No services div found')
                self.get_bags_and_info()
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding services info: {e}')
        
        services_info = []

        try:
            if fare_name == 'Economy':
                last_index = 1
            else:
                last_index = 1
            if self.print_ > 1:
                print('Iterating over services')
            for i in range(len(services)):
                name = 'N/A'
                price = 'N/A'
                if i > last_index:
                    break
                if check_element_exists_by_TAG_NAME(services[i], 'h3'):
                    if self.print_ > 1:
                        print('Found service title')
                    name = services[i].find_element(By.TAG_NAME, 'h3').text
                    if self.print_ > 2:
                        print(f'Service title: {name}')
                    if i == 0: # A problem might come here due to the name needing to be in the same language as the website
                        seats_button = services[i].find_element(By.CSS_SELECTOR, "[class*='category-add-service']")
                        if self.print_ > 1:
                            print('Found seats button')
                else:
                    if self.print_ > 1:
                        print('No service title found')
                if check_element_exists_by_CSS_SELECTOR(services[i], "[class='price-amount']"):
                    if self.print_ > 1:
                        print('Found service price')
                    price = services[i].find_element(By.CSS_SELECTOR, "[class='price-amount']").text
                    if self.print_ > 2:
                        print(f'Service price: {price}')
                else:
                    if self.print_ > 1:
                        print('No service price found')
                service = {'name': name, 'price': price}
                services_info.append(service)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error iterating over services: {e}')

        try:
            if self.print_ > 1:
                print('Clicking on seats button')
            self.click_with_retry(seats_button)
            if self.print_ > 1:
                print('Clicked on seats button')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on seats button: {e}')

        if self.print_ > 1:
            print('Exiting services info')
            print('Going to seats page')
        
        return services_info
    
    def check_seat_availability(self, seat):
        
        if self.print_ > 2:
            print(f'Checking seat {seat.get_attribute("title")} availability')
            print(f'Seat class: {seat.get_attribute("class")}')
        try:
            seat_class = seat.get_attribute("class")
            if "seat-characteristic-unavailable" in seat_class:
                if self.print_ > 2:
                    print('Seat unavailable')
                return 'unavailable'
            else:
                if "seat-characteristic-E" in seat_class:
                    if self.print_ > 2:
                        print('Seat available in emergency')
                    return 'emergency'
                else:
                    if self.print_ > 2:
                        print('Seat available')
                    return 'available'
        except Exception as e:
            print(f'Error checking seat {seat.get_attribute("title")} availability: {e}')
    
    def get_flight_seats(self, flights, index, fare_name):

        if self.print_ > 1:
            print('Getting seats')

        page_url = "https://digital.aireuropa.com/booking/seatmap/ST1"

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In seats page')
            else:
                if self.print_ > 1:
                    print('Not in seats page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.get_bags_and_info(flights, index, fare_name)
                    if state == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to seats page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to seats page: {e}')
            return "Abort"
        
        wait_for_loading_to_close(self.driver, "[id='ph-refx-spinner-bottom']")

        time.sleep(5)
        
        try:
            if self.print_ > 1:
                print('Finding seats div')
            
            if check_element_exists_by_TAG_NAME(self.driver, 'refx-seatmap-matrix-pres'):
                seatmap = self.driver.find_element(By.TAG_NAME, 'refx-seatmap-matrix-pres')
                if self.print_ > 1:
                    print('Found seatmap')
            else:
                if self.print_ > 1:
                    print('No seatmap found')
                time.sleep(2)
                self.get_seats()
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding seatmap: {e}')
        
        try:
            if self.print_ > 1:
                print('Finding seats')
            if check_element_exists_by_TAG_NAME(seatmap, 'refx-seatmap-seat-cell-pres'):
                seats = seatmap.find_elements(By.TAG_NAME, 'refx-seatmap-seat-cell-pres')
                if self.print_ > 1:
                    print(f'Found seats: {len(seats)}')
            else:
                if self.print_ > 1:
                    print('No seats found')
                time.sleep(2)
                self.get_flight_seats(fare_name)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding seats: {e}')

        try:
            if self.print_ > 1:
                print('Getting exit icon for position')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[aria-label*='Emergency exit']"):
                exit_icons = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label*='Emergency exit']")
                if self.print_ > 1:
                    print('Found exit icon')
            else:
                if self.print_ > 1:
                    print('No exit icon found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting exit icon: {e}')

        total_seats = [0, 0]
        seats_info = []

        if fare_name == 'Economy':
            names = ['Front', 'Exit', 'Back']
            number_of_classes = 3
        else:
            names = ['Business']
            number_of_classes = 1
        front = False
        exit = False
        back = False
        first_back = True
        for i in range(3):
            if i < number_of_classes:
                name = names[i]
            else:
                name = 'N/A'
            seats_info.append({'name': name, 'price': 'N/A', 'available_seats': 0, 'unavailable_seats': 0})

        try:
            if self.print_ > 1:
                print('Iterating over seats')
            for i in range(len(seats)):
                seat_button = seats[i].find_element(By.TAG_NAME, 'button')
                if self.check_seat_availability(seat_button) == 'available' or self.check_seat_availability(seat_button) == 'emergency':
                    total_seats[0] += 1
                    if fare_name == 'Economy':
                        if self.driver.execute_script(compare_positions, seat_button, exit_icons[0]):
                            if self.print_ > 2:
                                print('Front seat')
                            if not front:
                                price = 'N/A'
                                self.click_with_retry(seat_button)
                                if check_element_exists_by_TAG_NAME(self.driver, 'mat-dialog-container'):
                                    dialog = self.driver.find_element(By.TAG_NAME, 'mat-dialog-container')
                                    if check_element_exists_by_CSS_SELECTOR(dialog, "[class*='price-amount']"):
                                        price = dialog.find_element(By.CSS_SELECTOR, "[class*='price-amount']").text.replace('.', ',')
                                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                seats_info[0]['price'] = price
                                seats_info[0]['available_seats'] += 1 
                                if self.print_ > 2:
                                    print(f'Current available front seats: {seats_info[0]["available_seats"]}')
                                front = True
                            else:
                                seats_info[0]['available_seats'] += 1
                                if self.print_ > 2:
                                    print(f'Current available front seats: {seats_info[0]["available_seats"]}')
                        elif self.driver.execute_script(compare_positions, seat_button, exit_icons[3]):
                            if self.print_ > 2:
                                print('Exit seat')
                            if not exit:
                                price = 'N/A'
                                self.click_with_retry(seat_button)
                                if check_element_exists_by_TAG_NAME(self.driver, 'mat-dialog-container'):
                                    dialog = self.driver.find_element(By.TAG_NAME, 'mat-dialog-container')
                                    if check_element_exists_by_CSS_SELECTOR(dialog, "[class*='price-amount']"):
                                        price = dialog.find_element(By.CSS_SELECTOR, "[class*='price-amount']").text.replace('.', ',')
                                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                seats_info[1]['price'] = price
                                exit = True                            
                            seats_info[1]['available_seats'] += 1
                            if self.print_ > 2:
                                print(f'Current available exit seats: {seats_info[1]["available_seats"]}')
                        else:
                            if first_back:
                                first_back = False
                                if self.print_ > 2:
                                    print('In back block, but is the last seat of the emergency block')
                                seats_info[1]['available_seats'] += 1
                                continue
                            if self.print_ > 2:
                                print('Back seat')
                            if not back:
                                price = 'N/A'
                                self.click_with_retry(seat_button)
                                if check_element_exists_by_TAG_NAME(self.driver, 'mat-dialog-container'):
                                    dialog = self.driver.find_element(By.TAG_NAME, 'mat-dialog-container')
                                    if check_element_exists_by_CSS_SELECTOR(dialog, "[class*='price-amount']"):
                                        price = dialog.find_element(By.CSS_SELECTOR, "[class*='price-amount']").text.replace('.', ',')
                                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                seats_info[2]['price'] = price
                                seats_info[2]['available_seats'] = 1
                                back = True
                            else:
                                seats_info[2]['available_seats'] += 1
                    else:
                        seats_info[0]['available_seats'] += 1
                else:
                    total_seats[1] += 1
                    if fare_name == 'Economy':
                        if self.driver.execute_script(compare_positions, seat_button, exit_icons[0]):
                            seats_info[0]['unavailable_seats'] += 1
                        elif self.driver.execute_script(compare_positions, seat_button, exit_icons[3]):
                            seats_info[1]['unavailable_seats'] += 1
                        else:
                            if first_back:
                                first_back = False
                                if self.print_ > 2:
                                    print('In back block, but is the last seat of the emergency block')
                                seats_info[1]['unavailable_seats'] += 1
                                continue
                            seats_info[2]['unavailable_seats'] += 1
                    else:
                        seats_info[0]['unavailable_seats'] += 1
            if self.print_ > 1:
                print('Iterated over seats')
        except Exception as e:
            if self.print_ > 2:
                print(f'Error getting seats: {e}')
        
        if self.print_ > 1:
            print('Exiting seats page')
            print('Going to next page')
        
        return seats_info

    def close(self):
        self.driver.quit()


def main(origin_name, origin_code, destination_name, destination_code, date):

    # create the object
    aireuropa = AirEuropa(headless=False)

    airliner_site = 'AirEuropa'
    date_for_id = datetime.strptime(date, "%Y/%m/%d").strftime('%d-%m-%Y')

    filename_partial = airliner_site.replace(' ', '') + '/' + 'outputs' + '/' + airliner_site + '_' + time.strftime("%d-%m-%Y")

    fares = ["Economy", "Business"]
    flights_details = []
    flights_seats = []
    flights_services = []
    flights_options = []

    if aireuropa.fill_home_page_form(date, origin_name, origin_code, destination_name, destination_code) == "Abort":
        if inputs.aireuropa_print_ > 0:
            print('Failed to fill home page form. Aborting')
        return
    flights = aireuropa.get_flights()
    if flights is None or len(flights) == 0 or flights == "Abort":
        if inputs.aireuropa_print_ > 0:
            print('Failed to get flights. Aborting')
        return
    flight_id_partial = date_for_id + '_' + origin_code + '-' + destination_code

    if inputs.aireuropa_print_ > 2:
        print(f'Number of flights: {len(flights)}')

    if flights is not None:
        for i in range(0,len(flights)):
            if i != 0:
                if aireuropa.fill_home_page_form(date, origin_name, origin_code, destination_name, destination_code) == "Abort":
                    break
                flights = aireuropa.get_flights()
                if flights is None or len(flights) == 0 or flights == "Abort":
                    break
                if inputs.aireuropa_print_ > 2:
                    print(f'Number of flights: {len(flights)}')
            airliner, details = aireuropa.get_flight_details(flights, index = i)
            if details is not None:
                if details['departure_time'] is not None and details['departure_time'] != 'No time found':
                    flight_id = flight_id_partial + '_' + airliner_site + '_' + details['departure_time']
                else:
                    if aireuropa.print_ > 0:
                        print('An error has occured while getting flight details')
                    continue
            else:
                if aireuropa.print_ > 0:
                    print('An error has occured while getting flight details')
                continue
            flights_details.append(details)
            for fare in fares:
                sold_out = False
                break_outter = False
                # Add logic to exclude flights that are sold out
                observation_id = flight_id + '_' + fare
                if aireuropa.fill_home_page_form(date, origin_name, origin_code, destination_name, destination_code) == "Abort":
                    break
                flights = aireuropa.get_flights()
                if flights is None or len(flights) == 0 or flights == "Abort":
                    break
                if inputs.aireuropa_print_ > 2:
                    print(f'Number of flights: {len(flights)}')
                fare_options = aireuropa.advance_to_your_selection_page(flights, i, fare)
                if fare_options == "Continue":
                    if len(flights_options) > 1 and len(flights_services) > 1 and len(flights_seats) > 1:
                        sold_out = True
                        fare_options_sold_out = flights_options[-2]
                        services_sold_out = flights_services[-2]
                        seats_sold_out = flights_seats[-2]
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        data = {
                            'current_time': current_time,
                            'airliner': airliner,
                            'departure_city_name': origin_name,
                            'departure_city_code': origin_code,
                            'arrival_city_name': destination_name,
                            'arrival_city_code': destination_code,
                            'date': date,
                            'flight_id': flight_id,
                            'observation_id': observation_id,
                            'details': details,
                            'fares': fare_options_sold_out,
                            'services': services_sold_out,
                            'seats': seats_sold_out
                        }
                    else:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        data = {
                            'current_time': current_time,
                            'airliner': airliner,
                            'departure_city_name': origin_name,
                            'departure_city_code': origin_code,
                            'arrival_city_name': destination_name,
                            'arrival_city_code': destination_code,
                            'date': date,
                            'flight_id': flight_id,
                            'observation_id': observation_id,
                            'details': details,
                            'fares': 'Sold Out',
                            'services': 'Sold Out',
                            'seats': 'Sold Out'
                        }
                    filename = filename_partial + '_' + fare + '.csv'
                    file_exists = os.path.isfile(filename)
                    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
                    if file_exists and file_not_empty:
                        mode = 'a'
                        first = False
                    else:
                        mode = 'w'
                        first = True
                    with open(filename, mode=mode, newline='') as file:
                        writer = csv.writer(file)
                        write_to_csv_row(writer, data, first, sold_out=sold_out)
                    break
                flights_options.append(fare_options)
                aireuropa.advance_to_form_page(flights, i, fare)
                aireuropa.fill_passenger_form(flights=flights, index=i, fare_name=fare)
                services = aireuropa.get_bags_and_info(flights, index=i, fare_name=fare)
                flights_services.append(services)
                seats = aireuropa.get_flight_seats(flights, i, fare)
                flights_seats.append(seats)
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data = {
                    'time': current_time,
                    'airliner': airliner,
                    'departure_city_name': origin_name,
                    'departure_city_code': origin_code,
                    'arrival_city_name': destination_name,
                    'arrival_city_code': destination_code,
                    'date': date,
                    'flight_id': flight_id,
                    'observation_id': observation_id,
                    'details': details,
                    'fares': fare_options,
                    'services': services,
                    'seats': seats
                }
                filename = filename_partial + '_' + fare + '.csv'
                file_exists = os.path.isfile(filename)
                file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
                if file_exists and file_not_empty:
                    mode = 'a'
                    first = False
                else:
                    mode = 'w'
                    first = True
                with open(filename, mode=mode, newline='') as file:
                    writer = csv.writer(file)
                    write_to_csv_row(writer, data, first)
                if fare == "Economy":
                    for fare_option in fare_options:
                        if "Business" in fare_option['name']:
                            break_outter = False
                            break
                if break_outter:
                    if len(flights_options) > 1 and len(flights_services) > 1 and len(flights_seats) > 1:
                        sold_out = True
                        fare_options_sold_out = flights_options[-2]
                        services_sold_out = flights_services[-2]
                        seats_sold_out = flights_seats[-2]
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        data = {
                            'current_time': current_time,
                            'airliner': airliner,
                            'departure_city_name': origin_name,
                            'departure_city_code': origin_code,
                            'arrival_city_name': destination_name,
                            'arrival_city_code': destination_code,
                            'date': date,
                            'flight_id': flight_id,
                            'observation_id': observation_id,
                            'details': details,
                            'fares': fare_options_sold_out,
                            'services': services_sold_out,
                            'seats': seats_sold_out
                        }
                    else:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        data = {
                            'current_time': current_time,
                            'airliner': airliner,
                            'departure_city_name': origin_name,
                            'departure_city_code': origin_code,
                            'arrival_city_name': destination_name,
                            'arrival_city_code': destination_code,
                            'date': date,
                            'flight_id': flight_id,
                            'observation_id': observation_id,
                            'details': details,
                            'fares': 'Sold Out',
                            'services': 'Sold Out',
                            'seats': 'Sold Out'
                        }
                    filename = filename_partial + '_' + fare + '.csv'
                    file_exists = os.path.isfile(filename)
                    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
                    if file_exists and file_not_empty:
                        mode = 'a'
                        first = False
                    else:
                        mode = 'w'
                        first = True
                    with open(filename, mode=mode, newline='') as file:
                        writer = csv.writer(file)
                        write_to_csv_row(writer, data, first, sold_out=sold_out)
                    break
    else:
        if aireuropa.print_ > 0:
            print('No flights found')
        flight_id = date_for_id + '_' + origin_code + '-' + destination_code + '_' + str(1)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'current_time': current_time,
            'airliner': airliner,
            'departure_city_name': origin_name,
            'departure_city_code': origin_code,
            'arrival_city_name': destination_name,
            'arrival_city_code': destination_code,
            'date': date,
            'flight_id': flight_id_partial,
            'observation_id': 'N/A',
            'details': 'No flights found',
            'fares': 'No flights found',
            'services': 'No flights found',
            'seats': 'No flights found'
        }
        for fare in fares:
            filename = filename_partial + '_' + fare + '.csv'
            file_exists = os.path.isfile(filename)
            file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
            if file_exists and file_not_empty:
                mode = 'a'
                first = False
            else:
                mode = 'w'
                first = True
            with open(filename, mode=mode, newline='') as file:
                writer = csv.writer(file)
                write_to_csv_row(writer, data, first)
        

    if inputs.aireuropa_print_ > 2:
        print(flights_details)
        print(flights_options)
        print(flights_services)
        print(flights_seats)

    # close the driver
    aireuropa.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Get information about flights page form for AirEuropa")

    parser.add_argument('--origin-name', required=True, help='Origin airport name')
    parser.add_argument('--origin', required=True, help='Origin airport code')
    parser.add_argument('--destination-name', required=True, help='Destination airport name')
    parser.add_argument('--destination', required=True, help='Destination airport code')
    parser.add_argument('--date', required=True, help='Flight date in YYYYY/MM/DD format')

    args = parser.parse_args()

    current_origin_name = args.origin_name
    current_origin_code = args.origin
    current_destination_name = args.destination_name
    current_destination_code = args.destination
    current_date = args.date
    current_fare_name = 'Economy'

    main(origin_name=args.origin_name, origin_code=args.origin, destination_name=args.destination_name, destination_code=args.destination, date=args.date)
                    
                    
                                                       

                                                        



        




            

                


        





    
            
