# import libraries
import os
import sys
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

current_origin = "Lisbon"
current_destination = "Geneva, all airports"
current_flyout_date = "09/09/2024"
current_fare_name = "Economy"

def flatten_dict(d, parent_key='', sep='_'):
    if inputs.input_print_ > 1:
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
    if inputs.input_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def write_to_csv_row(writer, data, first=False):
    if inputs.input_print_ > 1:
        print('Writing to CSV row')
    # Flatten the details and seats data
    flattened_data = flatten_dict(data)
    if first:
        if inputs.input_print_ > 1:
            print('Writing header row')
        # Write the header row
        header = list(flattened_data.keys())
        writer.writerow(header)

    row = list(flattened_data.values())
    # Write the row to the CSV file
    writer.writerow(row)
    if inputs.input_print_ > 1:
        print('Wrote flattened data')

def check_and_close_popup(driver):
    if inputs.input_print_ > 1:
        print('Checking and closing popup')
    try:
        # Check for overlay element
        overlay = WebDriverWait(driver, timeout=inputs.input_timeout_cookies).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='rtm-overlay']")))
        if overlay:
            # Find and click the close button
            close_button = overlay.find_element(By.CSS_SELECTOR, "[class*='close-sc closeStyle1-sc']")
            if close_button:
                close_button.click()
                if inputs.input_print_ > 1:
                    print('Overlay closed')
        else:
            if inputs.input_print_ > 1:
                print('No overlay found')
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'Exception occurred: {e}')

def is_element_in_view(driver, element):
    if inputs.input_print_ > 1:
        print('Checking if element is in view')
    # Check if the element is displayed
    if element.is_displayed():
        if inputs.input_print_ > 1:
            print('Element is displayed')
        return True
    else:
        # Scroll the element into view
        if inputs.input_print_ > 1:
            print('Trying to scroll element into view')
        driver.execute_script("arguments[0].scrollIntoView();", element)
        if inputs.input_print_ > 1:
            print('Scrolled element into view')
        # Check again if the element is displayed after scrolling
        return element.is_displayed()

