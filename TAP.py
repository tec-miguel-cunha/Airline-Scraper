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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import chromedriver_autoinstaller
import json
import inputs
import re
from datetime import datetime
import csv

# timeout = inputs.tap_timeout
# timeout_cookies = inputs.tap_timeout_cookies
# timeout_little = inputs.tap_timeout_little
# timeout_implicitly_wait = inputs.tap_timeout_implicitly_wait
# cookies = inputs.tap_cookies
# print_ = inputs.tap_print_

buttons = []

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

mutation_observer_script = """
var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        var popup = document.querySelector('.rtm-overlay');
        if (popup) {
            // Try to close the popup using closeStyle1-sc
            var closeButton1 = popup.querySelector('.close-sc.closeStyle1-sc');
            if (closeButton1) {
                closeButton1.click();
                console.log('Popup closed by closeStyle1-sc.');
            } else {
                // If closeStyle1-sc is not found, try closeStyle2-sc
                var closeButton2 = popup.querySelector('.close-sc.closeStyle2-sc');
                if (closeButton2) {
                    closeButton2.click();
                    console.log('Popup closed by closeStyle2-sc.');
                }
            }
        }
    });
});

// Configuration of the observer to monitor child elements and subtree
var config = { childList: true, subtree: true };

// Start observing the document for DOM changes
observer.observe(document.body, config);
"""

def flatten_dict(d, parent_key='', sep='_'):
    if inputs.tap_print_ > 1:
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
    if inputs.tap_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def flatten_dict_with_na(d, parent_key='', sep='_'):
    if inputs.tap_print_ > 1:
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
    if inputs.tap_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def write_to_csv_row(writer, data, first=False, sold_out=False):
    if inputs.tap_print_ > 1:
        print('Writing to CSV row')
    # Flatten the details and seats data
    if sold_out:
        flattened_data = flatten_dict_with_na(data)
        flattened_data = flatten_dict(flattened_data)
    else:
        flattened_data = flatten_dict(data)
    if first:
        if inputs.tap_print_ > 1:
            print('Writing header row')
        # Write the header row
        header = list(flattened_data.keys())
        writer.writerow(header)

    row = list(flattened_data.values())
    # Write the row to the CSV file
    writer.writerow(row)
    if inputs.tap_print_ > 1:
        print('Wrote flattened data')

def check_and_close_popup(driver):
    if inputs.tap_print_ > 1:
        print('Checking and closing popup')
    try:
        # Check for overlay element
        overlay = WebDriverWait(driver, timeout=inputs.tap_timeout_cookies).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='rtm-overlay']")))
        if overlay:
            # Find and click the close button
            close_button = overlay.find_element(By.CSS_SELECTOR, "[class*='close-sc closeStyle1-sc']")
            if close_button:
                close_button.click()
                if inputs.tap_print_ > 1:
                    print('Overlay closed')
        else:
            if inputs.tap_print_ > 1:
                print('No overlay found')
    except Exception as e:
        if inputs.tap_print_ > 0:
            print(f'Exception occurred: {e}')

def is_element_in_view(driver, element):
    if inputs.tap_print_ > 1:
        print('Checking if element is in view')
    # Check if the element is displayed
    if element.is_displayed():
        if inputs.tap_print_ > 1:
            print('Element is displayed')
        return True
    else:
        # Scroll the element into view
        if inputs.tap_print_ > 1:
            print('Trying to scroll element into view')
        driver.execute_script("arguments[0].scrollIntoView();", element)
        if inputs.tap_print_ > 1:
            print('Scrolled element into view')
        # Check again if the element is displayed after scrolling
        return element.is_displayed()

