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

def flatten_dict(d, parent_key='', sep='_'):
    if inputs.easyjet_print_ > 1:
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
    if inputs.easyjet_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def flatten_dict_with_na(d, parent_key='', sep='_'):
    if inputs.easyjet_print_ > 1:
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
    if inputs.easyjet_print_ > 1:
        print('Returning items from falatten_dict')
    return dict(items)

def write_to_csv_row(writer, data, first=False, sold_out=False):
    if inputs.easyjet_print_ > 1:
        print('Writing to CSV row')
    # Flatten the details and seats data
    if sold_out:
        flattened_data = flatten_dict_with_na(data)
        flattened_data = flatten_dict(flattened_data)
    else:
        flattened_data = flatten_dict(data)
    if first:
        if inputs.easyjet_print_ > 1:
            print('Writing header row')
        # Write the header row
        header = list(flattened_data.keys())
        writer.writerow(header)

    row = list(flattened_data.values())
    # Write the row to the CSV file
    writer.writerow(row)
    if inputs.easyjet_print_ > 1:
        print('Wrote flattened data')

def check_and_close_popup(driver):
    if inputs.easyjet_print_ > 1:
        print('Checking and closing popup')
    try:
        # Check for overlay element
        overlay = WebDriverWait(driver, timeout=inputs.easyjet_timeout_cookies).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='rtm-overlay']")))
        if overlay:
            # Find and click the close button
            close_button = overlay.find_element(By.CSS_SELECTOR, "[class*='close-sc closeStyle1-sc']")
            if close_button:
                close_button.click()
                if inputs.easyjet_print_ > 1:
                    print('Overlay closed')
        else:
            if inputs.easyjet_print_ > 1:
                print('No overlay found')
    except Exception as e:
        if inputs.easyjet_print_ > 0:
            print(f'Exception occurred: {e}')

def is_element_in_view(driver, element):
    if inputs.easyjet_print_ > 1:
        print('Checking if element is in view')
    # Check if the element is displayed
    if element.is_displayed():
        if inputs.easyjet_print_ > 1:
            print('Element is displayed')
        return True
    else:
        # Scroll the element into view
        if inputs.easyjet_print_ > 1:
            print('Trying to scroll element into view')
        driver.execute_script("arguments[0].scrollIntoView();", element)
        if inputs.easyjet_print_ > 1:
            print('Scrolled element into view')
        # Check again if the element is displayed after scrolling
        return element.is_displayed()