def check_element_exists_by_ID(driver, id, timeout=inputs.input_timeout_checks):
    element_exists = False
    if inputs.input_print_ > 1:
        print(f'Checking if element exists by ID: {id}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.ID, id)))
        if inputs.input_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'No element by ID: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_CSS_SELECTOR(driver, css, timeout=inputs.input_timeout_checks):
    element_exists = False
    if inputs.input_print_ > 1:
        print(f'Checking if element exists by CSS: {css}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if inputs.input_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
        if inputs.input_print_ > 1:
            print('Element exists')
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'No element by CSS Selector: {e}')
        element_exists = False
    return element_exists

def check_element_NOT_exists_by_CSS_SELECTOR(driver, css, timeout=inputs.input_timeout_checks):
    element_not_exists = False
    if inputs.input_print_ > 1:
        print(f'Checking if element not exists by CSS: {css}')
    try:
        WebDriverWait(driver, timeout=timeout).until_not(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if inputs.input_print_ > 1:
            print("Passed WebDriverWait")
        element_not_exists = True
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'Element exists by CSS Selector: {e}')
        element_not_exists = False
    return element_not_exists

def check_element_exists_by_TAG_NAME(driver, tag, timeout=inputs.input_timeout_checks):
    element_exists = False
    if inputs.input_print_ > 1:
        print(f'Checking if element exists by Tag Name: {tag}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.TAG_NAME, tag)))
        if inputs.input_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'No element by Tag Name: {e}')
        element_exists = False
    return element_exists

def check_and_wait_for_URL(driver, url, timeout=inputs.input_timeout):
    if inputs.input_print_ > 1:
        print(f'Checking and waiting for URL: {url}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.url_to_be(url))
        if inputs.input_print_ > 1:
            print("Passed WebDriverWait")
        return True
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'URL not found: {e}')
        return False

class SwissAir:

    def __init__(self, headless=True):

        self.timeout = inputs.input_timeout
        self.timeout_cookies = inputs.input_timeout_cookies
        self.timeout_little = inputs.input_timeout_little
        self.timeout_implicitly_wait = inputs.input_timeout_implicitly_wait
        self.print_ = inputs.input_print_
        self.retries = inputs.swiss_retries
        self.cookies = 'not accepted'
        self.GDPR = 'not accepted'
        self.closed_popup_cabin_bags = False
        self.new_tab_opened = False
        self.closed_fares_overlay = False
        self.searched = False

        self.buttons = []

        if self.print_ > 1:
            print('Initializing SwissAir')
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = uc.Chrome()
        if self.print_ > 1:
            print('Initialized SwissAir')

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
            for attempt in range(self.retries):
                if self.print_ > 3:
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

    def get_element_by_CSS_SELECTOR(self, element, css, timeout=inputs.input_timeout_checks):
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

    def fill_home_page_form(self, flyout=current_flyout_date, orig=current_origin, dest=current_destination, adults='1', teens='0', children='0', infants='0'):
        if self.print_ > 1:
            print('Entering Fill Form Function')
        # set url
        url = f'https://www.swiss.com/'
        # get the page
        self.driver.get(url)
        if self.print_ > 1:    
            print('Opened SwissAir homepage')
        self.driver.implicitly_wait(self.timeout_implicitly_wait)

        if self.GDPR == 'not accepted':
            try:
                if self.print_ > 1:
                    print('Trying to close GDPR popup')
                if check_element_exists_by_ID(self.driver, '__tealiumGDPRcpPrefs'):
                    gdpr_popup = self.driver.find_element(By.ID, '__tealiumGDPRcpPrefs')
                    if self.print_ > 1:
                        print('Found GDPR popup')
                    if check_element_exists_by_ID(gdpr_popup, 'cm-acceptAll'):
                        accept_button = gdpr_popup.find_element(By.ID, 'cm-acceptAll')
                        self.click_with_retry(accept_button)
                        if self.print_ > 1:
                            print('Clicked accept button')
                        self.GDPR = 'accepted'
                    else:
                        if self.print_ > 1:
                            print('No accept button found')
                else:
                    if self.print_ > 1:
                        print('No GDPR popup found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error closing GDPR popup: {e}')

        try:
            if self.print_ > 1:
                print('Trying to close popup')
            if check_element_exists_by_CSS_SELECTOR(self.driver, '[role="dialog"]'):
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if self.print_ > 1:
                    print('Closed popup')
            else:
                if self.print_ > 1:
                    print('No popup found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to close popup: {e}')
        
        time.sleep(2)
        
        try:
            if self.print_ > 1:
                print('Trying to close login popup')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='login-flag-modal-container']"):
                # Trying to close login popup
                self.driver.find_element(By.CSS_SELECTOR, "[class*='login-flag-modal-container']").send_keys(Keys.ESCAPE)
                if self.print_ > 1:
                    print('Closed login popup')
            else:
                if self.print_ > 1:
                    print('No login popup found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to close login popup: {e}')

        if not self.searched:
            try:
                if self.print_ > 1:
                    print('Trying to open one way menu')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[aria-label='open menu']"):
                    self.driver.find_element(By.CSS_SELECTOR, "[aria-label='open menu']").click()
                    if self.print_ > 1:
                        print('Opened one way menu')
                else:
                    if self.print_ > 1:
                        print('No one way menu found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to open one way menu: {e}')

            try:
                if self.print_ > 1:
                    print('Trying to click one way button')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='selectable-result-list']"):
                    ways_list = self.driver.find_element(By.CSS_SELECTOR, "[class*='selectable-result-list']")
                    self.click_with_retry(ways_list.find_elements(By.TAG_NAME, 'li')[1])
                    if self.print_ > 1:
                        print('Clicked one way option')
                else:
                    if self.print_ > 1:
                        print('No one way button found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to click one way button: {e}')

            try:
                if self.print_ > 1:
                    print('Trying to enter origin')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[id*='flightSegments[0].originCode']"):
                    origin = self.driver.find_element(By.CSS_SELECTOR, "[id*='flightSegments[0].originCode']")
                    backspaces = len(origin.get_attribute('value')) + 1
                    origin.send_keys(backspaces * Keys.BACKSPACE)
                    origin.send_keys(orig)
                    time.sleep(1)
                    origin.send_keys(Keys.RETURN)
                    if self.print_ > 1:
                        print('Entered origin')
                else:
                    if self.print_ > 1:
                        print('No origin field found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to enter origin: {e}')
            
            try:
                if self.print_ > 1:
                    print('Trying to enter destination')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[id*='flightSegments[0].destinationCode']"):
                    destination = self.driver.find_element(By.CSS_SELECTOR, "[id*='flightSegments[0].destinationCode']")
                    destination.send_keys(dest)
                    time.sleep(1)
                    destination.send_keys(Keys.RETURN)
                    if self.print_ > 1:
                        print('Entered destination')
                else:
                    if self.print_ > 1:
                        print('No destination field found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to enter destination: {e}')

            try:
                if self.print_ > 1:
                    print('Trying to enter date')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[name='flightQuery.flightSegments[0].travelDatetime']"):
                    date_input = self.driver.find_element(By.CSS_SELECTOR, "[name='flightQuery.flightSegments[0].travelDatetime']")
                    self.click_with_retry(date_input)
                    if self.print_ > 1:
                        print('Clicked on date input')
                    if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='DayPicker_transitionContainer']"):
                        calendar = self.driver.find_element(By.CSS_SELECTOR, "[class*='DayPicker_transitionContainer']")
                        if self.print_ > 1:
                            print(f'Found calendar: {calendar}')
                        parsed_date = datetime.strptime(flyout, "%d/%m/%Y")
                        formatted_date = parsed_date.strftime("%d %B %Y")
                        if check_element_exists_by_CSS_SELECTOR(self.driver, f"[aria-label*='{formatted_date}']", timeout=self.timeout):
                            date = self.get_element_by_CSS_SELECTOR(self.driver, f"[aria-label*='{formatted_date}']", timeout=self.timeout)
                            self.click_with_retry(date)
                            if self.print_ > 1:
                                print('Clicked on date')
                        else:
                            if self.print_ > 1:
                                print('No date found')
                    else:
                        if self.print_ > 1:
                            print('No calendar found')
                else:
                    if self.print_ > 1:
                        print('No date input field found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to enter date: {e}')

            try:
                if self.print_ > 1:
                    print('Trying to click continue button')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='calendar-footer-continue-button']"):
                    continue_button = self.driver.find_element(By.CSS_SELECTOR, "[class*='calendar-footer-continue-button']")
                    self.click_with_retry(continue_button)
                    if self.print_ > 1:
                        print('Clicked continue button')
                else:
                    if self.print_ > 1:
                        print('No continue continue found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to click continue button: {e}')
            
            try:
                if self.print_ > 1:
                    print('Trying to click submit button')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[type*='submit']"):
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, "[type*='submit']")
                    self.click_with_retry(submit_button)
                    if self.print_ > 1:
                        print('Clicked submit button')
                else:
                    if self.print_ > 1:
                        print('No submit button found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Exception occurred trying to click submit button: {e}')
        else:
            try:
                if self.print_ > 1:
                    print('Clicking on recent searches')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='recent-searches-item']"):
                    self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='recent-searches-item']"))
                    if self.print_ > 1:
                        print('Clicked on recent searches')
                else:
                    if self.print_ > 1:
                        print('No recent searches found')
                    self.searched = False
                    self.fill_home_page_form(flyout, orig, dest)
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error clicking on recent searches: {e}')

        if self.print_ > 1:
            print('Exiting fill home page form function')
            print('Going to next page')

        self.searched = True

    def get_flights(self):

        if self.print_ > 1:
            print('Getting flights')

        try:
            if self.print_ > 1:
                print('Trying to close loading overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='loading loading-container']"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[class*='loading loading-container']")))
                if self.print_ > 1:
                    print('Closed loading overlay')
            else:
                if self.print_ > 1:
                    print('No loading overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing loading overlay: {e}')  

        page_url = 'https://shop.swiss.com/booking/availability/0'
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
            if check_element_exists_by_TAG_NAME(self.driver, 'mat-accordion', timeout=self.timeout):
                flights_div = self.driver.find_element(By.TAG_NAME, 'mat-accordion')
                if self.print_ > 1:
                    print('Found flights div')
                if check_element_exists_by_TAG_NAME(flights_div, 'refx-upsell-premium-row-pres'):
                    flights_temp = flights_div.find_elements(By.TAG_NAME, 'refx-upsell-premium-row-pres')
                    if self.print_ > 1:
                        print(f'Found {len(flights_temp)} flights')
                    for i in range(len(flights_temp)):
                        if self.print_ > 1:
                            print(f'Checking flight {i}')
                        if check_element_NOT_exists_by_CSS_SELECTOR(flights_temp[i], "[class*='bound-nb-stop ']", self.timeout_little):
                            flights.append(flights_temp[i])
                            if self.print_ > 1:
                                print('Added flight')
                        else:
                            if self.print_ > 1:
                                print('Flight has stops. Not adding. The ones following will also have stops')
                            break
                else:
                    if self.print_ > 1:
                        print('No flights found')
                    self.driver.refresh()
                    time.sleep(5)
                    flights = self.get_flights()
            else:
                if self.print_ > 1:
                    print('No flights div found')
                self.driver.refresh()
                time.sleep(5)
                flights = self.get_flights()
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to get flights: {e}')
            # Refresh the page then wait
            self.driver.refresh()
            time.sleep(5)
            flights = self.get_flights()

        if self.print_ > 1:
            print('Returning flights')
        
        return flights
    
    def get_flight_details(self, flights, index, repeat=False):

        if self.print_ > 1:
            print(f'Getting flight details for flight {index}')
        
        if repeat:
            flight = self.get_flights()[index]
        else:
            flight = flights[index]

        page_url = 'https://shop.swiss.com/booking/availability/0'
        
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
            if check_element_exists_by_CSS_SELECTOR(flight, "[class='operating-airline-name']"):
                airliner = flight.find_element(By.CSS_SELECTOR, "[class='operating-airline-name']").text
                if self.print_ > 1:
                    print(f'Airline: {airliner}')
            else:
                if self.print_ > 1:
                    print('No airliner found')
                airliner = 'N/A'
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to get airliner: {e}')
            airliner = 'N/A'

        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='bound-departure-datetime']"):
                departure_flyout_time = flight.find_element(By.CSS_SELECTOR, "[class*='bound-departure-datetime']").text
                if self.print_ > 1:
                    print(f'Departure: {departure_flyout_time}')
            else:
                if self.print_ > 1:
                    print('No departure time found')
                departure_flyout_time = 'N/A'
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='bound-arrival-datetime']"):
                arrival_flyout_time = flight.find_element(By.CSS_SELECTOR, "[class*='bound-arrival-datetime']").text
                if self.print_ > 1:
                    print(f'Arrival: {arrival_flyout_time}')
            else:
                if self.print_ > 1:
                    print('No arrival time found')
                arrival_flyout_time = 'N/A'
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to get departure and arrival times: {e}')
            departure_flyout_time = 'N/A'
            arrival_flyout_time = 'N/A'

        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='flight-card-button-section']"):
                buttons_section = flight.find_element(By.CSS_SELECTOR, "[class*='flight-card-button-section']")
                if self.print_ > 1:
                    print('Found buttons section')
                fares_buttons = buttons_section.find_elements(By.XPATH, "./*")
                if len(fares_buttons) == 2:
                    if self.print_ > 1:
                        print('Found 2 buttons')
                for i in range(len(fares_buttons)):
                    if fares_buttons[i].tag_name == 'button':
                        if i == 0:
                            price_economy = fares_buttons[i].find_element(By.CSS_SELECTOR, "[class*='price-amount']").text
                            if self.print_ > 2:
                                print(f'Economy: {price_economy}')
                        else:
                            price_business = fares_buttons[i].find_element(By.CSS_SELECTOR, "[class*='price-amount']").text
                            if self.print_ > 2:
                                print(f'Business: {price_business}')
                    else:
                        if fares_buttons[i].tag_name == 'div' and 'not-available' in fares_buttons[i].get_attribute('class'):
                            if i == 0:
                                price_economy = 'Sold Out'
                                if self.print_ > 1:
                                    print('Economy: Sold Out')
                            else:
                                price_business = 'Sold Out'
                                if self.print_ > 1:
                                    print('Business: Sold Out')
                        else:
                            if i == 0:
                                price_economy = 'N/A'
                                if self.print_ > 1:
                                    print('Economy: Not Found')
                            else:
                                price_business = 'N/A'
                                if self.print_ > 1:
                                    print('Business: Not Found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to get prices: {e}')
            price_economy = 'N/A'
            price_business = 'N/A'
            

        if self.print_ > 1:
            print('Returning flight details')

        return airliner, {
            'departure_flyout_time': departure_flyout_time,
            'arrival_flyout_time': arrival_flyout_time,
            'price_economy': price_economy,
            'price_business': price_business
        }
    
    def advance_to_your_selection_page(self, flights, index, fare_name=current_fare_name, repeat=False, retries=3):

        if self.print_ > 1:
            print(f'Entering function to advance to form page for flight: {index} and fare: {fare_name} and repeat: {repeat}')
        
        if repeat:
            flight = self.get_flights()[index]
        else:
            flight = flights[index]

        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class='flight-card-button-section ng-star-inserted']"):
                buttons_section = flight.find_element(By.CSS_SELECTOR, "[class='flight-card-button-section ng-star-inserted']")
                if self.print_ > 1:
                    print('Found buttons section')
                fares_buttons = buttons_section.find_elements(By.XPATH, "./*")
                if len(fares_buttons) == 2:
                    if self.print_ > 1:
                        print('Found 2 buttons')
                for i in range(len(fares_buttons)):
                    if fare_name == 'Economy' and 'eco' in fares_buttons[i].get_attribute('data-fare-family-group'):
                        if self.print_ > 1:
                            print('Clicking on economy fare')
                        self.click_with_retry(fares_buttons[i])
                    elif fare_name == 'Business' and 'business' in fares_buttons[i].get_attribute('data-fare-family-group'):
                        if self.print_ > 1:
                            print('Clicking on business fare')
                        self.click_with_retry(fares_buttons[i])
                    else:
                        if self.print_ > 1:
                            print('Not the fare we are looking for')
                        continue
            else:
                if self.print_ > 1:
                    print('No buttons section found')
                self.driver.refresh()
                time.sleep(5)
                fares = self.advance_to_your_selection_page(flights, index, fare_name, repeat=True)
                if len(fares) != 0:
                    return fares
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to advance to form page: {e}')
        
        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='mat-expansion-panel-content']") and is_element_in_view(self.driver, flight.find_element(By.CSS_SELECTOR, "[class*='mat-expansion-panel-content']")):
                panel = flight.find_element(By.CSS_SELECTOR, "[class*='mat-expansion-panel-content']")
                if self.print_ > 1:
                    print('Found panel')
            else:
                if self.print_ > 1:
                    print('No panel found')
                if retries > 0:
                    fares = self.advance_to_your_selection_page(flights, index, fare_name, repeat=True, retries=retries-1)
                    if len(fares) != 0:
                        return fares
                else:
                    if self.print_ > 0:
                        print('Failed to find panel')
                    return "Abort"
                
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to find panel: {e}')

        try:
            if self.print_ > 1:
                print('Finding flight fares list')
            if check_element_exists_by_TAG_NAME(flight, 'ul'):
                ul = flight.find_element(By.TAG_NAME, 'ul')
                if self.print_ > 1:
                    print('Found ul')
            else:
                if self.print_ > 1:
                    print('No ul found')
                fares = self.advance_to_your_selection_page(flights, index, fare_name, repeat=True)
                if len(fares) != 0:
                    return fares
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding ul: {e}')

        try:
            if self.print_ > 1:
                print('Finding flight fares')
            if check_element_exists_by_TAG_NAME(ul, 'li'):
                fares_divs = ul.find_elements(By.XPATH, "./*")
                if self.print_ > 1:
                    print('Found li')
            else:
                if self.print_ > 1:
                    print('No li found')
                fares = self.advance_to_your_selection_page(flights, index, fare_name, repeat=True)
                if len(fares) != 0:
                    return fares
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding li: {e}')

        fares = []

        try:
            if self.print_ > 1:
                print('Finding fares')
            for i in range(len(fares_divs)):
                if self.print_ > 1:
                    print(f'Checking fare {i}')
                if check_element_exists_by_CSS_SELECTOR(fares_divs[i], "[class*='price-card-title-label']"):
                    fare_name = fares_divs[i].find_element(By.CSS_SELECTOR, "[class*='price-card-title-label']").text
                    if self.print_ > 1:
                        print(f'Fare: {fare_name}')
                else:
                    if self.print_ > 1:
                        print('No fare name found')
                    fare_name = 'N/A'
                if check_element_exists_by_CSS_SELECTOR(fares_divs[i], "[class*='price-amount']"):
                    fare_price = fares_divs[i].find_element(By.CSS_SELECTOR, "[class*='price-amount']").text
                    if self.print_ > 1:
                        print(f'Price: {fare_price}')
                else:
                    if self.print_ > 1:
                        print('No fare price found')
                    fare_price = 'N/A'
                if i == 0:
                    button_to_click = fares_divs[i].find_element(By.CSS_SELECTOR, "[id*='selectFare']")
                    if self.print_ > 1:
                        print('Found button to click')
                fare = {
                    'name': fare_name,
                    'price': fare_price
                }
                fares.append(fare)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding fares: {e}')

        try:
            if self.print_ > 1:
                print('Clicking on button')
            self.click_with_retry(button_to_click)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on button: {e}')

        if self.print_ > 1:
            print('Going to next page')
        
        return fares

    def advance_to_passenger_form_page(self, flights, index, repeat=False):

        if self.print_ > 1:
            print('Entering function to advance to passenger form page')

        try:
            if self.print_ > 1:
                print('Trying to close loading overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='loading loading-container']"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[class*='loading loading-container']")))
                if self.print_ > 1:
                    print('Closed loading overlay')
            else:
                if self.print_ > 1:
                    print('No loading overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing loading overlay: {e}')  

        page_url = 'https://shop.swiss.com/booking/cart'

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout*1.5):
                if self.print_ > 1:
                    print('In your selection page')
            else:
                if self.print_ > 1:
                    print('Not in your selection page')
                for i in range(self.retries):
                    self.driver.refresh()
                    flights = self.advance_to_your_selection_page(flights, index, repeat=True)
                    if flights == "Abort":
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to your selection page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to your selection page: {e}')
            return "Abort"

        try:
            if self.print_ > 1:
                print('Clicking on continue button at Cart Page')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='next-step-button']", timeout=self.timeout*1.5):
                continue_button = self.driver.find_element(By.CSS_SELECTOR, "[class*='next-step-button']")
                self.click_with_retry(continue_button)
                if self.print_ > 1:
                    print('Clicked on continue button')
            else:
                if self.print_ > 1:
                    print('No continue button found')

        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on continue button: {e}')
        
        if self.print_ > 1:
            print('Exiting advance to form page function')
            print('Going to next page')

        return fares
    
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
                text_input.send_keys(input)
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

    def fill_passenger_form(self):

        if self.print_ > 1:
            print('Filling passenger form')

        # Try to get of the loading overlay
        try:
            if self.print_ > 1:
                print('Trying to close loading overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='loading loading-container']"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[class*='loading loading-container']")))
                if self.print_ > 1:
                    print('Closed loading overlay')
            else:
                if self.print_ > 1:
                    print('No loading overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing loading overlay: {e}')  
        
        page_url = 'https://shop.swiss.com/booking/traveler/0'

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In passenger form page')
            else:
                if self.print_ > 1:
                    print('Not in passenger form page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.advance_to_passenger_form_page()
                    if state == 'Abort':
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to passenger form page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to passenger form page: {e}')
            return "Abort"

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='mat-tooltip-trigger']"):
                form_title_field = self.driver.find_element(By.CSS_SELECTOR, "[class*='mat-tooltip-trigger']")
                div_to_click = form_title_field.find_element(By.CSS_SELECTOR, "[class*='mat-form-field-flex']")
                self.click_with_retry(div_to_click)
                if self.print_ > 1:
                    print('Clicked on form title field to open dropdown')
                if check_element_exists_by_ID(self.driver, 'mat-option-284'):
                    self.click_with_retry(self.driver.find_element(By.ID, 'mat-option-284'))
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
            if self.driver.current_url != 'https://shop.swiss.com/booking/cart':
                self.fill_passenger_form()
            else:
                self.fill_passenger_form()
            
        try:
            if self.print_ > 1:
                print('Filling text fields')
            self.fill_text_input_fields("[formcontrolname='firstName']", 'Miguel', tab=True)
            self.fill_text_input_fields("[formcontrolname='lastName']", 'Cunha')
            self.fill_text_input_fields("[id*='-0email']", 'micascunha@hotmail.com', tab=True)
            self.fill_text_input_fields("[id*='phoneItem-0phoneCountryCode']", '+351', tab=True)
            self.driver.switch_to.active_element.send_keys('912345678')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error filling text fields: {e}')
        
        # try:
        #     if self.print_ > 1:
        #         print('Filling GDPR Field')
        #     if check_element_exists_by_ID(self.driver, 'gdprConsent-input'):
        #         gdpr_checkbox = self.driver.find_element(By.ID, 'gdprConsent-input')
        #         self.click_with_retry(gdpr_checkbox)
        #         if self.print_ > 1:
        #             print('Clicked on GDPR checkbox')
        #     else:
        #         if self.print_ > 1:
        #             print('No GDPR checkbox found')
        # except Exception as e:
        #     if self.print_ > 0:
        #         print(f'Error filling GDPR checkbox: {e}')

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

    def get_bags_and_info(self, fare_name):

        if self.print_ > 1:
            print('Getting bags and info')

        try:
            if self.print_ > 1:
                print('Waiting for loading to finish')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='loading loading-container']"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[class*='loading loading-container']")))
                if self.print_ > 1:
                    print('Loading finished')
            else:
                if self.print_ > 1:
                    print('No loading found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error waiting for loading to finish: {e}')

        page_url = 'https://shop.swiss.com/booking/cart'

        try:
            abort = False
            if check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                if self.print_ > 1:
                    print('In baggage and info page')
            else:
                if self.print_ > 1:
                    print('Not in baggage and info page')
                for i in range(self.retries):
                    self.driver.refresh()
                    state = self.fill_passenger_form()
                    if state == 'Abort':
                        return "Abort"
                    if not check_and_wait_for_URL(self.driver, page_url, timeout=self.timeout):
                        abort = True
                        break
                if abort:
                    if self.print_ > 0:
                        print('Failed to get to baggage and info page')
                    return "Abort"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting to baggage and info page: {e}')
            return "Abort"

        try:
            if self.print_ > 1:
                print('Finding elements of services info')
            if check_element_exists_by_TAG_NAME(self.driver, 'refx-service-catalog-pres', timeout=self.timeout):
                services_div = self.driver.find_element(By.TAG_NAME, 'refx-service-catalog-pres')
                if self.print_ > 1:
                    print('Found services div')
                ul = services_div.find_element(By.TAG_NAME, 'ul')
                if self.print_ > 1:
                    print('Found ul')
                services = ul.find_elements(By.XPATH, "./*")
                if self.print_ > 1:
                    print('Found li')
            else:
                if self.print_ > 1:
                    print('No services div found')
                services_info = self.get_bags_and_info(fare_name)
                if len(services_info) != 0:
                    return services_info
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
                    if fare_name == 'Economy' and i == 1: # A problem might come here due to the name needing to be in the same language as the website
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
                    if fare_name == 'Business' and i == 1: # A problem might come here due to the name needing to be in the same language as the website
                        seats_button = services[i].find_element(By.CSS_SELECTOR, "[class*='category-add-service']")
                        if self.print_ > 1:
                            print('Found seats button')
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
        try:
            if self.print_ > 1:
                print('Checking seat availability')
            seat_class = seat.get_attribute("class")
            seat_aria_label = seat.get_attribute("aria-label")
            if self.print_ > 3:
                print(f'Seat class: {seat_class}')
                print(f'Seat aria label: {seat_aria_label}')
            if "not available" in seat_class or "occupied" in seat_class or "blocked" in seat_class:
                return '', 'unavailable'
            else:
                if "Preferred Zone Seat" in seat_aria_label:
                    return 'preferred', 'available'
                elif "Extra Legroom Seat" in seat_aria_label:
                    return 'extra', 'available'
                elif "Classic Seat" in seat_aria_label:
                    return 'classic', 'available'
                else:
                    return '', 'unavailable'
        except Exception as e:
            print(f'Error checking seat {seat.get_attribute("title")} availability: {e}')
    
    def get_flight_seats(self, fare_name):

        if self.print_ > 1:
            print('Getting seats')

        try:
            if self.print_ > 1:
                print('Trying to close loading overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='loading loading-container']"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[class*='loading loading-container']")))
                if self.print_ > 1:
                    print('Closed loading overlay')
            else:
                if self.print_ > 1:
                    print('No loading overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing loading overlay: {e}')  

        page_url = "https://shop.swiss.com/booking/seatmap/ST1"

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
                    services_info = self.get_bags_and_info(fare_name)
                    if services_info == 'Abort':
                        return 'Abort'
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
                print('Finding seats div')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[id*='svg-container']", timeout=self.timeout):
                seatmap = self.driver.find_element(By.CSS_SELECTOR, "[id*='svg-container']")
                if self.print_ > 1:
                    print('Found seatmap')
            else:
                if self.print_ > 1:
                    print('No seatmap found')
                time.sleep(2)
                self.get_flight_seats(fare_name)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding seatmap: {e}')

        time.sleep(3)
        
        try:
            if self.print_ > 1:
                print('Finding seats')
            if check_element_exists_by_CSS_SELECTOR(seatmap, "[class*='Seat_']"):
                seats = seatmap.find_elements(By.CSS_SELECTOR, "[class*='Seat_']")
                if self.print_ > 1:
                    print('Found seats')
                seats = [seat for seat in seats if seat.get_attribute('aria-label') != '']
                seat_pattern = re.compile(r'Seat_[0-9]')
                seats = [seat for seat in seats if any(seat_pattern.match(seat.get_attribute('class')))]
            else:
                if self.print_ > 1:
                    print('No seats found')
                time.sleep(2)
                self.get_flight_seats(fare_name)
        except Exception as e:
            if self.print_ > 0:
                print(f'Error finding seats: {e}')

        total_seats = [0, 0]
        seats_info = []
        if fare_name == 'Economy':
            names = ['Preferred Zone Seat', 'Extra Legroom Seat', 'Classic Seat']
            for i in range(len(names)):    
                seats_info.append({'name': names[i], 'price': 'N/A', 'available_seats': 0, 'unavailable_seats': 0})
            try:
                if self.print_ > 1:
                    print('Getting seat prices')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='seat-type-content']"):
                    seat_type_overviews = self.driver.find_elements(By.CSS_SELECTOR, "[class*='seat-type-content']")
                    for i in range(len(seat_type_overviews)):
                        if check_element_exists_by_CSS_SELECTOR(seat_type_overviews[i], "[class*='price-amount']"):
                            price = seat_type_overviews[i].find_element(By.CSS_SELECTOR, "[class*='price-amount']").text
                            seats_info[i]['price'] = price.replace('.', ',')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error getting seat prices: {e}')      
        else:
            names = ['Business']
            for i in range(len(names)):
                seats_info.append({'name': names[i], 'price': 'N/A', 'available_seats': 0, 'unavailable_seats': 0})
            seats_info[0]['price'] = '0'
        preferred = False
        extra_legroom = False
        classic = False

        try:
            if self.print_ > 1:
                print(f'Iterating over seats: len = {len(seats)}')
            for i in range(len(seats)):
                zone, availability = self.check_seat_availability(seats[i])
                if availability == 'available':
                    total_seats[0] += 1
                    if fare_name == 'Economy':
                        if zone == 'preferred':
                            seats_info[0]['available_seats'] += 1 
                            preferred = True
                        elif zone == 'extra':
                            seats_info[1]['available_seats'] += 1
                            extra_legroom = True
                        else:
                            seats_info[2]['available_seats'] += 1
                            classic = True
                    else:
                        seats_info[0]['available_seats'] += 1
                else:
                    total_seats[1] += 1
                    if fare_name == 'Economy':
                        if not extra_legroom and not classic:
                            seats_info[0]['unavailable_seats'] += 1
                        elif not classic:
                            seats_info[1]['unavailable_seats'] += 1
                        else:
                            seats_info[2]['unavailable_seats'] += 1
                    else:
                        seats_info[0]['unavailable_seats'] += 1
            if self.print_ > 1:
                print('Iterated over seats')
        except Exception as e:
            if self.print_ > 1:
                print(f'Error getting seats: {e}')

        if self.print_ > 1:
            print('Returning seats')

        return seats_info

    def close(self):
        self.driver.quit()

