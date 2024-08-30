# import libraries
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
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'No element by CSS Selector: {e}')
        element_exists = False
    return element_exists

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

class AirEuropa:

    def __init__(self, headless=True):

        self.timeout = inputs.input_timeout
        self.timeout_cookies = inputs.input_timeout_cookies
        self.timeout_little = inputs.input_timeout_little
        self.timeout_implicitly_wait = inputs.input_timeout_implicitly_wait
        self.cookies = inputs.input_cookies
        self.print_ = inputs.input_print_
        self.closed_popup_cabin_bags = False
        self.new_tab_opened = False
        self.closed_fares_overlay = False

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
                self.fill_home_page_form(flyout, orig, dest)
        
        try:
            if self.print_ > 1:
                print('Clicking on apply language')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='mat-tooltip-trigger ae-btn']", timeout = self.timeout):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='mat-tooltip-trigger ae-btn']"))
                if self.print_ > 1:
                    print('Clicked on apply language')
            else:
                if self.print_ > 1:
                    print('No apply language button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on apply language: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)

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
            self.fill_home_page_form(flyout, orig, dest)

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
            self.fill_home_page_form(flyout, orig, dest)

        try:
            if self.print_ > 1:
                print('Selecting one way')
            if check_element_exists_by_ID(self.driver, 'mat-option-1'):
                self.click_with_retry(form.find_element(By.ID, 'mat-option-1'))
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
                self.driver.find_element(By.ID, 'departure').send_keys(orig + Keys.RETURN)
                if self.print_ > 1:
                    print('Entered origin')
            else:
                if self.print_ > 1:
                    print('No origin field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering origin: {e}. Trying to solve the problem')
            
        try:
            if self.print_ > 1:
                print('Entering destination')
            if check_element_exists_by_ID(self.driver, 'cdk-overlay-2'):
                if self.print_ > 1:
                    print('Found overlay for dropdown menu')
            else:
                if self.print_ > 1:
                    print('No overlay for dropdown menu found')
            if check_element_exists_by_ID(self.driver, 'arrival'):
                self.driver.find_element(By.ID, 'arrival').send_keys(dest + Keys.RETURN)
                if self.print_ > 1:
                    print('Entered destination')
            else:
                if self.print_ > 1:
                    print('No destination field found')
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
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='mat-tooltip-trigger ae-btn']"):
                self.click_with_retry(form.find_element(By.CSS_SELECTOR, "[class*='mat-tooltip-trigger ae-btn']"))
                if self.print_ > 1:
                    print('Clicked on search button')
            else:
                if self.print_ > 1:
                    print('No search button found')
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='mat-tooltip-trigger ae-btn']"):
                    if self.print_ > 1:
                        print('Search button is disabled')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on search button: {e}. Trying to solve the problem')
            self.fill_home_page_form(flyout, orig, dest)

        
        if self.print_ > 1:
            print('Exiting Fill Form Function')
            print('Going to next page')
            
    def check_seat_availability(self, seat):
        try:
            seat_class = seat.get_attribute("class")
            if "seat-characteristic-unavailable" in seat_class:
                return 'unavailable'
            else:
                if "seat-characteristic-E" in seat_class:
                    return 'emergency'
                else:
                    return 'available'
        except Exception as e:
            print(f'Error checking seat {seat.get_attribute("title")} availability: {e}')

    def get_flights(self):
        if self.print_ > 1:
            print('Getting Flights')

        try:
            if check_element_exists_by_TAG_NAME(self.driver, 'mat-accordion'):
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
    
    def get_flight_details(self, flight):

        if self.print_ > 1:
            print('Getting flight details')

        departure_flyout_time = 'No time found'
        
        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[class='refx-display-1 bound-departure-datetime']"):
                if self.print_ > 1:
                    print('Found flight departure time')
                departure_flyout_time = flight.find_element(By.CSS_SELECTOR, "[class*='flight-details']").text
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
                arrival_flyout_time = flight.find_element(By.CSS_SELECTOR, "[class*='flight-details']").text
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
        
        details = {
            'departure_flyout_time': departure_flyout_time,
            'arrival_flyout_time': arrival_flyout_time,
            'price_economy': price
        }

        return details
    
    def advance_to_form_page(self, flight, fare_name):

        if self.print_ > 1:
            print('Advancing to form page')

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
                self.advance_to_form_page(flight)
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
            
            if check_element_exists_by_TAG_NAME(ul, 'li'):
                if self.print_ > 1:
                    print('Found li')
                fares_divs = ul.find_elements(By.TAG_NAME, 'li')
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
                if i == 3 and fare_name == 'Business':
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
                if check_element_exists_by_CSS_SELECTOR(fares_divs[i], "[class*='price-card-title-label']"):
                    if self.print_ > 1:
                        print('Found fare name')
                    name = fares_divs[i].find_element(By.CSS_SELECTOR, "[class*='price-card-title-label']").text
                    fare['name'] = name
                    if self.print_ > 2:
                        print(f'Fare name: {name}')
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
                print('Clicking on first button')
            self.click_with_retry(button_to_continue)
            if self.print_ > 1:
                print('Clicked on first button')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on first button: {e}')

        if not self.closed_fares_overlay:
            if self.print_ > 1:
                print('Closing dialog')
            if fare_name == 'Economy':
                index_of_dialog = '2'
            else:
                index_of_dialog = '0'
            try:
                if check_element_exists_by_ID(self.driver, 'mat-dialog-' + index_of_dialog):
                    if self.print_ > 1:
                        print('Found dialog')
                    self.driver.find_element(By.ID, 'mat-dialog-' + index_of_dialog).send_keys(Keys.ESCAPE)
                    if self.print_ > 1:
                        print('Closed dialog')
                    self.closed_fares_overlay = True
                else:
                    if self.print_ > 1:
                        print('No dialog found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error closing dialog: {e}')

        if self.print_ > 1:
            print('Exiting flights page')
            print('Going to next page')

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

        return fares
    
    def fill_text_input_fields(self, field, input):

        if self.print_ > 1:
            print(f'Filling text input field with {input}')
        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, field):
                if self.print_ > 1:
                    print('Found text input field')
                text_input = self.driver.find_element(By.CSS_SELECTOR, field)
                text_input.clear()
                text_input.send_keys(input)
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
            self.fill_text_input_fields("[id*='-0phoneCountryCode']", '+351')
            self.fill_text_input_fields("[id*='-0phone']", '912345678')
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

    def get_bags_and_info(self, fare_name):

        if self.print_ > 1:
            print('Getting bags and info')

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
                services = ul.find_elements(By.TAG_NAME, 'li')
                if self.print_ > 1:
                    print('Found li')
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
    
    def get_flight_seats(self, fare_name):

        if self.print_ > 1:
            print('Getting seats')
        
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
                    print('Found seats')
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
        for i in range(number_of_classes):    
            seats_info.append({'name': names[i], 'price': 'N/A', 'available_seats': 0, 'unavailable_seats': 0})

        try:
            if self.print_ > 1:
                print('Iterating over seats')
            for i in range(len(seats)):
                seat_button = self.driver.find_element(By.TAG_NAME, 'button')
                if self.check_seat_availability(seat_button) == 'available':
                    total_seats[0] += 1
                    if fare_name == 'Economy':
                        if compare_positions(seat_button, exit_icons[0]):
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
                                front = True
                            else:
                                seats_info[0]['available_seats'] += 1
                        elif compare_positions(seat_button, exit_icons[3]):
                            if not exit:
                                price = 'N/A'
                                self.click_with_retry(seat_button)
                                if check_element_exists_by_TAG_NAME(self.driver, 'mat-dialog-container'):
                                    dialog = self.driver.find_element(By.TAG_NAME, 'mat-dialog-container')
                                    if check_element_exists_by_CSS_SELECTOR(dialog, "[class*='price-amount']"):
                                        price = dialog.find_element(By.CSS_SELECTOR, "[class*='price-amount']").text.replace('.', ',')
                                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                seats_info[1]['price'] = price
                                seats_info[1]['available_seats'] += 1
                                exit = True
                            else:
                                seats_info[1]['available_seats'] += 1
                        else:
                            if not back:
                                price = 'N/A'
                                self.click_with_retry(seat_button)
                                if check_element_exists_by_TAG_NAME(self.driver, 'mat-dialog-container'):
                                    dialog = self.driver.find_element(By.TAG_NAME, 'mat-dialog-container')
                                    if check_element_exists_by_CSS_SELECTOR(dialog, "[class*='price-amount']"):
                                        price = dialog.find_element(By.CSS_SELECTOR, "[class*='price-amount']").text.replace('.', ',')
                                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                seats_info[2]['price'] = price
                                seats_info[2]['available_seats'] += 1
                                back = True
                            else:
                                seats_info[2]['available_seats'] += 1
                    else:
                        seats_info[0]['available_seats'] += 1
                else:
                    total_seats[1] += 1
                    if fare_name == 'Economy':
                        if compare_positions(seat_button, exit_icons[0]):
                            seats_info[0]['unavailable_seats'] += 1
                        elif compare_positions(seat_button, exit_icons[3]):
                            seats_info[1]['unavailable_seats'] += 1
                        else:
                            seats_info[2]['unavailable_seats'] += 1
                    else:
                        seats_info[0]['unavailable_seats'] += 1
            if self.print_ > 1:
                print('Iterated over seats')
        except Exception as e:
            if self.print_ > 2:
                print(f'Error getting seats: {e}')

    def close(self):
        self.driver.quit()