def check_element_exists_by_ID(driver, id, timeout=inputs.easyjet_timeout_checks):
    element_exists = False
    if inputs.easyjet_print_ > 1:
        print(f'Checking if element exists by ID: {id}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.ID, id)))
        if inputs.easyjet_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.easyjet_print_ > 0:
            print(f'No element by ID: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_CSS_SELECTOR(driver, css, timeout=inputs.easyjet_timeout_checks):
    element_exists = False
    if inputs.easyjet_print_ > 1:
        print(f'Checking if element exists by CSS: {css}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if inputs.easyjet_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.easyjet_print_ > 0:
            print(f'No element by CSS Selector: {e}')
        element_exists = False
    return element_exists

def check_element_exists_by_TAG_NAME(driver, tag, timeout=inputs.easyjet_timeout_checks):
    element_exists = False
    if inputs.easyjet_print_ > 1:
        print(f'Checking if element exists by Tag Name: {tag}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.TAG_NAME, tag)))
        if inputs.easyjet_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.easyjet_print_ > 0:
            print(f'No element by Tag Name: {e}')
        element_exists = False
    return element_exists

class EasyJet:

    def __init__(self, headless=True):

        self.timeout = inputs.easyjet_timeout
        self.timeout_cookies = inputs.easyjet_timeout_cookies
        self.timeout_little = inputs.easyjet_timeout_little
        self.timeout_implicitly_wait = inputs.easyjet_timeout_implicitly_wait
        self.cookies = inputs.easyjet_cookies
        self.print_ = inputs.easyjet_print_
        self.closed_popup_cabin_bags = False
        self.new_tab_opened = False

        self.buttons = []

        if self.print_ > 1:
            print('Initializing EasyJet')
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = uc.Chrome()
        if self.print_ > 1:
            print('Initialized EasyJet')

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

    def fill_home_page_form(self, flyout, orig, dest, adults='1', teens='0', children='0', infants='0'):

        if self.print_ > 1:
            print('Entering Fill Form Function')
        # set url
        url = f'https://www.easyjet.com/en/'
        # get the page
        self.driver.get(url)
        if self.print_ > 1:    
            print('Opened EasyJet homepage')
        self.driver.implicitly_wait(self.timeout_implicitly_wait)

        # For some reason there are no cookies on the EasyJet website
        # id="ensNotifyBanner"
        # id="ensCloseBanner"

        if self.cookies == "not accepted":
            try:
                if check_element_exists_by_ID(self.driver, 'ensCloseBanner', timeout = self.timeout_cookies):
                    self.driver.find_element(By.CSS_SELECTOR, "[id*='ensCloseBanner']").click()
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
            if check_element_exists_by_ID(self.driver, 'one-way'):
                self.click_with_retry(self.driver.find_element(By.ID, 'one-way'))
                if self.print_ > 1:
                    print('Clicked on One Way')
            else:
                if self.print_ > 1:
                    print('No One Way button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on One Way: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)
        
        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[aria-label*='From Airport']"):
                self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='From Airport']").clear()
                self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='From Airport']").send_keys(orig + Keys.RETURN)
                if self.print_ > 1:
                    print('Entered origin')
            else:
                if self.print_ > 1:
                    print('No From Airport field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering origin: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[aria-label*='To Airport']"):
                self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='To Airport']").send_keys(dest + Keys.RETURN)
                if self.print_ > 1:
                    print('Entered destination')
            else:
                if self.print_ > 1:
                    print('No To Airport field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering destination: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)

        try:
            if self.print_ > 1:
                print('Clicking to open calendar date')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='date-picker-button']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='date-picker-button']"))
                if self.print_ > 1:
                    print('Clicked on Calendar Opener Button')
            else:
                if self.print_ > 1:
                    print('No Calendar Opener Button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Calendar Opener Button: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)

        try:
            if self.print_ > 1:
                print('Selecting departure date on calendar')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='drawer-tab-content active']"):
                formatted_date = datetime.strptime(flyout, '%Y/%m/%d').strftime('%Y-%m-%d')
                if check_element_exists_by_CSS_SELECTOR(self.driver, f"[data-date='{formatted_date}']"):
                    date_div = self.driver.find_element(By.CSS_SELECTOR, f"[data-date='{formatted_date}']")
                    self.click_with_retry(date_div.find_element(By.TAG_NAME, 'a'))
                    if self.print_ > 1:
                        print('Selected departure date')
                else:
                    if self.print_ > 1:
                        print('Departure date not found.')
                    # TODO: Press ESC to close the drawer and repeat the process
            else:
                if self.print_ > 1:
                    print('No active drawer tab found')
                # TODO: Repeat the process
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting departure date: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-ej-gtm*='searchpod|searchFlightsButton']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[data-ej-gtm*='searchpod|searchFlightsButton']"))
                if self.print_ > 1:
                    print('Clicked on Search Flights Button')
            else:
                if self.print_ > 1:
                    print('No Search Flights button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Search Flights button: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)

        if self.print_ > 1:
            print('Exiting Fill Form Function')
            print('Going to next page')

        # try:
        #     # WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='flight-search-from']")))
        #     # self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").clear()
        #     # self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").send_keys(orig + Keys.RETURN)
        #     # if self.print_ > 1:
        #     #     print('Entered origin')
        #     # Correct this here
        #     # WebDriverWait(self.driver, timeout=self.timeout).until(lambda d: d.find_element(By.CSS_SELECTOR, "[id*='flight-search-to']").get_attribute('disabled') is None)
        #     WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='flight-search-to']")))
        #     self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-to']").send_keys(dest + Keys.RETURN)
        #     if self.print_ > 1:
        #         print('Entered destination')
        #     self.driver.find_element(By.CSS_SELECTOR, "[class*='form-control bsdatepicker']").send_keys(flyout + Keys.RETURN)
        #     if self.print_ > 1:
        #         print('Entered departure date')
        # except Exception as e:
        #     if check_element_exists_by_TAG_NAME(self.driver, 'app-stopover-modal'):
        #         try:
        #             self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Close dialog']").click()
        #             if self.print_ > 1:
        #                 print('Closed Stopover Modal')
        #         except Exception as e:
        #             if self.print_ > 0:
        #                 print(f'Error closing Stopover Modal: {e}')
        #         self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").clear()
        #         self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-from']").send_keys(orig + Keys.RETURN)
        #         if self.print_ > 1:
        #             print('Entered origin')
        #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='flight-search-to']")))
        #         self.driver.find_element(By.CSS_SELECTOR, "[id*='flight-search-to']").send_keys(dest + Keys.RETURN)
        #         if self.print_ > 1:
        #             print('Entered destination')
        #         self.driver.find_element(By.CSS_SELECTOR, "[class*='form-control bsdatepicker']").send_keys(flyout + Keys.RETURN)
        #         if self.print_ > 1:
        #             print('Entered departure date')
        #     else:
        #         if self.print_ > 0:
        #             print(f'Error entering origin, destination or date: {e}')
        #         self.fill_home_page_form(flyout, orig, dest)

        # # Open Search Page
        # try:
        #     WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Continue to next page to select dates']")))
        #     self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Continue to next page to select dates']").click()
        #     if self.print_ > 1:
        #         print('Clicked on Search Button')
        # except Exception as e:
        #     if check_element_exists_by_TAG_NAME(self.driver, 'app-stopover-modal'):
        #         try:
        #             self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Close dialog']").click()
        #             if self.print_ > 1:
        #                 print('Closed Stopover Modal')
        #         except Exception as e:
        #             if self.print_ > 0:
        #                 print(f'Error closing Stopover Modal: {e}')
        #         self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Continue to next page to select dates']").click()
        #         if self.print_ > 1:
        #             print('Clicked on Search Button')
        #     else:
        #         if self.print_ > 0:
        #             print(f'Error clicking on Search Button: {e}')
        #         self.fill_home_page_form(flyout, orig, dest)

        # if self.print_ > 1:
        #     print('Exiting Fill Form Function')
        #     print('Going to next page')
        # if check_element_exists_by_TAG_NAME(self.driver, 'app-stopover-modal'):
        #     self.fill_home_page_form(flyout, orig, dest)

    def search_from_home_page(self):
        if self.print_ > 1:
            print('Searching from home page')
        
        url = f'https://www.easyjet.com/en/'
        self.driver.get(url)

        if self.print_ > 1:
            print('Hitting search on home page')
            
        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-ej-gtm*='searchpod|searchFlightsButton']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[data-ej-gtm*='searchpod|searchFlightsButton']"))
                if self.print_ > 1:
                    print('Clicked on Search Flights Button')
            else:
                if self.print_ > 1:
                    print('No Search Flights button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Search Flights button (HAVE NOT FILLED FORM) : {e}. Trying to solve the problem')
            self.search_from_home_page()

        if self.print_ > 1:
            print('Exiting Search From Home Page Function')
            print('Going to next page')

    def get_flights(self):
        if self.print_ > 1:
            print('Getting Flights')

        if not self.new_tab_opened:
            try: # Wait for the new tab to load and then switch to it
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.number_of_windows_to_be(2))
                if self.print_ > 1:
                    print('New tab loaded')
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.new_tab_opened = True
                if self.print_ > 1:
                    print('Switched to new tab')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error switching to new tab: {e}')
                self.get_flights()

        time.sleep(5)

        try: # Select FLEXI fares button with id=flexi-fares-checkbox
            if self.print_ > 1:
                print('Selecting Flexi Fares')
            if check_element_exists_by_ID(self.driver, 'flexi-fares-checkbox'):
                self.click_with_retry(self.driver.find_element(By.ID, 'flexi-fares-checkbox'))
                if self.print_ > 1:
                    print('Clicked on Flexi Fares')
            else:
                if self.print_ > 1:
                    print('No Flexi Fares found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting Flexi Fares: {e}')
            # TODO: Get past buttons to get to the next page 
            

        try:
            if self.print_ > 1:
                print('Waiting for flights to load')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='flight-grid-day-wrapper']"):
                flights_div = self.driver.find_element(By.CSS_SELECTOR, "[class='flight-grid-day-wrapper']")
                if self.print_ > 1:
                    print('Found flights div')
            else:
                if self.print_ > 1:
                    print('No flights div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flights: {e}')
            # TODO: Get past buttons to get to the next page
        
        try:
            if self.print_ > 1:
                print('Getting flights from flight div')
            if check_element_exists_by_TAG_NAME(self.driver, 'ul'):
                flights_list = flights_div.find_element(By.TAG_NAME, 'ul')
                flights = flights_list.find_elements(By.TAG_NAME, 'li')
                if self.print_ > 1:
                    print('Found flights list')
                if self.print_ > 2:
                    print(f'Flights: {flights}')
            else:
                if self.print_ > 1:
                    print('No flights list found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flights from list: {e}')

        if self.print_ > 1:
            print('Exiting Get Flights Function')
    
        return flights
    
    def get_flight_details(self, flight):
        if self.print_ > 1:
            print('Getting Flight Details')

        date = 'N/A'
        fares_buttons = []

        try:
            if self.print_ > 1:
                print('Getting flight date')
            if check_element_exists_by_CSS_SELECTOR(flight, "[class='flight-grid-day-wrapper']"):
                flights_div = flight.find_element(By.CSS_SELECTOR, "[class='flight-grid-day-wrapper']")
                if check_element_exists_by_CSS_SELECTOR(flights_div, "[class='day-title']"):
                    date_title = flights_div.find_element(By.CSS_SELECTOR, "[class='day-title']")
                    date = date_title.find_elements(By.TAG_NAME, 'span')[1].text
                    if self.print_ > 1:
                        print(f'Found date: {date}')
                else:
                    if self.print_ > 1:
                        print('No date found')
            else:
                if self.print_ > 1:
                    print('No flights div found inside flight details function')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting date: {e}')
            self.get_flight_details(flight)
                
        try:
            if self.print_ > 1:
                print('Getting flight details from flight')
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='flight-grid-flight-fare ej-text']"):
                fares_buttons = flight.find_elements(By.CSS_SELECTOR, "[class*='flight-grid-flight-fare ej-text']")
                if self.print_ > 1:
                    print('Found fares')
            else:
                if self.print_ > 1:
                    print('No fares found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting fare: {e}')
            self.get_flight_details(flight)

        fares = []
        departure_time = 'N/A'
        arrival_time = 'N/A'
        standard_price = 'N/A'
        flexi_price = 'N/A'
        
        try:
            if self.print_ > 1:
                print('Getting fare details')
            for i in range(len(fares_buttons)):
                if i == 0:
                    times = fares_buttons[i].find_elements(By.CSS_SELECTOR, "[class='flight-time']")
                    departure_time = times[0].text
                    arrival_time = times[1].text
                    price_span = fares_buttons[i].find_element(By.CSS_SELECTOR, "[class='price-container']")
                    standard_price = price_span.find_element(By.CSS_SELECTOR, "[class='major']").text + ',' + price_span.find_element(By.CSS_SELECTOR, "[class='minor']").text
                    fares.append({'fare': 'Standard', 'price': standard_price})
                if i == 1:
                    price_span = fares_buttons[i].find_element(By.CSS_SELECTOR, "[class='price-container']")
                    flexi_price = price_span.find_element(By.CSS_SELECTOR, "[class='major']").text + ',' + price_span.find_element(By.CSS_SELECTOR, "[class='minor']").text
                    fares.append({'fare': 'FLEXI', 'price': flexi_price})
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting fare details: {e}')
            self.get_flight_details(flight)

        if self.print_ > 1:
            print('Exiting Get Flight Details Function')
        
        details = {
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'fares': fares,
        }

        return details
    
    def advance_to_seats(self, flight):

        if self.print_ > 1:
            print('Advancing to Seats')

        try: # click button with 
            if self.print_ > 1:
                print('Clicking on Select Button')
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='flight-grid-flight-fare ej-text standard']"):
                if self.click_with_retry(flight.find_element(By.CSS_SELECTOR, "[class*='flight-grid-flight-fare ej-text standard']")):
                    if self.print_ > 1:
                        print('Clicked on Select Button')
                else:
                    if self.print_ > 1:
                        print('Failed to click on Select Button')
                    return "Sold Out"
            else:
                if self.print_ > 1:
                    print('No Select Button found')
                return "Sold Out"
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Select Button: {e}')
            return "Sold Out"

        try:
            if self.print_ > 1:
                print('Clicking on Continue Button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='ej-button rounded-corners continue-button']"):
                if self.print_ > 1:
                    print('Continue Button found')
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class='ej-button rounded-corners continue-button']"))
                if self.print_ > 1:
                    print('Clicked on Continue Button')
            else:
                if self.print_ > 1:
                    print('Continue Button not found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Continue Button: {e}')

        if self.print_ > 1:
            print('Opening overlay to select fares')
        
        try:
            if self.print_ > 1:
                print('Opening overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='select-fare-type-modal']"):
                overlay = self.driver.find_element(By.CSS_SELECTOR, "[class='select-fare-type-modal']")
                if self.print_ > 1:
                    print('Overlay found')
            else:
                if self.print_ > 1:
                    print('No overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error opening overlay: {e}')

        fares = []

        try:
            if self.print_ > 1:
                print('Getting fare types')
            if check_element_exists_by_CSS_SELECTOR(overlay, "[class*='fare-card-outer-wrapper']"):
                fare_cards = overlay.find_elements(By.CSS_SELECTOR, "[class*='fare-card-outer-wrapper']")
                if self.print_ > 1:
                    print('Found fare cards')
                for i in range(len(fare_cards)):
                    fare_type = fare_cards[i].find_element(By.CSS_SELECTOR, "[class='fare-heading']").text.replace(' ', '')
                    if self.print_ > 2:
                        print(f'Fare type: {fare_type}')
                    fare_card_footer = fare_cards[i].find_element(By.CSS_SELECTOR, "[class='fare-card__footer']")
                    button_div = fare_card_footer.find_element(By.CSS_SELECTOR, "[class='button-container']")
                    button = button_div.find_element(By.CSS_SELECTOR, "[class='ej-button rounded-corners']")
                    if fare_type == 'Standard':
                        if self.print_ > 1:
                            print('Standard fare type found')
                        standard_button = button
                        price = '0'
                    else:
                        price = button.text.replace('+', '').replace('€', '').replace('.', ',').replace(' ', '')
                        match = re.search(r'\d+\,\d+', price)
                        if match:
                            price = match.group() + '€'
                        else:
                            price = '0'
                    fares.append({'fare': fare_type, 'price': price})

            else:
                if self.print_ > 1:
                    print('No fare cards found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting fare types: {e}')

        try:
            if self.print_ > 1:
                print('Selecting standard fare type')
            if self.print_ > 2:
                print(f'Standard button: {standard_button.text}')
            self.click_with_retry(standard_button)
            if self.print_ > 1:
                print('Selected standard fare type')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting standard fare type: {e}')
            self.advance_to_seats(flight)

        return fares
    
    def check_seat_availability(self, seat):
        try:
            seat_class = seat.get_attribute("class")
            if "unavailable" in seat_class:
                return 'unavailable'
            else:
                return 'available'
        except Exception as e:
            
            print(f'Error checking seat {seat.get_attribute("id")} availability: {e}')
        
    def decide_area(self, seat, info_div):
        if self.print_ > 1:
            print('Deciding area')
        if(self.driver.execute_script(compare_positions, seat, info_div)):
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

    def determine_section_info(self, section_info):
        if self.print_ > 1:
            print('Determining section info')
        name = section_info.find_element(By.CSS_SELECTOR, "[class='price-band-name']").text
        price = section_info.find_element(By.CSS_SELECTOR, "[class='major']").text + ',' + section_info.find_element(By.CSS_SELECTOR, "[class='minor']").text
        return {
            'name': name,
            'price': price,
            'available': 0,
            'unavailable': 0
        }  
    
    def get_flight_seats(self):
        if self.print_ > 1:
            print('Getting flight seats')
        try:
            if self.print_ > 1:
                print('Checking for seatmap')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='aircraft-wrapper']"):
                seatmap = self.driver.find_element(By.CSS_SELECTOR, "[class='aircraft-wrapper']")
                if self.print_ > 1:
                    print('Seatmap found')
            else:
                if self.print_ > 0:
                    print('Seatmap not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting seatmap: {e}')
            # TODO: Implement button logic to solve the problem

        try:
            if self.print_ > 1:
                print('Counting seats')
            total_seats = [0, 0]
            seats_divs = seatmap.find_elements(By.CSS_SELECTOR, "[class='seat-wrapper']")
            section_infos = seatmap.find_elements(By.CSS_SELECTOR, "[class='section-information']")
            infos = []

            for i in range(len(section_infos)):
                infos.append(self.determine_section_info(section_infos[i]))

            for i in range(len(seats_divs)):
                seat_div = seats_divs[i]
                seat_button = seat_div.find_element(By.CSS_SELECTOR, "[class*='seat']")
                broke = False
                for j in range(len(infos)):
                    if self.driver.execute_script(compare_positions, seat_button, section_infos[j]):
                        broke = True
                        break
                if broke:
                    k = j-1
                else:
                    k = j
                if self.check_seat_availability(seat_button) == 'available':
                    infos[k]['available'] += 1
                    total_seats[0] += 1
                else:
                    infos[k]['unavailable'] += 1
                    total_seats[1] += 1

            if self.print_ > 1:
                print('Seats counted successfully')
            if self.print_ > 2:
                print(f'Total Seats counted {total_seats}')
                for i in range(len(infos)):
                    print(f'Section {infos[i]["name"]}: Available {infos[i]["available"]} Unavailable {infos[i]["unavailable"]}')

        except Exception as e:
            if self.print_ > 0:
                print(f'Error counting seats: {e}')

        try:
            if self.print_ > 1:
                print('Clicking on Skip Seats Button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='button-link arrow-button']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class='button-link arrow-button']"))
                if self.print_ > 1:
                    print('Clicked on Skip Seats Button')
            else:
                if self.print_ > 1:
                    print('No Skip Seats Button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Skip Seats Button: {e}')

        if self.print_ > 1:
            print('Going to Cabin Bags Page')
            print('Exiting Get Flight Seats Function')
                
        seats_data = {
            'total_seats_available': total_seats[0],
            'total_seats_unavailable': total_seats[1],
            'seats_info': infos
        }
        
        return seats_data 

    def get_cabin_bags(self):
        
        if self.print_ > 1:
            print('Getting Cabin Bags')

        try: # waiting for container with class = large-cabin-bags-container
            if self.print_ > 1:
                print('Waiting for cabin bags container')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='large-cabin-bags-container']"):
                cabin_bags_container = self.driver.find_element(By.CSS_SELECTOR, "[class='large-cabin-bags-container']")
                if self.print_ > 1:
                    print('Cabin bags container found')
            else:
                if self.print_ > 1:
                    print('No cabin bags container found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting cabin bags container: {e}')
            # TODO: Implement button logic to solve the problem
        
        bags = {
            'name': 'Large Cabin Bags',
            'price': '',
        }
        
        try:
            if self.print_ > 1:
                print('Getting cabin bags price')
            if check_element_exists_by_CSS_SELECTOR(cabin_bags_container, "[class='price price-eur']"):
                # Get major and minor separately
                major = cabin_bags_container.find_element(By.CSS_SELECTOR, "[class='major']").text
                minor = cabin_bags_container.find_element(By.CSS_SELECTOR, "[class='minor']").text
                bags['price'] = major + ',' + minor
                if self.print_ > 1:
                    print(f'Found price: {bags["price"]}')
            else:
                if self.print_ > 1:
                    print('No price found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting cabin bags price: {e}')
        
        
        try:
            if self.print_ > 1:
                print('Clicking on Skip Cabin Bags Button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[aria-label='Skip cabin bags page']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[aria-label='Skip cabin bags page']"))
                if self.print_ > 1:
                    print('Clicked on Skip Cabin Bags Button')
            else:
                if self.print_ > 1:
                    print('No Skip Cabin Bags Button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on Skip Cabin Bags Button: {e}')
        
        if not self.closed_popup_cabin_bags:
            try: # I need to click on the "no thanks" button. The class of the popup is "drawer-content-outer" and of the button inside the popup has this attribute: data-ej-gtm="button|addALargeCabinBagDrawer|no"
                if self.print_ > 1:
                    print('Clicking on No Thanks Button')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-ej-gtm*='addALargeCabinBagDrawer|no']"):
                    self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[data-ej-gtm*='addALargeCabinBagDrawer|no']"))
                    self.closed_popup_cabin_bags = True
                    if self.print_ > 1:
                        print('Clicked on No Thanks Button')
                else:
                    if self.print_ > 1:
                        print('No "No Thanks" Button found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error clicking on No Thanks Button: {e}')

        
        if self.print_ > 1:
            print('Going to next page')
            print('Exiting Get Cabin Bags Function')
        
        return bags

    def get_hold_bags(self):
        if self.print_ > 1:
            print('Getting Hold Bags')

        bags = {
            'name': '23Kg Hold Bags',
            'price': '',
        }

        try: # waiting for container with class = hold-bags-container
            if self.print_ > 1:
                print('Waiting for hold bags container')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='luggage-tile-weight-23']"):
                hold_bags_container = self.driver.find_element(By.CSS_SELECTOR, "[class*='luggage-tile-weight-23']")
                if self.print_ > 1:
                    print('Hold bags container found')
            else:
                if self.print_ > 1:
                    print('No hold bags container found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting hold bags container: {e}')

        try:
            if self.print_ > 1:
                print('Getting hold bags price')
            if check_element_exists_by_CSS_SELECTOR(hold_bags_container, "[class='price price-eur']"):
                # Get major and minor separately
                major = hold_bags_container.find_element(By.CSS_SELECTOR, "[class='major']").text
                minor = hold_bags_container.find_element(By.CSS_SELECTOR, "[class='minor']").text
                bags['price'] = major + ',' + minor
                if self.print_ > 1:
                    print(f'Found price: {bags["price"]}')
            else:
                if self.print_ > 1:
                    print('No price found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting hold bags price: {e}')

        if self.print_ > 1:
            print('Exiting Get Hold Bags Function')
        
        return bags
    
    def close(self):
        self.driver.quit()