if __name__ == '__main__':
    # create the object
    swiss = SwissAir(headless=True)

    filename = 'SwissAir_' + time.strftime("%d-%m-%Y") + '.csv'
    file_exists = os.path.isfile(filename)
    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
    fares = ["Economy", "Business"]
    flights_details = []
    flights_seats = []

    # Loop here for the flights inputs

    current_origin = 'Lisbon'
    current_destination = 'Geneva, all airports'
    current_flyout_date = '09/09/2024'
    state = swiss.fill_home_page_form('09/09/2024', 'Lisbon', 'Geneva, all airports')
    if state == "Abort":
        if inputs.input_print_ > 0:
            print('Aborting due to error filling home page form')
        swiss.close()
        sys.exit()

    flights = swiss.get_flights()
    if flights == "Abort":
        if inputs.input_print_ > 0:
            print('Aborting due to error getting flights')
        swiss.close()
        sys.exit()
    if inputs.input_print_ > 2:
        print(f'Number of flights: {len(flights)}')

    for j in range(0,len(flights)):
        flight_id = '09-09-2024_' + 'LIS-' + 'GVA_' + str(j+1)
        if j != 0:
            state = swiss.fill_home_page_form(current_flyout_date, current_origin, current_destination)
            if state == "Abort":
                if inputs.input_print_ > 0:
                    print('Aborting due to error filling home page form')
                continue
        flights = swiss.get_flights()
        airliner, details = swiss.get_flight_details(flights, j)
        flights_details.append(details)
        for i in range(len(fares)):
            fare = fares[i]
            if fare == "Economy" and details['price_economy'] == "Sold Out":
                data = {
                    'time': current_time,
                    'airliner': airliner,
                    'flight_ID': flight_id,
                    'details': details
                }
            if fare == "Business" and details['price_business'] == "Sold Out":
                data = {
                    'time': current_time,
                    'airliner': airliner,
                    'flight_ID': flight_id,
                    'details': details
                }
            else:    
                # Add logic to exclude flights that are sold out
                flyout = current_flyout_date
                orig = current_origin
                dest = current_destination
                current_fare_name = fare
                state = swiss.fill_home_page_form(current_flyout_date, current_origin, current_destination)
                if state == "Abort":
                    if inputs.input_print_ > 0:
                        print('Aborting due to error filling home page form')
                    continue
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                flights = swiss.get_flights()
                if flights == "Abort":
                    if inputs.input_print_ > 0:
                        print('Aborting due to error getting flights')
                    continue
                if inputs.input_print_ > 2:
                    print(f'Number of flights: {len(flights)}')
                fare_options = swiss.advance_to_your_selection_page(flights, fare_name=current_fare_name, index=j)
                if fare_options == "Abort":
                    if inputs.input_print_ > 0:
                        print('Aborting due to error advancing to form page')
                    continue
                if "Swiss" in airliner:
                    state = swiss.advance_to_passenger_form_page(flights, index=j)
                    if state == "Abort":
                        if inputs.input_print_ > 0:
                            print('Aborting due to error advancing to passenger form page')
                        continue
                    state = swiss.fill_passenger_form()
                    if state == "Abort":
                        if inputs.input_print_ > 0:
                            print('Aborting due to error filling passenger form')
                        continue
                    services = swiss.get_bags_and_info(fare)
                    if services == "Abort":
                        if inputs.input_print_ > 0:
                            print('Aborting due to error getting services')
                        continue
                    seats = swiss.get_flight_seats(fare)
                    if seats == "Abort":
                        if inputs.input_print_ > 0:
                            print('Aborting due to error getting seats')
                        continue
                    flights_seats.append(seats)
                    data = {
                        'time': current_time,
                        'airliner': airliner,
                        'flight_ID': flight_id,
                        'details': details,
                        'fares': fare_options,
                        'services': services,
                        'seats': seats
                    }
                else:
                    data = {
                        'time': current_time,
                        'airliner': airliner,
                        'flight_ID': flight_id,
                        'details': details,
                        'fares': fare_options
                    }
            if(j == 0 and fare == "Economy"):
                if file_exists and file_not_empty:
                    mode = 'a'
                    first = False
                else:
                    mode = 'w'
                    first = True
                with open(filename, mode=mode, newline='') as file:
                    writer = csv.writer(file)
                    write_to_csv_row(writer, data, first)
            else:
                with open(filename, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    write_to_csv_row(writer, data)

    if inputs.input_print_ > 2:
        print(flights_details)
        print(flights_seats)

    # close the driver
    swiss.close()







        
                

                        

                
        

        




                

