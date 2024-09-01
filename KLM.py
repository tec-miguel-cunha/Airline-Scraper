# import libraries
import argparse
import os
import threading
import urllib3
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
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

current_origin = ''
current_origin_code = ''
current_destination = ''
current_destination_code = ''
current_flyout_date = ''
current_fare_name = ''
current_flights = []
current_index = 0

def flatten_dict(d, parent_key='', sep='_'):
    if inputs.klm_print_ > 1:
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
    if inputs.klm_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def flatten_dict_with_na(d, parent_key='', sep='_'):
    if inputs.klm_print_ > 1:
        print('Flattening dictionary')
    items = []
    for k, v in d.items():
        if k in {'current_time', 'airliner', 'flight_id', 'observation_id'}:
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
    if inputs.klm_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def write_to_csv_row(writer, data, first=False, sold_out=False):
    if inputs.klm_print_ > 1:
        print('Writing to CSV row')
    # Flatten the details and seats data
    if sold_out:
        flattened_data = flatten_dict_with_na(data)
        flattened_data = flatten_dict(flattened_data)
    else:
        flattened_data = flatten_dict(data)
    if first:
        if inputs.klm_print_ > 1:
            print('Writing header row')
        # Write the header row
        header = list(flattened_data.keys())
        writer.writerow(header)
    
    row = list(flattened_data.values())
    # Write the row to the CSV file
    writer.writerow(row)
    if inputs.iberia_print_ > 1:
        print('Wrote flattened data')

def check_and_close_popup(driver):
    if inputs.klm_print_ > 1:
        print('Checking and closing popup')
    try:
        # Check for overlay element
        overlay = WebDriverWait(driver, timeout=inputs.klm_timeout_cookies).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='rtm-overlay']")))
        if overlay:
            # Find and click the close button
            close_button = overlay.find_element(By.CSS_SELECTOR, "[class*='close-sc closeStyle1-sc']")
            if close_button:
                close_button.click()
                if inputs.klm_print_ > 1:
                    print('Overlay closed')
        else:
            if inputs.klm_print_ > 1:
                print('No overlay found')
    except Exception as e:
        if inputs.klm_print_ > 0:
            print(f'Exception occurred: {e}')

def is_element_in_view(driver, element):
    if inputs.klm_print_ > 1:
        print('Checking if element is in view')
    # Check if the element is displayed
    if element.is_displayed():
        if inputs.klm_print_ > 1:
            print('Element is displayed')
        return True
    else:
        # Scroll the element into view
        if inputs.klm_print_ > 1:
            print('Trying to scroll element into view')
        driver.execute_script("arguments[0].scrollIntoView();", element)
        if inputs.klm_print_ > 1:
            print('Scrolled element into view')
        # Check again if the element is displayed after scrolling
        return element.is_displayed()