def check_element_exists_by_ID(driver, id, timeout=inputs.tap_timeout_checks):
    element_exists = False
    if inputs.tap_print_ > 1:
        print(f'Checking if element exists by ID: {id}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.ID, id)))
        if inputs.tap_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.tap_print_ > 0:
            print(f'No element by ID: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_CSS_SELECTOR(driver, css, timeout=inputs.tap_timeout_checks):
    element_exists = False
    if inputs.tap_print_ > 1:
        print(f'Checking if element exists by CSS: {css}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if inputs.tap_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.tap_print_ > 0:
            print(f'No element by CSS Selector: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_TAG_NAME(driver, tag, timeout=inputs.tap_timeout_checks):
    element_exists = False
    if inputs.tap_print_ > 1:
        print(f'Checking if element exists by Tag Name: {tag}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.TAG_NAME, tag)))
        if inputs.tap_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.tap_print_ > 0:
            print(f'No element by Tag Name: {e}')
        element_exists = False
    return element_exists

class TAP:

    # TODO: 
    # - Test sold out flights
    ## - Add button logic to the fill_home_page_form function
    ## - Add button logic to the get_flight_seats function
    ## - Add print and timeout to inputs.py and implement logic
    ## - Add a way to check if the buttons are in view and scroll them into view if they are not

    


    def __init__(self, headless=True):

        self.timeout = inputs.tap_timeout
        self.timeout_cookies = inputs.tap_timeout_cookies
        self.timeout_little = inputs.tap_timeout_little
        self.timeout_implicitly_wait = inputs.tap_timeout_implicitly_wait
        self.cookies = inputs.tap_cookies
        self.print_ = inputs.tap_print_

        self.buttons = []

        if self.print_ > 1:
            print('Initializing TAP')
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = uc.Chrome()
        if self.print_ > 1:
            print('Initialized TAP')
    
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

    def fill_calendar(self, flyout):
        if self.print_ > 1:
            print('Filling calendar')
        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.TAG_NAME, 'app-calendar')))
            if self.print_ > 1:
                print('Calendar loaded successfully')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error waiting for calendar to load: {e}')
        
        date = datetime.strptime(flyout, "%d/%m/%Y")
        
        try:
            formatted_date = date.strftime("%B of %Y")
            aria_label_table_query = f"[aria-label*='{formatted_date}']"
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, aria_label_table_query)))
            table = self.driver.find_element(By.CSS_SELECTOR, aria_label_table_query)
            if self.print_ > 1:    
                print('Table loaded successfully')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error waiting for table to load: {e}')

        try:
            if(date.day < 10):
                day = f'0{date.day}'
            else:
                day = date.day
            aria_label_cell_query = f"[aria-label*='Day {day},']"
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, aria_label_cell_query)))
            cell = table.find_element(By.CSS_SELECTOR, aria_label_cell_query)
            cell.click()
            if self.print_ > 1:
                print('Clicked on cell')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on cell: {e}')
    
    # The error in this function is not returning the correct error in the cookies section, but let's keep it this way for now because it's working
    def fill_home_page_form(self, flyout, orig, dest, adults='1', teens='0', children='0', infants='0'):
        # set url
        url = f'https://www.flytap.com/en-us/'
        # get the page
        self.driver.get(url)
        if self.print_ > 1:    
            print('Opened TAP homepage')
        self.driver.implicitly_wait(self.timeout_implicitly_wait)

        formatted_date = datetime.strptime(flyout, "%Y/%m/%d").strftime("%d/%m/%Y")

        if self.cookies == "not accepted":
            try:
                if check_element_exists_by_ID(self.driver, 'onetrust-accept-btn-handler', timeout = self.timeout_cookies):
                    self.driver.find_element(By.CSS_SELECTOR, "[id*='onetrust-accept-btn-handler']").click()
                    self.cookies = "accepted"
                    if self.print_ > 1:
                        print('Accepted cookies on cookie banner')
                else:
                    if self.print_ > 1:
                        print('No cookies banner found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error accepting cookies: {e}')
                self.fill_home_page_form(flyout, orig, dest)

        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='One way']")))
            self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='One way']").click()
            if self.print_ > 1:
                print('Clicked on One Way')
        except Exception as e:
            if check_element_exists_by_TAG_NAME(self.driver, 'app-stopover-modal'):
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Close dialog']").click()
                    if self.print_ > 1:
                        print('Closed Stopover Modal')
                except Exception as e:
                    if self.print_ > 0:
                        print(f'Error closing Stopover Modal: {e}')
                self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='One way']").click()
                if self.print_ > 1:
                    print('Clicked on One Way')
            else:
                if self.print_ > 0:
                    print(f'Error clicking on One Way: {e}')
                self.fill_home_page_form(flyout, orig, dest)

        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='flight-search-from']")))
            self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").clear()
            self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").send_keys(orig + Keys.RETURN)
            if self.print_ > 1:
                print('Entered origin')
            # Correct this here
            # WebDriverWait(self.driver, timeout=self.timeout).until(lambda d: d.find_element(By.CSS_SELECTOR, "[id*='flight-search-to']").get_attribute('disabled') is None)
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='flight-search-to']")))
            self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-to']").send_keys(dest + Keys.RETURN)
            if self.print_ > 1:
                print('Entered destination')
            self.driver.find_element(By.CSS_SELECTOR, "[class*='form-control bsdatepicker']").send_keys(formatted_date + Keys.RETURN)
            if self.print_ > 1:
                print('Entered departure date')
        except Exception as e:
            if check_element_exists_by_TAG_NAME(self.driver, 'app-stopover-modal'):
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Close dialog']").click()
                    if self.print_ > 1:
                        print('Closed Stopover Modal')
                except Exception as e:
                    if self.print_ > 0:
                        print(f'Error closing Stopover Modal: {e}')
                self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").clear()
                self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").send_keys(orig + Keys.RETURN)
                if self.print_ > 1:
                    print('Entered origin')
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='flight-search-to']")))
                self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-to']").send_keys(dest + Keys.RETURN)
                if self.print_ > 1:
                    print('Entered destination')
                self.driver.find_element(By.CSS_SELECTOR, "[class*='form-control bsdatepicker']").send_keys(flyout + Keys.RETURN)
                if self.print_ > 1:
                    print('Entered departure date')
            else:
                if self.print_ > 0:
                    print(f'Error entering origin, destination or date: {e}')
                self.fill_home_page_form(flyout, orig, dest)

        # Open Search Page
        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Continue to next page to select dates']")))
            self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Continue to next page to select dates']").click()
            if self.print_ > 1:
                print('Clicked on Search Button')
        except Exception as e:
            if check_element_exists_by_TAG_NAME(self.driver, 'app-stopover-modal'):
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Close dialog']").click()
                    if self.print_ > 1:
                        print('Closed Stopover Modal')
                except Exception as e:
                    if self.print_ > 0:
                        print(f'Error closing Stopover Modal: {e}')
                self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Continue to next page to select dates']").click()
                if self.print_ > 1:
                    print('Clicked on Search Button')
            else:
                if self.print_ > 0:
                    print(f'Error clicking on Search Button: {e}')
                self.fill_home_page_form(flyout, orig, dest)

        if self.print_ > 1:
            print('Exiting Fill Form Function')
            print('Going to next page')
        if check_element_exists_by_TAG_NAME(self.driver, 'app-stopover-modal'):
            self.fill_home_page_form(flyout, orig, dest)

    def get_flights(self):
        if self.print_ > 1:
            print('Getting flights')

        flights = []

        try:
            if self.print_ > 1:
                print('Waiting for flights to load')
            if check_element_exists_by_TAG_NAME(self.driver, 'app-flight-result-collapse'):
                # Exclude layovers, so we choose the first element. Could be more explicit.
                # Might work on it later 
                flights_div = self.driver.find_elements(By.TAG_NAME, 'app-flight-result-collapse')[0]
                if self.print_ > 1:
                    print('Flights loaded successfully')
            else:
                if self.print_ > 0:
                    print('No flights available or Error loading flights')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error waiting for flights to load or fetching flights: {e}')


        try:
            if self.print_ > 1:
                print('Getting flight details')
            flights = flights_div.find_elements(By.TAG_NAME, 'app-flight-result')
            if flights != []:
                if self.print_ > 1:
                    print('Flights loaded successfully')
            else:
                if self.print_ > 0:
                    print('No flights available or Error loading flights')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error waiting for flights to load or fetching flights: {e}')
        if self.print_ > 1:
            print('Returning flights')
        return flights
    
    def get_flight_details(self, flight):
        if self.print_ > 1:
            print('Getting flight details')

        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='operated-by']"):
                text_to_split = flight.find_element(By.CSS_SELECTOR, "[class*='operated-by']").text
                words = text_to_split.split()
                remaining_words = words[2:]
                operated_by = ' '.join(remaining_words)
                if self.print_ > 2:
                    print(f'Operated by: {operated_by}')
            else:
                operated_by = 'N/A'
        except Exception as e:
            operated_by = 'N/A'
            if self.print_ > 0:
                print(f'Error getting operated by: {e}')

        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='title-h2']")))
            departure_date_elements = self.driver.find_element(By.CSS_SELECTOR, "[class*='title-h2']")
            departure_date = departure_date_elements.find_elements(By.TAG_NAME, 'strong')[1].text
            if self.print_ > 2:
                print(f'Departure date: {departure_date}')
        except Exception as e:
            departure_date = 'N/A'
            if self.print_ > 0:
                print(f'Error getting departure date: {e}')
        
        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='flight-details__time-location is-departure']")))
            departure_div = flight.find_element(By.CSS_SELECTOR, "[class*='flight-details__time-location is-departure']")
            departure_flyout_times = departure_div.find_element(By.CSS_SELECTOR, "[class*='bold']").text
            if self.print_ > 2:
                print(f'Departure time: {departure_flyout_times}')
        except Exception as e:
            departure_flyout_times = 'N/A'
            if self.print_ > 0:
                print(f'Error getting departure time: {e}')
        
        try:
            arrival_div = flight.find_element(By.CSS_SELECTOR, "[class*='flight-details__time-location is-arrival']")
            arrival_flyout_times = arrival_div.find_element(By.CSS_SELECTOR, "[class*='bold']").text
            if self.print_ > 2:
                print(f'Arrival time: {arrival_flyout_times}')
        except Exception as e:
            arrival_flyout_times = 'N/A'
            if self.print_ > 0:
                print(f'Error getting arrival time: {e}')
        
        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Economy from']"):
                price_economy_element = flight.find_element(By.CSS_SELECTOR, "[aria-label*='Economy from']")
                price_economy = price_economy_element.find_element(By.CSS_SELECTOR, "[class*='price']").text.replace(' USD', '')
                if self.print_ > 2:
                    print(f'Price Economy: {price_economy}')
            else:
                if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Economy for this flight is sold out']"):
                    if self.print_ > 1:
                        print('Economy for this flight is sold out')
                    price_economy = 'Sold Out'
        except Exception as e:
            price_economy = 'N/A'
            if self.print_ > 0:
                print(f'Error getting flight details: {e}')

        try:    
            # WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Executive from']")))
            # price_business_element = flight.find_element(By.CSS_SELECTOR, "[aria-label*='Executive from']")
            # price_business = price_business_element.find_element(By.CSS_SELECTOR, "[class*='price']").text.replace(' USD', '')
            # print(f'Price Business: {price_business}')
            if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Executive from']"):
                price_business_element = flight.find_element(By.CSS_SELECTOR, "[aria-label*='Executive from']")
                price_business = price_business_element.find_element(By.CSS_SELECTOR, "[class*='price']").text.replace(' USD', '')
                if self.print_ > 2:
                    print(f'Price Business: {price_business}')
            else:
                if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Executive for this flight is sold out']"):
                    if self.print_ > 1:
                        print('Executive for this flight is sold out')
                    price_business = 'Sold Out'
        except Exception as e:
            price_business = 'N/A'
            if self.print_ > 0:
                print(f'Error getting flight details: {e}')
        
        details = {
            'date': departure_date,
            'departure_time': departure_flyout_times,
            'arrival_time': arrival_flyout_times,
            'price_economy': price_economy,
            'price_business': price_business       
            }
        
        if self.print_ > 2:
            print(f'Returning flight details {details}')

        return operated_by, details

    def decide_area(self, seat):
        if self.print_ > 1:
            print('Deciding area')
        if(self.driver.execute_script(compare_positions, seat, self.driver.find_element(By.CSS_SELECTOR, "[class*='seat--emergency']"))):
            if self.print_ > 2:
                print('Comfort')
            return 'comfort'
        else:
            if('seat--emergency' in seat.get_attribute("class")):
                if self.print_ > 2:
                    print('Emergency')
                return 'emergency'
            else:
                if self.print_ > 2:
                    print('Standard')
                return 'standard'

    def get_popup_info(self, seat):

        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.ID, 'selectPassenger')))
            if self.print_ > 1:
                print('Popup exists')
            popup = self.driver.find_element(By.ID, 'selectPassenger')
            if self.print_ > 1:
                print('Popup loaded successfully')
            popup_header = self.driver.find_element(By.CSS_SELECTOR, "[class*='select-passenger-header']")
            area = popup_header.find_elements(By.TAG_NAME, 'p')[0].text
            if self.print_ > 2:
                print(f'Area: {area}')
        except Exception as e:
            area = 'N/A'
            if self.print_ > 0:
                print(f'Error getting area: {e}')

        try:
            select_seat_form = popup.find_element(By.CSS_SELECTOR, "[class*='select-passenger-list']")
            price = select_seat_form.find_element(By.CSS_SELECTOR, "[class*='bold']").text.split(' ', 1)[0]
            if self.print_ > 2:
                print(f'Price: {price}')
        except Exception as e:
            price = 'N/A'
            if self.print_ > 0:
                print(f'Error getting price: {e}')

        if not area == 'Executive' and not area == 'Standard':
            try:
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if(not check_element_exists_by_ID(self.driver, 'selectPassenger')):
                    if self.print_ > 1:
                        print('Closed popup')
                else:
                    if self.print_ > 0:
                        print('Popup still open: CORRECT THIS')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error closing popup: {e}')
        
            if(not check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='app-sidebar is-open']")):
                extra_element = self.driver.find_element(By.ID, 'SEAT_1')
                open_seats_button = extra_element.find_element(By.CSS_SELECTOR, "[aria-label*='Open dialog to Choose']")
                check_and_close_popup(self.driver)
                open_seats_button.click()
                if self.print_ > 1:
                    print('Clicked to open seatmap')
                if(check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='app-sidebar is-open']")):
                    if self.print_ > 1:
                        print('Sidebar open successfully')
                    if(check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='seatmap__plane-wrapper']")):
                        if self.print_ > 1:
                            print('Seatmap loaded successfully')
                else:
                    extra_element = self.driver.find_element(By.ID, 'SEAT_1')
                    open_seats_button = extra_element.find_element(By.CSS_SELECTOR, "[aria-label*='Open dialog to Choose']")
                    check_and_close_popup(self.driver)
                    open_seats_button.click()
                    if(check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='app-sidebar is-open']")):
                        if self.print_ > 1:
                            print('Sidebar open successfully')
                        if(check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='seatmap__plane-wrapper']")):
                            if self.print_ > 1:
                                print('Seatmap loaded successfully')
            else:
                if self.print_ > 1:
                    print('Sidebar still open')


        info = {
            'area': area,
            'price': price
        }

        if self.print_ > 2:
            print(info)

        return info
    
    def get_flight_seats(self, flight, fare = "Economy"):
        if self.print_ > 1:
            print('Getting flight seats')
        # TODO: ADD BUSINESS CLASS
        try:
            # economy_button = flight.find_element(By.CSS_SELECTOR, "[aria-label*='Economy from']")
            # business_button = flight.find_element(By.CSS_SELECTOR, "[aria-label*='Executive from']")
            if (fare == "Economy"):
                if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Economy from']"):
                    economy_button = flight.find_element(By.CSS_SELECTOR, "[aria-label*='Economy from']")
                else:
                    if self.print_ > 1:
                        print('Economy fare button does not exist or not clickable')
                    if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Economy for this flight is sold out']"):
                        if self.print_ > 1:
                            print('Economy fare is sold out')
                        return {
                            'fare': fare,
                            'seat_price': 'N/A',
                            'total_seats_available': 'Look at last check for this flight',
                            'total_seats_unavailable': 'Look at last check for this flight',
                            'price_bag': 'N/A',
                            'price_preferred_boarding': 'N/A',
                            'seats_comfort_available': 'Look at last check for this flight',
                            'seats_comfort_unavailable': 'Look at last check for this flight',
                            'seats_emergency_available': 'Look at last check for this flight',
                            'seats_emergency_unavailable': 'Look at last check for this flight',
                            'seats_standard_available': 'Look at last check for this flight',
                            'seats_standard_unavailable': 'Look at last check for this flight',
                            'seats_business_available': 'N/A',
                            'seats_business_unavailable': 'N/A'
                            }
                    elif (is_element_in_view(self.driver, economy_button)):
                        if self.print_ > 1:
                            print('Economy fare button exists')
                    else:
                        if self.print_ > 0:
                            print('Economy fare button is not in view and does not exist')
                        return {'error': 'Economy fare button is not in view and does not exist'}
                if(is_element_in_view(self.driver, economy_button)):
                    if self.print_ > 1:
                        print('Economy fare button exists')
                else:
                    if self.print_ > 0:
                        print('Economy fare button is not in view')
                self.buttons.append(economy_button)
                self.driver.execute_script("arguments[0].click();", economy_button)
            else:
                if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Executive from']"):
                    business_button = flight.find_element(By.CSS_SELECTOR, "[aria-label*='Executive from']")
                else:
                    if self.print_ > 1:
                        print('Executive fare button does not exist or not clickable')
                    if check_element_exists_by_CSS_SELECTOR(flight, "[aria-label*='Executive for this flight is sold out']"):
                        if self.print_ > 1:
                            print('Executive fare is sold out')
                        return {
                            'fare': fare,
                            'seat_price': 'N/A',
                            'total_seats_available': 'Look at last check for this flight',
                            'total_seats_unavailable': 'Look at last check for this flight',
                            'price_bag': 'N/A',
                            'price_preferred_boarding': 'N/A',
                            'seats_comfort_available': 'N/A',
                            'seats_comfort_unavailable': 'N/A',
                            'seats_emergency_available': 'N/A',
                            'seats_emergency_unavailable': 'N/A',
                            'seats_standard_available': 'N/A',
                            'seats_standard_unavailable': 'N/A',
                            'seats_business_available': 'Look at last check for this flight',
                            'seats_business_unavailable': 'Look at last check for this flight',
                            }
                    elif (is_element_in_view(self.driver, business_button)):
                        if self.print_ > 1:
                            print('Business fare button exists')
                    else:
                        if self.print_ > 0:
                            print('Business fare button does not exist and does not exist')
                        return {'error': 'Business fare button is not in view and does not exist'}
                if(is_element_in_view(self.driver, business_button)):
                    if self.print_ > 1:
                        print('Business fare button exists')
                else:
                    if self.print_ > 1:
                        print('Business fare button does not exist')
                self.buttons.append(business_button)
                self.driver.execute_script("arguments[0].click();", business_button)
            if self.print_ > 1:
                print(f'Clicked on {fare} fare')

        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on {fare} fare: {e}')
            return None
        
        try:
            if (fare == "Economy"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Select plus brand']")))
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Select plus brand']")
                if(is_element_in_view(self.driver, submit_button)):
                    if self.print_ > 1:
                        print(f'Select fare button exists: {fare}')
                else:
                    if(not self.click_buttons_in_reverse_order()):
                        if self.print_ > 0:
                            print('Failed to click all buttons')
                        return "Abort"
                    else:
                        if self.print_ > 1:
                            print('WARNING: Buttons hadn\'t been clicked successfully')
                            print('Problem is corrected')
                self.buttons.append(submit_button)
                self.buttons.pop(0)
                submit_button.click()
            else:
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Select executive brand']")))
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Select executive brand']")
                if(is_element_in_view(self.driver, submit_button)):
                    if self.print_ > 1:
                        print(f'Select fare button exists: {fare}')
                else:
                    if(not self.click_buttons_in_reverse_order()):
                        if self.print_ > 0:
                            print('Failed to click select fare button: Aborting')
                        return "Abort"
                    else:
                        if self.print_ > 1:
                            print('WARNING: Buttons hadn\'t been clicked successfully')
                            print('Problem is corrected')
                self.buttons.append(submit_button)
                self.buttons.pop(0)
                submit_button.click()
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on select fare button: {e}')
        
        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.TAG_NAME, 'app-confirm-dialog')))
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Complete this booking now']")))
            confirm_button = self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Complete this booking now']")
            # if(is_element_in_view(self.driver, confirm_button)):
            #     print(f'Confirm button exists: {fare}')
            # else:
            #     if(not self.click_buttons_in_reverse_order()):
            #         print('Failed to click confirm buttons. Aborting')
            #         return "Abort"
            #     else:
            #         print('WARNING: Buttons hadn\'t been clicked successfully')
            #         print('Problem is corrected')
            self.buttons.append(confirm_button)
            self.buttons.pop(0)
            confirm_button.click()
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on confirm button. Trying to fix the problem: {e}')
            try:
                if(not self.click_buttons_in_reverse_order()):
                    if self.print_ > 0:
                        print('Failed to click confirm buttons. Aborting')
                    return "Abort"
                else:
                    if self.print_ > 1:
                        print('WARNING: Buttons hadn\'t been clicked successfully')
                        print('Problem is corrected')
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.TAG_NAME, 'app-confirm-dialog')))
                confirm_button = self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Complete this booking now']")
                self.buttons.append(confirm_button)
                self.buttons.pop(0)
                confirm_button.click()
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error clicking on confirm button. Couldn\'t fix the problem: {e}')
                return "Abort"

        if self.print_ > 1:
            print('Going to next page')

        # Add condition if these elements are not present and go over the previous buttons

        try:
            extras_elements = []
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.ID, 'SEAT_1')))
            extras_elements.append(self.driver.find_element(By.ID, 'SEAT_1'))
            if self.print_ > 1:
                print('Extra seat loaded successfully')
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.ID, 'BAG_1')))
            extras_elements.append(self.driver.find_element(By.ID, 'BAG_1'))
            if self.print_ > 1:
                print('Extra bag loaded successfully')
            if(fare == "Economy"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.ID, 'PREFERRED_BOARDING_1')))
                extras_elements.append(self.driver.find_element(By.ID, 'PREFERRED_BOARDING_1'))
                if self.print_ > 1:
                    print('Extra prefered boarding loaded successfully')
            if self.print_ > 1:
                print('Extras elements loaded successfully')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting extras elements (Seat, Bag and Prefered Boarding): {e}')

        try:
            if self.print_ > 1:
                print('Getting extras values')
            extras_values = ['0', '0', '0']
            for i in range(extras_elements):
                lable_price = extras_elements[i].find_element(By.CSS_SELECTOR, "[class*='label_price']")
                if ('free' in lable_price.text):
                    extras_values[i] = '0'
                else:
                    price = re.findall(r'\d+', lable_price.text)
                    extras_values[i] = price[0] + ',' + price[1]
            if self.print_ > 1:
                print(f'Extras values gotten successfully: {extras_values}')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting extras values (Seat, Bag and Prefered Boarding): {e}')

        try:
            extras_elements[0].find_element(By.CSS_SELECTOR, "[aria-label*='Open dialog to Choose']").click()
            if self.print_ > 1:
                print('Clicked to open seatmap')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking to open seatmap: {e}')

        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='seatmap__plane-wrapper']")))
            seatmap = self.driver.find_element(By.CSS_SELECTOR, "[class*='seatmap__plane-wrapper']")
            if self.print_ > 1:
                print('Seatmap loaded successfully')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error waiting for seatmap to load: {e}')

        comfort = False
        emergency = False
        standard = False
        business = False
        comfort_info = {'area': 'comfort', 'price': '0,00'}
        emergency_info = {'area': 'emergency', 'price': '0,00'}
        standard_info = {'area': 'standard', 'price': '0,00'}
        business_info = {'area': 'business', 'price': '0,00'}
        infos = []
        infos_button = []

        if(fare == "Economy"):
            try:
                total_seats = [0, 0]
                seats_comfort = [0, 0]
                seats_emergency = [0, 0]
                seats_standard = [0, 0]
                seats = seatmap.find_elements(By.TAG_NAME, 'app-seatmap-seat')
                for i in range(len(seats)):
                    area = self.decide_area(seats[i])
                    if(area == 'comfort'):
                        if(not comfort and self.check_seat_availability(seats[i]) == 'available'):
                            infos_button.append(i)
                            comfort = True
                        if(self.check_seat_availability(seats[i]) == 'available'):
                            total_seats[0] += 1
                            seats_comfort[0] += 1
                        else:
                            total_seats[1] += 1
                            seats_comfort[1] += 1
                    else:
                        if(area == 'emergency'):
                            if(not emergency and self.check_seat_availability(seats[i]) == 'available'):
                                infos_button.append(i)
                                emergency = True
                            if(self.check_seat_availability(seats[i]) == 'available'):
                                total_seats[0] += 1
                                seats_emergency[0] += 1
                            else:
                                total_seats[1] += 1
                                seats_emergency[1] += 1
                        else:
                            if(not standard and self.check_seat_availability(seats[i]) == 'available'):
                                infos_button.append(i)
                                standard = True
                            if(self.check_seat_availability(seats[i]) == 'available'):
                                total_seats[0] += 1
                                seats_standard[0] += 1
                            else:
                                total_seats[1] += 1
                                seats_standard[1] += 1
                if self.print_ > 1:
                    print('Seats counted successfully')
                if self.print_ > 2:
                    print(f'Total Seats counted {sum(total_seats)}')
                    print(f'Total Seats breakdown {total_seats}')
                    print(f'Seats Comfort counted {sum(seats_comfort)}')
                    print(f'Seats Comfort breakdown {seats_comfort}')
                    print(f'Seats Emergency counted {sum(seats_emergency)}')
                    print(f'Seats Emergency breakdown {seats_emergency}')
                    print(f'Seats Standard counted {sum(seats_standard)}')
                    print(f'Seats Standard breakdown {seats_standard}')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error counting seats: {e}')

            try:
                if self.print_ > 1:
                    print('Getting seats info')
                for i in range(len(infos_button)):
                    seatmap = self.driver.find_element(By.CSS_SELECTOR, "[class*='seatmap__plane-wrapper']")
                    seats = seatmap.find_elements(By.TAG_NAME, 'app-seatmap-seat')
                    if(is_element_in_view(self.driver, seats[infos_button[i]])):
                        if self.print_ > 1:
                            print(f'Seat {infos_button[i]} is in view')
                    self.click_with_retry(seats[infos_button[i]], retries=10, delay=0.1)
                    if self.print_ > 1:
                        print('Clicked on seat')
                    infos.append(self.get_popup_info(seats[infos_button[i]]))
                if self.print_ > 1:
                    print('Seats info gotten successfully: Economy')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error getting seats info: {e}')
        else:
            try:
                total_seats = [0, 0]
                seats_business = [0, 0]
                seats = seatmap.find_elements(By.TAG_NAME, 'app-seatmap-seat')
                for i in range(len(seats)):
                    if(not business and self.check_seat_availability(seats[i]) == 'available'):
                        infos_button.append(i)
                        business = True
                    if(self.check_seat_availability(seats[i]) == 'available'):
                        total_seats[0] += 1
                        seats_business[0] += 1
                    else:
                        total_seats[1] += 1
                        seats_business[1] += 1
                if self.print_ > 1:
                    print('Seats counted successfully')
                if self.print_ > 2:
                    print(f'Total Seats counted {sum(total_seats)}')
                    print(f'Total Seats breakdown {total_seats}')
                    print(f'Seats Business counted {sum(seats_business)}')
                    print(f'Seats Business breakdown {seats_business}')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error counting seats: {e}')
            
            try:
                if self.print_ > 1:
                    print('Getting seats info')
                self.click_with_retry(seats[infos_button[0]], retries=10, delay=0.1)
                if self.print_ > 1:
                    print('Clicked on seat')
                infos.append(self.get_popup_info(seats[infos_button[0]]))
                if self.print_ > 1:
                    print('Seats info gotten successfully: Business')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error getting seats info: {e}')

        if (fare == "Economy"):
            return {
                'fare': fare,
                'seat_price': infos,
                'total_seats_available': total_seats[0],
                'total_seats_unavailable': total_seats[1],
                'price_bag': extras_values[1],
                'price_preferred_boarding': extras_values[2],
                'seats_comfort_available': seats_comfort[0],
                'seats_comfort_unavailable': seats_comfort[1],
                'seats_emergency_available': seats_emergency[0],
                'seats_emergency_unavailable': seats_emergency[1],
                'seats_standard_available': seats_standard[0],
                'seats_standard_unavailable': seats_standard[1],
                'seats_business_available': 'N/A',
                'seats_business_unavailable': 'N/A'
                }
        else:
            return {
                'fare': fare,
                'seat_price': infos,
                'total_seats_available': total_seats[0],
                'total_seats_unavailable': total_seats[1],
                'price_bag': extras_values[1],
                'price_preferred_boarding': 'N/A',
                'seats_comfort_available': 'N/A',
                'seats_comfort_unavailable': 'N/A',
                'seats_emergency_available': 'N/A',
                'seats_emergency_unavailable': 'N/A',
                'seats_standard_available': 'N/A',
                'seats_standard_unavailable': 'N/A',
                'seats_business_available': seats_business[0],
                'seats_business_unavailable': seats_business[1]
                }
    
    def check_seat_availability(self, seat):
        if self.print_ > 1:
            print('Checking seat availability')
        try:
            seat_class = seat.get_attribute("class")
            if "seat--not-available" in seat_class:
                return 'unavailable'
            else:
                return 'available'
        except Exception as e:
            if self.print_ > 0:
                print(f'Error checking seat availability: {e}')
            return 'unavailable'

    def close(self):
        if self.print_ > 1:
            print('Closing the driver')
        self.driver.close()
        