if __name__ == '__main__':
    # create the object
    aireuropa = AirEuropa(headless=True)

    filename = 'AirEuropa_' + time.strftime("%d-%m-%Y") + '.csv'
    file_exists = os.path.isfile(filename)
    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
    fares = ["Economy", "Business"]
    flights_details = []
    flights_seats = []

    aireuropa.fill_home_page_form('09/09/2024', 'LIS', 'MAD')
    flights = aireuropa.get_flights()
    if inputs.input_print_ > 2:
        print(f'Number of flights: {len(flights)}')

    for i in range(0,len(flights)):
        flight_id = '09-09-2024_' + 'LIS-' + 'MAD_' + str(i+1)
        details = aireuropa.get_flight_details(flights[i])
        airliner = 'AirEuropa'
        flights_details.append(details)
        for fare in fares:
            # Add logic to exclude flights that are sold out
            aireuropa.fill_home_page_form('09/09/2024', 'LIS', 'MAD')
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            flights = aireuropa.get_flights()
            if inputs.input_print_ > 2:
                print(f'Number of flights: {len(flights)}')
            fare_options = aireuropa.advance_to_form_page(flights[i], fare)
            aireuropa.fill_passenger_form()
            services = aireuropa.get_bags_and_info(fare)
            seats = aireuropa.get_flight_seats(fare)
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
            if(i == 0 and fare == "Economy"):
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
    aireuropa.close()            
                    
                    
                                                       

                                                        



        




            

                


        





    
            