def check_element_exists_by_ID(driver, id, timeout=inputs.klm_timeout_checks):
    element_exists = False
    if inputs.klm_print_ > 1:
        print(f'Checking if element exists by ID: {id}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.ID, id)))
        if inputs.klm_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.klm_print_ > 0:
            print(f'No element by ID: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_CSS_SELECTOR(driver, css, timeout=inputs.klm_timeout_checks):
    element_exists = False
    if inputs.klm_print_ > 1:
        print(f'Checking if element exists by CSS: {css}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if inputs.klm_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
        if inputs.klm_print_ > 1:
            print('Element exists')
    except Exception as e:
        if inputs.klm_print_ > 0:
            print(f'No element by CSS Selector: {e}')
        element_exists = False
    return element_exists

def check_element_NOT_exists_by_CSS_SELECTOR(driver, css, timeout=inputs.klm_timeout_checks):
    element_not_exists = False
    if inputs.klm_print_ > 1:
        print(f'Checking if element not exists by CSS: {css}')
    try:
        WebDriverWait(driver, timeout=timeout).until_not(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if inputs.klm_print_ > 1:
            print("Passed WebDriverWait")
        element_not_exists = True
    except Exception as e:
        if inputs.klm_print_ > 0:
            print(f'Element exists by CSS Selector: {e}')
        element_not_exists = False
    return element_not_exists

def check_element_exists_by_TAG_NAME(driver, tag, timeout=inputs.klm_timeout_checks):
    element_exists = False
    if inputs.klm_print_ > 1:
        print(f'Checking if element exists by Tag Name: {tag}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.TAG_NAME, tag)))
        if inputs.klm_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.klm_print_ > 0:
            print(f'No element by Tag Name: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_XPATH(driver, xpath, timeout=inputs.klm_timeout_checks):
    element_exists = False
    if inputs.klm_print_ > 1:
        print(f'Checking if element exists by XPATH: {xpath}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
        if inputs.klm_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.klm_print_ > 0:
            print(f'No element by XPATH: {e}')
        element_exists = False
    return element_exists

def check_and_wait_for_URL(driver, url, timeout=inputs.klm_timeout):
    if inputs.klm_print_ > 1:
        print(f'Checking and waiting for URL: {url}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.url_to_be(url))
        if inputs.klm_print_ > 1:
            print("Passed WebDriverWait")
        return True
    except Exception as e:
        if inputs.klm_print_ > 0:
            print(f'URL not found: {e}')
        return False

class KLM:

    def __init__(self, headless=True):

        self.timeout = inputs.klm_timeout
        self.timeout_cookies = inputs.klm_timeout_cookies
        self.timeout_little = inputs.klm_timeout_little
        self.timeout_implicitly_wait = inputs.klm_timeout_implicitly_wait
        self.print_ = inputs.klm_print_
        self.cookies = 'not accepted'
        self.GDPR = 'not accepted'
        self.closed_popup_cabin_bags = False
        self.retries = 3
        self.new_tab_opened = False
        self.closed_fares_overlay = False
        self.searched = False

        self.buttons = []

        if self.print_ > 1:
            print('Initializing KLM')
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = uc.Chrome()
        if self.print_ > 1:
            print('Initialized KLM')

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

    def get_element_by_CSS_SELECTOR(self, element, css, timeout=inputs.klm_timeout_checks):
        if self.print_ > 1:
            print(f'Getting element by CSS: {css}')
        try:
            temp = WebDriverWait(element, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
            if self.print_ > 1:
                print('Found element')
            return temp
        except Exception as e:
            if self.print_ > 0:
                print(f'No element by CSS Selector: {e}')
            return None

    def fill_home_page_form(self, flyout, orig, dest, repeat=True, retreis=0):
        if self.print_ > 1:
            print('Entering Fill Form Function')
        # set url
        url = f'https://www.klm.pt/en'
        # get the page
        self.driver.get(url)
        if self.print_ > 1:    
            print('Opened KLM homepage')
        self.driver.implicitly_wait(self.timeout_implicitly_wait)

        if self.cookies == 'not accepted':
            try:
                if self.print_ > 1:
                    print('Trying to close cookies popup')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='bw-cookie-banner__main']"):
                    cookies_popup = self.driver.find_element(By.CSS_SELECTOR, "[class*='bw-cookie-banner__main']")
                    if self.print_ > 1:
                        print('Found cookies popup')
                    if check_element_exists_by_ID(cookies_popup, 'accept_cookies_btn'):
                        accept_button = cookies_popup.find_element(By.ID, 'accept_cookies_btn')
                        self.click_with_retry(accept_button)
                        if self.print_ > 1:
                            print('Clicked accept button')
                        self.cookies = 'accepted'
                    else:
                        if self.print_ > 1:
                            print('No accept button found')
                else:
                    if self.print_ > 1:
                        print('No cookies popup found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error closing cookies popup: {e}')

        time.sleep(2)

        if repeat:
            try:
                if self.print_ > 1:
                    print('Trying to open rest of home page form')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwsfe-widget__open-search-button']", self.timeout):
                    open_search_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwsfe-widget__open-search-button']")
                    self.click_with_retry(open_search_button)
                    if self.print_ > 1:
                        print('Clicked to open home page form')
                else:
                    if self.print_ > 1:
                        print('No button to open home page form found')
                    if retreis < 3:
                        self.driver.refresh()
                        time.sleep(5)
                        return self.fill_home_page_form(flyout, orig, dest, retreis=retreis+1)
                    else:
                        if self.print_ > 0:
                            print('Failed to open home page form after retries')
                        return "Abort"
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error opening rest of home page form: {e}')
                return "Abort"
            
        else:
            try:
                if self.print_ > 1:
                    print('Trying to one way option in select')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[formcontrolname='tripKind']"):
                    select_element = self.driver.find_element(By.CSS_SELECTOR, "[formcontrolname='tripKind']")
                    select = Select(select_element)
                    select.select_by_index(1)
                    if self.print_ > 1:
                        print('Selected one way option')
                else:
                    if self.print_ > 1:
                        print('No select element found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to select one way option: {e}')

            try:
                if self.print_ > 1:
                    print('Trying to enter origin')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test-value='origin']"):
                    origin = self.driver.find_element(By.CSS_SELECTOR, "[data-test-value='origin']")
                    origin.send_keys(orig)
                    time.sleep(1)
                    origin.send_keys(Keys.RETURN)
                else:
                    if self.print_ > 1:
                        print('No origin field found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to enter origin: {e}')
            
            try:
                if self.print_ > 1:
                    print('Trying to enter destination')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test-value='destination']"):
                    destination = self.driver.find_element(By.CSS_SELECTOR, "[data-test-value='destination']")
                    destination.send_keys(dest)
                    time.sleep(1)
                    destination.send_keys(Keys.RETURN)
                else:
                    if self.print_ > 1:
                        print('No destination field found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to enter destination: {e}')

            try:
                if self.print_ > 1:
                    print('Trying to open calendar')
                if check_element_exists_by_TAG_NAME(self.driver, 'bw-datepicker'):
                    klm_div = self.driver.find_element(By.TAG_NAME, 'bw-datepicker')
                    if self.print_ > 1:
                        print('Found input div')
                    if check_element_exists_by_CSS_SELECTOR(klm_div, "[class*='mat-mdc-text-field-wrapper']"):
                        klm_field = klm_div.find_element(By.CSS_SELECTOR, "[class*='mat-mdc-text-field-wrapper']")
                        self.click_with_retry(klm_field)
                        if self.print_ > 1:
                            print('Clicked to open calendar')
                    else:
                        if self.print_ > 1:
                            print('No input field found')
                else:
                    if self.print_ > 1:
                        print('No input div found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to open calendar: {e}')

            try:
                if self.print_ > 1:
                    print('Trying to enter date')
                if check_element_exists_by_TAG_NAME(self.driver, 'bwc-calendar'):
                    if self.print_ > 1:
                        print('Found calendar')
                    calendar = self.driver.find_element(By.TAG_NAME, 'bwc-calendar')
                    parsed_date = datetime.strptime(flyout, "%d/%m/%Y")
                    formatted_date = parsed_date.strftime("%d %B %Y")
                    if check_element_exists_by_CSS_SELECTOR(calendar, f"[aria-label*='{formatted_date}']"):
                        date = calendar.find_element(By.CSS_SELECTOR, f"[aria-label*='{formatted_date}']")
                        self.click_with_retry(date)
                        if self.print_ > 1:
                            print('Clicked on date')
                    else:
                        if self.print_ > 1:
                            print('No date found')
                else:
                    if self.print_ > 1:
                        print('No calendar found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to enter date: {e}')

            try: # click on button with data-test='bwc-calendar__confirm'
                if self.print_ > 1:
                    print('Trying to click continue button')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwc-calendar__confirm']"):
                    continue_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwc-calendar__confirm']")
                    self.click_with_retry(continue_button)
                    if self.print_ > 1:
                        print('Clicked continue button')
                else:
                    if self.print_ > 1:
                        print('No continue button found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to click continue button: {e}')

        try:
            if self.print_ > 1:
                print('Trying to open rest of home page form')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwsfe-widget__search-button']", self.timeout):
                search_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwsfe-widget__search-button']")
                self.click_with_retry(search_button)
                if self.print_ > 1:
                    print('Clicked search button')
            else:
                if self.print_ > 1:
                    print('No search button found')
                if retreis < 3:
                    self.driver.refresh()
                    time.sleep(5)
                    return self.fill_home_page_form(flyout, orig, dest, retreis=retreis+1)
                else:
                    if self.print_ > 0:
                        print('Failed click search button after retries')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to click search button: {e}')
            return "Abort"

        if self.print_ > 1:
            print('Exiting fill home page form function')
            print('Going to next page')

    def get_flights(self):

        if self.print_ > 1:
            print('Getting Flights')

        page_url = "https://www.klm.pt/en/search/flights/0"
        flights = []

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
                    state = self.fill_home_page_form()
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
        
        try:
            if self.print_ > 1:
                print('Getting direct flights')
            if check_element_exists_by_TAG_NAME(self.driver, 'bwsfe-search-result-list'):
                flights_results_div = self.driver.find_element(By.TAG_NAME, 'bwsfe-search-result-list')
                if self.print_ > 1:
                    print('Found flights results div')
                if check_element_exists_by_TAG_NAME(self.driver, 'section'):
                    flights_section = flights_results_div.find_elements(By.TAG_NAME, 'section')[0]
                    if self.print_ > 1:
                        print('Found flights section')
                    if check_element_exists_by_TAG_NAME(flights_section, 'ol'):
                        flights_list = flights_section.find_element(By.TAG_NAME, 'ol')
                        if self.print_ > 1:
                            print('Found flights list')
                        if check_element_exists_by_TAG_NAME(flights_list, 'li'):
                            flights = flights_list.find_elements(By.TAG_NAME, 'li')
                            if self.print_ > 1:
                                print('Found flights')
                        else:
                            if self.print_ > 1:
                                print('No flights found')
                    else:
                        if self.print_ > 1:
                            print('No flights list found')
                else:
                    if self.print_ > 1:
                        print('No flights section found')
            else:
                if self.print_ > 1:
                    print('No flights results div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting direct flights: {e}')
            return "Abort"
        
        if self.print_ > 1:
            print('Returning flights')

        return flights
    
    def get_flight_details(self, flights, index, repeat=False):

        if self.print_ > 1:
            print('Getting flight details')

        if repeat:
            self.get_flights()[index]
        else:
            flight = flights[index]

        departure_flyout_time = 'N/A'
        arrival_flyout_time = 'N/A'
        price_economy = 'N/A'
        price_business = 'N/A'

        try:
            if self.print_ > 1:
                print('Trying to get departure and arrival times')
            if check_element_exists_by_TAG_NAME(flight, 'bwsfc-itinerary-station-node'):
                itinerary = flight.find_elements(By.TAG_NAME, 'bwsfc-itinerary-station-node')
                if self.print_ > 1:
                    print('Found departure and arrival times')
                if len(itinerary) > 1:
                    departure_flyout_time = itinerary[0].find_element(By.TAG_NAME, 'time').text
                    arrival_flyout_time = itinerary[-1].find_element(By.TAG_NAME, 'time').text
                    if self.print_ > 1:
                        print('Got departure and arrival times')
                else:
                    if self.print_ > 1:
                        print('Not enough dates found')
            else:
                if self.print_ > 1:
                    print('No departure and arrival times found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting departure and arrival times: {e}')

        try:
            if self.print_ > 1:
                print('Trying to get prices')
            if check_element_exists_by_TAG_NAME(flight, 'bwsfc-cabin-class-card'):
                fares_buttons = flight.find_elements(By.TAG_NAME, 'bwsfc-cabin-class-card')
                if self.print_ > 1:
                    print('Found prices')
                if check_element_exists_by_CSS_SELECTOR(fares_buttons[0], "[class*='bwsfc-cabin-class-card__price-amount']"): 
                    price_economy = fares_buttons[0].find_element(By.CSS_SELECTOR, "[class*='bwsfc-cabin-class-card__price-amount']").text
                    price_economy = ''.join(re.findall(r'\d+', price_economy))
                else:
                    price_economy = 'Sold Out'
                if check_element_exists_by_CSS_SELECTOR(fares_buttons[1], "[class*='bwsfc-cabin-class-card__price-amount']"):
                    price_business = fares_buttons[1].find_element(By.CSS_SELECTOR, "[class*='bwsfc-cabin-class-card__price-amount']").text
                    price_business = ''.join(re.findall(r'\d+', price_business))
                else:
                    price_business = 'Sold Out'
                if self.print_ > 1:
                    print('Got prices')
            else:
                if self.print_ > 1:
                    print('No prices found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting prices: {e}')

        try:
            if check_element_exists_by_TAG_NAME(flight, 'bwc-carrier-logo'):
                carrier_logo = flight.find_element(By.TAG_NAME, 'bwc-carrier-logo')
                image = carrier_logo.find_element(By.TAG_NAME, 'img')
                airliner = image.get_attribute('alt')
                if self.print_ > 1:
                    print(f'Got carrier name: {airliner}')
            else:
                airliner = 'N/A'
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting airliner: {e}')

        if self.print_ > 1:
            print('Returning flight details')

        details = {
            'departure_time': departure_flyout_time,
            'arrival_time': arrival_flyout_time,
            'price_economy': price_economy,
            'price_business': price_business
        }

        return airliner, details
    
    def advance_to_your_selection_page(self, flights = current_flights, index = current_index, fare_name = current_fare_name):

        if self.print_ > 1:
            print('Entering function to advance to your selection page')

        flight = flights[index]

        try:
            if self.print_ > 1:
                print('Trying to get select fare')
            if check_element_exists_by_TAG_NAME(flight, 'bwsfc-cabin-class-card'):
                fares_buttons = flight.find_elements(By.TAG_NAME, 'bwsfc-cabin-class-card')
                if self.print_ > 1:
                    print('Found prices')
                if fare_name == 'Economy':
                    if not self.click_with_retry(fares_buttons[0]):
                        if self.print_ > 0:
                            print('Failed to click on Economy fare')
                        return "Sold Out"
                else:
                    if not self.click_with_retry(fares_buttons[1]):
                        if self.print_ > 0:
                            print('Failed to click on Business fare')
                        return "Sold Out"
                if self.print_ > 1:
                    print('Got prices')
            else:
                if self.print_ > 1:
                    print('No prices found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting prices: {e}')
            
        fares = []

        try:
            if self.print_ > 1:
                print('Waiting for upsells container')
            if check_element_exists_by_TAG_NAME(self.driver, 'bw-upsells-container'):
                upsells_container = self.driver.find_element(By.TAG_NAME, 'bw-upsells-container')
                if self.print_ > 1:
                    print('Found upsells container')
                if check_element_exists_by_TAG_NAME(upsells_container, 'bws-flight-upsell-item'):
                    fares_divs = upsells_container.find_elements(By.TAG_NAME, 'bws-flight-upsell-item')
                    for i in range(len(fares_divs)):
                        fare_name = fares_divs[i].find_element(By.TAG_NAME, 'h3').find_element(By.TAG_NAME, 'span').text
                        if self.print_ > 1:
                            print('Found fare name')
                        fare_price_div = fares_divs[i].find_element(By.TAG_NAME, 'bws-flight-upsell-price')
                        if self.print_ > 1:
                            print('Found fare price div')
                        fare_price = fare_price_div.find_element(By.TAG_NAME, 'span').text
                        fare_price = ''.join(re.findall(r'\d+', fare_price))
                        if self.print_ > 1:
                            print('Found fare price')
                        if i == 0:
                            button_to_click = fares_divs[i].find_element(By.CSS_SELECTOR, "[data-test='bws-flight-upsell-confirm__button']")
                            if self.print_ > 1:
                                print('Found button to click')
                        fares.append({
                            'name': fare_name,
                            'price': fare_price
                        })
                else:
                    if self.print_ > 1:
                        print('No fares found')
            else:
                if self.print_ > 1:
                    print('No upsells container found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting upsells: {e}')
            return "Abort"
    
        try:
            if self.print_ > 1:
                print('Trying to click button')
            self.click_with_retry(button_to_click)
            if self.print_ > 1:
                print('Clicked button')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking button: {e}')

        if self.print_ > 1:
            print('Exiting function to advance to your selection page')
            print('Going to next page')

        return fares

    def advance_to_passenger_form(self):

        if self.print_ > 1:
            print('Entering function to advance to passenger form')

        page_url = "https://www.klm.pt/en/search/search-summary"

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
                    state = self.advance_to_your_selection_page(flights=current_flights, index=current_index, fare_name=current_fare_name)
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
        
        try:
            if self.print_ > 1:
                print('Trying to click continue button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwss-summary-container__continue']"):
                continue_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwss-summary-container__continue']")
                self.click_with_retry(continue_button)
                if self.print_ > 1:
                    print('Clicked continue button')
            else:
                if self.print_ > 1:
                    print('No continue button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to click continue button: {e}')
        
        if self.print_ > 1:
            print('Exiting function to advance to passenger form')
            print('Going to next page')

    def fill_passenger_form(self):

        if self.print_ > 1:
            print('Entering function to fill passenger form')

        page_url = "https://www.klm.pt/en/checkout/passenger-details"

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
                    state = self.advance_to_passenger_form()
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

        time.sleep(2)

        try:
            if self.print_ > 1:
                print('Trying to get title field')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='bwc-grid bwco-personal-details__fields']", self.timeout):
                title_selector_div = self.driver.find_element(By.CSS_SELECTOR, "[class*='bwc-grid bwco-personal-details__fields']")
                if self.print_ > 1:
                    print('Found title field div')
                if check_element_exists_by_TAG_NAME(title_selector_div, 'select'):
                    title_selector = title_selector_div.find_element(By.TAG_NAME, 'select')
                    if self.print_ > 1:
                        print('Found title field')
                    select = Select(title_selector)
                    select.select_by_index(1)
                    if self.print_ > 1:
                        print('Selected title')
                else:
                    if self.print_ > 1:
                        print('No title field found')
            else:
                if self.print_ > 1:
                    print('No title field div found')
                self.driver.refresh()
                if self.fill_passenger_form() == "Abort":
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting title: {e}')

        try:
            if self.print_ > 1:
                print('Trying to get first name field')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[name='firstName']"):
                first_name = self.driver.find_element(By.CSS_SELECTOR, "[name='firstName']")
                first_name.clear()
                first_name.send_keys('Miguel')
                if self.print_ > 1:
                    print('Entered first name')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[name='lastName']"):
                    last_name = self.driver.find_element(By.CSS_SELECTOR, "[name='lastName']")
                    last_name.clear()
                    last_name.send_keys('Cunha')
                    if self.print_ > 1:
                        print('Entered last name')
                else:
                    if self.print_ > 1:
                        print('No last name field found')
            else:
                if self.print_ > 1:
                    print('No first name field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering first name: {e}')
            return "Abort"

        try:
            if self.print_ > 1:
                print('Clicking on Continue button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwco-personal-details__continue']"):
                continue_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwco-personal-details__continue']")
                self.click_with_retry(continue_button)
                if self.print_ > 1:
                    print('Clicked continue button')
            else:
                if self.print_ > 1:
                    print('No continue button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking continue button: {e}')
            return "Abort"

        time.sleep(1)

        try:
            if self.print_ > 1:
                print('Inserting Contact Details')
            if check_element_exists_by_TAG_NAME(self.driver, 'bw-checkout-pax-contact-details'):
                contact_details_div = self.driver.find_element(By.TAG_NAME, 'bw-checkout-pax-contact-details')
                if self.print_ > 1:
                    print('Found contact details div')
                if check_element_exists_by_TAG_NAME(contact_details_div, 'select'):
                    country_code_select = contact_details_div.find_element(By.TAG_NAME, 'select')
                    Select(country_code_select).select_by_value('PT')
                    if self.print_ > 1:
                        print('Selected country code')
                else:
                    if self.print_ > 1:
                        print('No country code found')
                if check_element_exists_by_CSS_SELECTOR(contact_details_div, "[name='phoneNumberFirst']"):
                    phone_number = contact_details_div.find_element(By.CSS_SELECTOR, "[name='phoneNumberFirst']")
                    phone_number.clear()
                    phone_number.send_keys('912345678')
                    if self.print_ > 1:
                        print('Entered phone number')
                else:
                    if self.print_ > 1:
                        print('No phone number found')
                if check_element_exists_by_CSS_SELECTOR(contact_details_div, "[name='emailAddress']"):
                    email = contact_details_div.find_element(By.CSS_SELECTOR, "[name='emailAddress']")
                    email.clear()
                    email.send_keys('abc123@gmail.com')
                    if self.print_ > 1:
                        print('Entered email')
                else:
                    if self.print_ > 1:
                        print('No email found')
            else:
                if self.print_ > 1:
                    print('No contact details div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error inserting contact details: {e}')
            return "Abort"

        try: # Click on continue button with this data-test bwco-contact-details__continue
            if self.print_ > 1:
                print('Clicking on Close details button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwco-contact-details__continue']"):
                continue_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwco-contact-details__continue']")
                self.click_with_retry(continue_button)
                if self.print_ > 1:
                    print('Clicked close details button')
            else:
                if self.print_ > 1:
                    print('No close details button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking close details button: {e}')
            return "Abort"

        try:
            if self.print_ > 1:
                print('Trying to click continue button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwco-pax__continue']"):
                continue_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwco-pax__continue']")
                self.click_with_retry(continue_button)
                if self.print_ > 1:
                    print('Clicked continue button')
            else:
                if self.print_ > 1:
                    print('No continue button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking continue button: {e}')
            return "Abort"
        
        
        if self.print_ > 1:
            print('Exiting function to fill passenger form')
            print('Going to next page')

    def get_bags_and_info(self):

        if self.print_ > 1:
            print('Entering function to get bags and info')

        bags = []
        page_url = "https://www.klm.pt/en/checkout/ancillaries"

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In seat selection page')
            else:
                if self.print_ > 1:
                    print('Not in seat selection page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.fill_passenger_form()
                    if state == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to seat selection page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to seat selection page: {e}')
            return "Abort"
        
        try:
            if self.print_ > 1:
                print('Trying to get info on bags')
            
            if check_element_exists_by_TAG_NAME(self.driver, 'bwan-push-card-product-baggage'):
                bags_div = self.driver.find_element(By.TAG_NAME, 'bwan-push-card-product-baggage')
                if self.print_ > 1:
                    print('Found bags div')
                if check_element_exists_by_TAG_NAME(bags_div, 'a'):
                    bags_button = bags_div.find_element(By.TAG_NAME, 'a')
                    if self.print_ > 1:
                        print('Found bags button')
                    self.click_with_retry(bags_button)
                    if self.print_ > 1:
                        print('Clicked bags button')
                else:
                    if self.print_ > 1:
                        print('No bags button found')
            else:
                if self.print_ > 1:
                    print('No bags div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting bags info: {e}')
        
        try:
            if self.print_ > 1:
                print('Trying to get bags')
            if check_element_exists_by_TAG_NAME(self.driver, 'mat-select'):
                bags_select = self.driver.find_element(By.TAG_NAME, 'mat-select')
                if self.print_ > 1:
                    print('Found bags select')
                self.click_with_retry(bags_select)
                if self.print_ > 1:
                    print('Clicked bags select')
                if check_element_exists_by_TAG_NAME(self.driver, 'mat-option'):
                    bags_option = self.driver.find_elements(By.TAG_NAME, 'mat-option')[1]
                    if self.print_ > 1:
                        print('Found bags option')
                    if check_element_exists_by_TAG_NAME(bags_option, 'span'):
                        bags_text = bags_option.find_element(By.TAG_NAME, 'span').text
                        if self.print_ > 1:
                            print('Found bags text')
                        match = re.search(r"EUR (\d+)", bags_text)
                        if match:
                            price = match.group(1)
                            if self.print_ > 1:
                                print(f'Extracted price: {price}')
                            bags.append({'name': 'Checked Bag', 'price': price})
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        else:
                            if self.print_ > 1:
                                print('No price found')
                    else:
                        if self.print_ > 1:
                            print('No bags text found')
                else:
                    if self.print_ > 1:
                        print('No bags overlay found')
            else:
                if self.print_ > 1:
                    print('No bags select found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting bags: {e}')

        try:
            if self.print_ > 1:
                print('Trying to click on back button')

            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwc-subheader-back-button']"):
                back_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwc-subheader-back-button']")
                self.click_with_retry(back_button)
                if self.print_ > 1:
                    print('Clicked back button')
            else:
                if self.print_ > 1:
                    print('No back button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking back button: {e}')

        if self.print_ > 1:
            print('Returning bags and info')
            print('Exiting function get bags and info')

        return bags
    
    def get_to_seats_page(self):

        if self.print_ > 1:
            print('Entering function to get seats page')

        page_url = "https://www.klm.pt/en/checkout/ancillaries"

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
                    state = self.fill_passenger_form()
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
        
        try:
            if self.print_ > 1:
                print('Trying to click on seats button')
            if check_element_exists_by_TAG_NAME(self.driver, 'bwan-push-card-product-seat'):
                bags_div = self.driver.find_element(By.TAG_NAME, 'bwan-push-card-product-seat')
                if self.print_ > 1:
                    print('Found seats div')
                if check_element_exists_by_TAG_NAME(bags_div, 'a'):
                    seats_button = bags_div.find_element(By.TAG_NAME, 'a')
                    if self.print_ > 1:
                        print('Found seats button')
                    self.click_with_retry(seats_button)
                    if self.print_ > 1:
                        print('Clicked seats button')
                else:
                    if self.print_ > 1:
                        print('No seats button found')
            else:
                if self.print_ > 1:
                    print('No seats div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting seats info: {e}')

        if self.print_ > 1:
            print('Exiting function to get seats page')
            print('Going to next page')

    def check_seat_availability(self, seat, fare_name = current_fare_name):

        if self.print_ > 1:
            print('Checking seat availability')

        try:
            seat_href = seat.get_attribute("href")
            if self.print_ > 2:
                print(f'Seat href: {seat_href}')
            zone_match = re.search(r"Paid seats=([^,]+)", seat_href)
            state_match = re.search(r"State=([^,]+)(?:,|$)", seat_href)
            zone = 'N/A'
            state = 'N/A'

            if zone_match:
                zone = zone_match.group(1)
            if state_match:
                state = state_match.group(1)
            
            if zone == 'N/A':
                if fare_name == 'Business':
                    zone = 'Business'
                    if self.print_ > 2:
                        print(f'Zone is business. Availability is {state}')
                    return zone, state
            else:
                if fare_name == 'Business':
                    return 'N/A', 'N/A'
                    

            if self.print_ > 3:
                print(f'Seat zone: {zone}')
                print(f'Seat state: {state}')
            return zone, state

        except Exception as e:
            print(f'Error checking seat {seat.get_attribute("title")} availability: {e}')
    
    def get_seats(self, fare_name = current_fare_name):

        if self.print_ > 1:
            print('Entering function to get seats')

        seats_info = []
        
        try: # Wait for element with this class 'bw-seatmap-spinner__overlay-inner-content' to disappear
            if self.print_ > 1:
                print('Waiting for spinner to disappear')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='bw-seatmap-spinner__overlay-inner-content']", timeout=self.timeout):
                spinner = self.driver.find_element(By.CSS_SELECTOR, "[class*='bw-seatmap-spinner__overlay-inner-content']")
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element(spinner))
                if self.print_ > 1:
                    print('Spinner disappeared')
            else:
                if self.print_ > 1:
                    print('No spinner found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error waiting for spinner to disappear: {e}')

        try:
            if self.print_ > 1:
                print('Trying to get seatmap')
            if check_element_exists_by_TAG_NAME(self.driver, 'bw-seatmap-svg-deck'):
                seatmap = self.driver.find_element(By.TAG_NAME, 'bw-seatmap-svg-deck')
                if self.print_ > 1:
                    print('Found seatmap')
                if check_element_exists_by_TAG_NAME(seatmap, 'use'):
                    seats = seatmap.find_elements(By.TAG_NAME, 'use')
                    if self.print_ > 1:
                        print('Found seats')
                    if self.print_ > 2:
                        print(f'Number of seats: {len(seats)}')
                else:
                    if self.print_ > 1:
                        print('No seats found')
            else:
                if self.print_ > 1:
                    print('No seatmap found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting seats: {e}')

        names = ['Business', 'Economy Comfort', 'Front Seat', 'Extra leg room', 'Economy']

        for zone in names:
            seats_info.append({'zone': zone, 'price': 'N/A', 'available': 0, 'unavailable': 0})

        time.sleep(2)
                        
        try:
            if self.print_ > 1:
                print('Checking all seats and availability')
            for seat in seats:
                seat_zone, seat_availability = self.check_seat_availability(seat, fare_name)
                if fare_name == 'Economy':
                    if seat_zone == 'N/A' or seat_availability == 'N/A':
                        continue
                    if self.print_ > 3:
                        print(f'Seat type: {seat_zone}')
                        print(f'Seat availability: {seat_availability}')
                    for seat_info in seats_info:
                        if seat_info['zone'] == seat_zone:
                            if seat_availability == 'Available':
                                seat_info['available'] += 1
                            else:
                                seat_info['unavailable'] += 1
                            break
                else:
                    if seat_zone == 'Business':
                        if seat_availability == 'Available':
                            seats_info[0]['available'] += 1
                        else:
                            seats_info[0]['unavailable'] += 1

        except Exception as e:
            if self.print_ > 0:
                print(f'Error checking seats availability: {e}')

        if fare_name == 'Economy':
            try:
                if self.print_ > 1:
                    print('Trying to get price of seats')
                if check_element_exists_by_TAG_NAME(self.driver, 'bw-seatmap-commercial-legend'):
                    seats_info_legend_container = self.driver.find_element(By.TAG_NAME, 'bw-seatmap-commercial-legend')
                    if self.print_ > 1:
                        print('Found seats info legend container')
                    if check_element_exists_by_TAG_NAME(seats_info_legend_container, 'bws-seatmap-legend-item'):
                        seats_info_legends = seats_info_legend_container.find_elements(By.TAG_NAME, 'bws-seatmap-legend-item')
                        for legend in seats_info_legends:
                            if check_element_exists_by_TAG_NAME(legend, 'mat-expansion-panel-header'):
                                header = legend.find_element(By.TAG_NAME, 'mat-expansion-panel-header')
                                panel_title = header.find_element(By.TAG_NAME, 'mat-panel-title')
                                divs = panel_title.find_elements(By.TAG_NAME, 'div')
                                if check_element_exists_by_TAG_NAME(divs[1], 'span'):
                                    price = divs[1].find_element(By.TAG_NAME, 'span').text
                                    price = ''.join(re.findall(r'\d+\.\d+|\d+', price))
                                    for seat_info in seats_info:
                                        if seat_info['zone'] in divs[0].text:
                                            seat_info['price'] = price
                                            continue
                                else:
                                    if self.print_ > 1:
                                        print('No price found')
                                        print('Opening legend')
                                    self.click_with_retry(header)
                                    if check_element_exists_by_TAG_NAME(legend, 'bw-seatmap-commercial-legend-item', timeout=self.timeout_little):
                                        legend_items = legend.find_elements(By.TAG_NAME, 'bw-seatmap-commercial-legend-item')
                                    else:
                                        if self.print_ > 1:
                                            print('Could not find legend items by TAG_NAME: bw-seatmap-commercial-legend-item')
                                            print('Looking for buttons')
                                        if check_element_exists_by_TAG_NAME(legend, 'button'):
                                            legend_items = legend.find_elements(By.TAG_NAME, 'button')
                                    for item in legend_items:
                                        if check_element_exists_by_CSS_SELECTOR(item, "[class*='__content-header']"):
                                            item_infos_div = item.find_element(By.CSS_SELECTOR, "[class*='__content-header']")
                                            if check_element_exists_by_TAG_NAME(item_infos_div, 'div'):
                                                divs = item_infos_div.find_elements(By.TAG_NAME, 'div')
                                                if "Front" in divs[0].text:
                                                    price = divs[1].find_element(By.TAG_NAME, 'span').text
                                                    price = ''.join(re.findall(r'\d+\.\d+|\d+', price))
                                                    seats_info[2]['price'] = price
                                                elif "Extra legroom" in divs[0].text:
                                                    price = divs[1].find_element(By.TAG_NAME, 'span').text
                                                    price = ''.join(re.findall(r'\d+\.\d+|\d+', price))
                                                    seats_info[3]['price'] = price
                                                elif "Standard" in divs[0].text:
                                                    price = divs[1].find_element(By.TAG_NAME, 'span').text
                                                    price = ''.join(re.findall(r'\d+\.\d+|\d+', price))
                                                    seats_info[4]['price'] = price
                                        else:
                                            if self.print_ > 1:
                                                print('No item infos div found')
                else:
                    if self.print_ > 1:
                        print('No seats info legend container found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error getting price of seats: {e}')

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-test='bwc-subheader-back-button']"):
                back_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test='bwc-subheader-back-button']")
                self.click_with_retry(back_button)
                if self.print_ > 1:
                    print('Clicked back button')
            else:
                if self.print_ > 1:
                    print('No back button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking back button: {e}')

        if self.print_ > 1:
            print('Exiting get seats function')

        return seats_info
    
    def get_back_to_home_page(self):

        if self.print_ > 1:
            print('Entering function to get back to home page')
        
        page_url = "https://www.klm.pt/en/checkout/ancillaries"

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
                    state = self.fill_home_page_form()
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
        
        try:
            if self.print_ > 1:
                print('Trying to click on button to go back to search page')
            if check_element_exists_by_TAG_NAME(self.driver, 'bwc-trip-stepper-step'):
                back_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'bwc-trip-stepper-step')
                if self.print_ > 1:
                    print('Found back button')
                for back_button in back_buttons:
                    button = back_button.find_element(By.TAG_NAME, 'button')
                    if button.get_attribute("aria-label") == "Search":
                        self.click_with_retry(button)
                        if self.print_ > 1:
                            print('Clicked back button')
                        break
            else:
                if self.print_ > 1:
                    print('No back button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking back button: {e}')

        if self.print_ > 1:
            print('Exiting function to get back to home page')
            print('Going to Home page')

    def close(self):
        if self.print_ > 1:
            print('Closing driver')
        self.driver.quit()


def main(origin_name, origin_code, destination_name, destination_code, date):


    klm = KLM(headless=False)

    airliner_site = "KLM"
    filename_partial = airliner_site.replace(' ', '') + '/'  + 'outputs' + '/' + airliner_site + '_' + time.strftime("%d-%m-%Y")

    date_for_id = datetime.strptime(date, "%Y/%m/%d").strftime('%d-%m-%Y')

    flight_id_partial = date_for_id + '_' + origin_code + '-' + destination_code

    flights_details = []
    flights_fares = []
    flights_infos = []
    flights_seats = []
    
    flyout = datetime.strptime(date, '%Y/%m/%d').strftime('%d/%m/%Y')

    fare_names = ['Economy', 'Business']

    if klm.fill_home_page_form(flyout=flyout, orig=origin_name, dest=destination_name, repeat=False) == "Abort":
        if klm.print_ > 0:
            print('Closing driver due to error filling home page form. Going to open a new one')
        klm.close()
        klm = KLM(headless=False)
        if klm.fill_home_page_form(flyout=flyout, orig=origin_name, dest=destination_name) == "Abort":
            if klm.print_ > 0:
                print('Aborting due to error filling home page form')
            return
        else:
            if klm.print_ > 2:
                print('Filled home page form at second attempt')
    else:
        if klm.print_ > 2:
            print('Filled home page form at first attempt')

    flights = klm.get_flights()
    current_flights = flights

    if flights is not None:
        if klm.print_ > 2:
            print(f'Found {len(flights)} flights')
        for i in range(len(flights)):
            flight_id = flyout.replace('/', '-') + '_' + origin_code + '-' + destination_code + '_' + str(i+1)
            for j in range(len(fare_names)):
                sold_out = False
                current_fare_name = fare_names[j]
                fare_name = fare_names[j]
                if not (i == 0 and j == 0):
                    if klm.fill_home_page_form(flyout=flyout, orig=origin_name, dest=destination_name) == "Abort":
                        if klm.print_ > 0:
                            print('Aborting due to error filling home page form')
                        return
                    flights = klm.get_flights()
                    current_flights = flights
                airliner, details = klm.get_flight_details(flights, index = i)
                if details is not None:
                    if details['departure_time'] is not None and details['departure_time'] != 'N/A':
                        flight_id = flight_id_partial + '_' + airliner_site + '_' + details['departure_time']
                        observation_id = f'{flight_id}_{fare_names[j]}'
                    else:
                        if klm.print_ > 0:
                            print('An error has occured while getting flight details')
                        continue
                else:
                    if klm.print_ > 0:
                        print('An error has occured while getting flight details')
                    continue
                if 'KLM' in airliner:
                    flights_details.append(details)
                    fares = klm.advance_to_your_selection_page(flights, index = i, fare_name = fare_names[j])
                    if fares == "Sold Out":
                        if len(flights_fares) > 1 and len(flights_infos) > 1 and len(flights_seats) > 1:
                            sold_out = True
                            fare_sold_out = flights_fares[-2]
                            info_sold_out = flights_infos[-2]
                            seats_sold_out = flights_seats[-2]
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
                                'fares': fare_sold_out,
                                'infos': info_sold_out,
                                'seats': seats_sold_out
                            }
                        else:
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
                                'fares': 'Sold Out',
                                'infos': 'Sold Out',
                                'seats': 'Sold Out',
                            }
                    else:
                        flights_fares.append(fares)
                        klm.advance_to_passenger_form()
                        klm.fill_passenger_form()
                        infos = klm.get_bags_and_info()
                        flights_infos.append(infos)
                        klm.get_to_seats_page()
                        seats = klm.get_seats(fare_name=current_fare_name)
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
                            'fares': fares,
                            'infos': infos,
                            'seats': seats
                        }
                else:
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
                        'fares': 'No information available',
                        'infos': 'No information available',
                        'seats': 'No information available',
                    }

                filename = filename_partial + '_' + fare_name + '.csv'
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

    else:
        if klm.print_ > 0:
            print('No flights found')
        if len(flights_fares) > 1 and len(flights_infos) > 1 and len(flights_seats) > 1:
            sold_out = True
            fare_options_sold_out = flights_fares[-2]
            services_sold_out = flights_infos[-2]
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
        

    if klm.print_ > 2:
        print(flights_details)
        print(flights_fares)
        print(flights_infos)
        print(flights_seats)

    klm.close()