# test
def main(origin_name, origin_code, destination_name, destination_code, date):

    # create the object
    tap = TAP(headless=True)

    fares = ["Economy", "Business"]

    airliner = 'TAP'
    flights_details = []
    flights_seats = []

    filename_partial = airliner + '_' + time.strftime("%d-%m-%Y") + '_'

    tap.fill_home_page_form(date, origin_code, destination_code)
    flights = tap.get_flights()

    if flights is not None:
        if inputs.tap_print_ > 2:
            print(f'Number of flights: {len(flights)}')
        for i in range(0,len(flights)):
            flight_id = date.replace('/', '-') + '_' + origin_code + '-' + destination_code + '_' + str(i+1)
            if i != 0:
                tap.fill_home_page_form(date, origin_code, destination_code)
                flights = tap.get_flights()
            airliner, details = tap.get_flight_details(flights[i])
            flights_details.append(details)
            if 'Portug' in airliner:
                for fare in fares:
                    sold_out = False
                    filename = filename_partial + fare + '.csv'
                    observation_id = flight_id + '_' + fare
                    file_exists = os.path.isfile(filename)
                    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
                    # Add logic to exclude flights that are sold out
                    if (details['price_' + fare.lower()] == 'Sold Out'):
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if len(flights_seats) > 1:
                            sold_out = True
                            seats_sold_out = flights_seats[-2]
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            data = {
                                'current_time': current_time,
                                'airliner': airliner,
                                'flight_id': flight_id,
                                'observation_id': observation_id,
                                'details': details,
                                'seats': seats_sold_out
                            }
                        else:
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            data = {
                                'current_time': current_time,
                                'airliner': airliner,
                                'flight_id': flight_id,
                                'observation_id': observation_id,
                                'details': details,
                                'seats': "Sold Out"
                            }
                    else:
                        tap.fill_home_page_form(date, origin_code, destination_code)
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        flights = tap.get_flights()
                        seats = tap.get_flight_seats(flights[i], fare)
                        flights_seats.append(seats)
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        data = {
                            'current_time': current_time,
                            'airliner': airliner,
                            'flight_id': flight_id,
                            'observation_id': observation_id,
                            'details': details,
                            'seats': seats
                        }
                    if file_exists and file_not_empty:
                        mode = 'a'
                        first = False
                    else:
                        mode = 'w'
                        first = True
                    with open(filename, mode=mode, newline='') as file:
                        writer = csv.writer(file)
                        write_to_csv_row(writer, data, first, sold_out=sold_out)
                    # else:
                    #     with open(filenames[file_index], mode='a', newline='') as file:
                    #         writer = csv.writer(file)
                    #         write_to_csv_row(writer, data)
            else:
                if inputs.tap_print_ > 1:
                    print('Airliner is not TAP')
                for fare in fares:
                    filename = 'TAP_' + time.strftime("%d-%m-%Y") + '_' + fare + '.csv'
                    observation_id = flight_id + '_' + fare
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    file_exists = os.path.isfile(filename)
                    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    data = {
                        'current_time': current_time,
                        'airliner': airliner,
                        'flight_id': flight_id,
                        'observation_id': observation_id,
                        'details': details,
                        'seats': 'N/A'
                    }
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
        if tap.print_ > 0:
            print('No flights found')
        flight_id = date.replace('/', '-') + '_' + origin_code + '-' + destination_code + '_' + str(1)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'current_time': current_time,
            'airliner': airliner,
            'flight_ID': flight_id,
            'observation_ID': 'N/A',
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

    if inputs.tap_print_ > 2:
        print(flights_details)
        print(flights_seats)

    # close the driver
    tap.close()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Get information about flights page form for TAP")

    parser.add_argument('--origin-name', required=False, help='Origin airport name')
    parser.add_argument('--origin', required=True, help='Origin airport code')
    parser.add_argument('--destination-name', required=False, help='Destination airport name')
    parser.add_argument('--destination', required=True, help='Destination airport code')
    parser.add_argument('--date', required=True, help='Flight date in YYYYY/MM/DD format')

    args = parser.parse_args()

    main(origin_name=args.origin_name, origin_code=args.origin, destination_name=args.destination_name, destination_code=args.destination, date=args.date)