def main(origin_name, origin_code, destination_name, destination_code, date):

    easyjet = EasyJet(headless=True)
    
    airliner = 'EasyJet'

    filename = airliner + '/' + 'outputs' + '/' + 'EasyJet_' + time.strftime("%d-%m-%Y") + '.csv'
    file_exists = os.path.isfile(filename)
    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
    flights_details = []
    flights_fares = []
    flights_seats = []
    flights_luggage = []
    sold_out = False
    date_for_id = datetime.strptime(date, "%Y/%m/%d").strftime('%d-%m-%Y')

    # get the data
    easyjet.fill_home_page_form(date, origin_code, destination_code)
    flights = easyjet.get_flights()

    flight_id_partial = date_for_id + '_' + origin_code + '-' + destination_code

    if flights is not None:
        if inputs.easyjet_print_ > 2:
            print(f'Number of flights: {len(flights)}')
        for i in range(0, len(flights)):
            sold_out = False
            luggage_prices = []
            flight_id = date.replace('/', '-') + '_' + origin_code + '-' + destination_code + '_' + str(i+1)
            observation_id = flight_id
            if not i == 0:
                easyjet.search_from_home_page()
                flights = easyjet.get_flights()
            details = easyjet.get_flight_details(flights[i])
            if details is not None:
                if details['departure_time'] is not None and details['departure_time'] != 'N/A':
                    flight_id = flight_id_partial + '_' + airliner + '_' + details['departure_time']
                else:
                    if easyjet.print_ > 0:
                        print('An error has occured while getting flight details')
                    continue
            else:
                if easyjet.print_ > 0:
                    print('An error has occured while getting flight details')
                continue
            flights_details.append(details)
            fares = easyjet.advance_to_seats(flights[i])
            if fares == 'Sold Out':
                if inputs.easyjet_print_ > 2:
                    print(f'Flight {i+1} is sold out')
                if len(flights_fares) > 1 and len(flights_seats) > 1 and len(flights_luggage) > 1:
                    sold_out = True
                    fare_sold_out = flights_fares[-2]
                    seats_sold_out = flights_seats[-2]
                    luggage_sold_out = flights_luggage[-2]
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    data = {
                        'time': current_time,
                        'airliner': airliner,
                        'origin_name': origin_name,
                        'origin_code': origin_code,
                        'destination_name': destination_name,
                        'destination_code': destination_code,
                        'date': date,
                        'flight_id': flight_id,
                        'observation_id': observation_id,
                        'details': details,
                        'fares': fare_sold_out,
                        'infos': luggage_sold_out,
                        'seats': seats_sold_out
                    }
                else:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    data = {
                        'time': current_time,
                        'airliner': airliner,
                        'flight_id': flight_id,
                        'origin_name': origin_name,
                        'origin_code': origin_code,
                        'destination_name': destination_name,
                        'destination_code': destination_code,
                        'date': date,
                        'observation_id': observation_id,
                        'details': details,
                        'fares': 'Sold Out',
                        'infos': 'Sold Out',
                        'seats': 'Sold Out'
                    }
            else:
                flights_fares.append(fares)
                seats = easyjet.get_flight_seats()
                flights_seats.append(seats)
                cabin_bags = easyjet.get_cabin_bags()
                hold_bags = easyjet.get_hold_bags()
                luggage_prices.append(cabin_bags)
                luggage_prices.append(hold_bags)
                flights_luggage.append(luggage_prices)
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
                    'infos': luggage_prices,
                    'seats': seats
                }
            if(i == 0):
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
                with open(filename, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    write_to_csv_row(writer, data, sold_out=sold_out)

    else:
        if easyjet.print_ > 0:
            print('No flights found. Assuming that the flights are sold out.')
        flight_id = date.replace('/', '-') + '_' + origin_code + '-' + destination_code + '_' + str(1)
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

    if easyjet.print_ > 1:
        print(flights_details)
        print(flights_fares)
        print(flights_luggage)
        print(flights_seats)

    # close the driver
    easyjet.close()

    if easyjet.print_ > 1:
        print('Driver closed')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Get information about flights page form for EasyJet")

    parser.add_argument('--origin-name', required=False, help='Origin airport name')
    parser.add_argument('--origin', required=True, help='Origin airport code')
    parser.add_argument('--destination-name', required=False, help='Destination airport name')
    parser.add_argument('--destination', required=True, help='Destination airport code')
    parser.add_argument('--date', required=True, help='Flight date in YYYYY/MM/DD format')

    args = parser.parse_args()

    main(origin_name=args.origin_name, origin_code=args.origin, destination_name=args.destination_name, destination_code=args.destination, date=args.date)