if __name__ == "__main__":
        
    parser = argparse.ArgumentParser(description="Get information about flights page form for KLM")

    parser.add_argument('--origin-name', required=False, help='Origin airport name')
    parser.add_argument('--origin', required=True, help='Origin airport code')
    parser.add_argument('--destination-name', required=False, help='Destination airport name')
    parser.add_argument('--destination', required=True, help='Destination airport code')
    parser.add_argument('--date', required=True, help='Flight date in YYYYY/MM/DD format')

    args = parser.parse_args()

    main(origin_name=args.origin_name, origin_code=args.origin, destination_name=args.destination_name, destination_code=args.destination, date=args.date)
           



            



    



# if __name__ == '__main__':
#     klm = KLM()
#     klm.fill_home_page_form('09/09/2024', 'Amsterdam', 'Zurich')
#     flights = klm.get_flights()
#     print(len(flights))
#     print(klm.get_flight_details(flights, 0))
#     print(klm.advance_to_your_selection_page(flights, 0))
#     klm.advance_to_passenger_form()
#     klm.fill_passenger_form()
#     print(klm.get_bags_and_info())
#     klm.get_to_seats_page()
#     print(klm.get_seats())
#     klm.get_back_to_home_page()
#     time.sleep(5)
#     klm.driver.quit()
#     print('Done')