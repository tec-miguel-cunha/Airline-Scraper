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

current_origin = "Lisbon"
current_destination = "Madrid"
current_origin_code = "LIS"
current_destination_code = "MAD"
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

def check_element_exists_by_XPATH(driver, xpath, timeout=inputs.input_timeout_checks):
    element_exists = False
    if inputs.input_print_ > 1:
        print(f'Checking if element exists by XPATH: {xpath}')
    try:
        WebDriverWait(driver, timeout=timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
        if inputs.input_print_ > 1:
            print("Passed WebDriverWait")
        element_exists = True
    except Exception as e:
        if inputs.input_print_ > 0:
            print(f'No element by XPATH: {e}')
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

class Iberia:

    def __init__(self, headless=True):

        self.timeout = inputs.input_timeout
        self.timeout_cookies = inputs.input_timeout_cookies
        self.timeout_little = inputs.input_timeout_little
        self.timeout_implicitly_wait = inputs.input_timeout_implicitly_wait
        self.timeout_retry_click = inputs.input_timeout_retry_click
        self.print_ = inputs.input_print_
        self.cookies = 'not accepted'
        self.GDPR = 'not accepted'
        self.closed_popup_cabin_bags = False
        self.new_tab_opened = False
        self.closed_fares_overlay = False
        self.searched = False
        self.saved_data = False

        self.buttons = []

        if self.print_ > 1:
            print('Initializing Iberia')
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = uc.Chrome()
        if self.print_ > 1:
            print('Initialized Iberia')

    def click_with_retry(self, element, retries=3, delay=1):
        if self.print_ > 1:
            print('Clicking with retry')
        for attempt in range(retries):
            try:
                # Check if the element is clickable
                WebDriverWait(self.driver, timeout=self.timeout_retry_click).until(EC.element_to_be_clickable(element))
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

    def fill_home_page_form(self, flyout, orig, dest, adults='1', teens='0', children='0', infants='0'):
        if self.print_ > 1:
            print('Entering Fill Form Function')
        # set url
        url = f'https://www.iberia.com/gb/?language=en'
        # get the page
        self.driver.get(url)
        if self.print_ > 1:    
            print('Opened Iberia homepage')
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

        try:
            if self.print_ > 1:
                print('Getting form fields')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='ibe-searcher__row--col1 ibe-searcher__options']"):
                one_way_departure_and_destination_form = self.driver.find_element(By.CSS_SELECTOR, "[class='ibe-searcher__row--col1 ibe-searcher__options']")
                if self.print_ > 1:
                    print('Found form fields')
            else:
                if self.print_ > 1:
                    print('No form fields found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting form fields: {e}')

        try:
            if self.print_ > 1:
                print('Trying to choose one way option in select')
            if check_element_exists_by_TAG_NAME(one_way_departure_and_destination_form, 'select'):
                select_element = one_way_departure_and_destination_form.find_element(By.TAG_NAME, 'select')
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
            if check_element_exists_by_ID(one_way_departure_and_destination_form, 'flight_origin1'):
                origin = one_way_departure_and_destination_form.find_element(By.ID, 'flight_origin1')
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
            if check_element_exists_by_ID(one_way_departure_and_destination_form, 'flight_destiny1'):
                destination = one_way_departure_and_destination_form.find_element(By.ID, 'flight_destiny1')
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
                print('Trying to write flyout date')
            if check_element_exists_by_ID(self.driver, 'flight_round_date1'):
                flyout_date = one_way_departure_and_destination_form.find_element(By.ID, 'flight_round_date1')
                flyout_date.send_keys(flyout)
                time.sleep(1)
                flyout_date.send_keys(Keys.RETURN)
                if self.print_ > 1:
                    print('Entered flyout date')
            else:
                if self.print_ > 1:
                    print('No flyout date field found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to enter flyout date: {e}')

        try:
            if self.print_ > 1:
                print('Trying to click search button')
            if check_element_exists_by_ID(self.driver, 'buttonSubmit1'):
                search_button = one_way_departure_and_destination_form.find_element(By.ID, 'buttonSubmit1')
                self.click_with_retry(search_button)
                if self.print_ > 1:
                    print('Clicked search button')
            else:
                if self.print_ > 1:
                    print('No search button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Exception occurred trying to click search button: {e}')

        if self.print_ > 1:
            print('Exiting fill home page form function')
            print('Going to next page')

    def get_to_flights(self, flyout=current_flyout_date, orig_name=current_origin , orig=current_origin_code, dest_name=current_destination, dest=current_destination_code, repeat=True):
        if self.print_ > 1:
            print('Entering get to flights function')

        day_2_digits, month, year = flyout.split('/')

        year_and_month_2_digits = year + month
        
        page_url = f'https://www.iberia.com/flights/?market=PT&language=en&appliesOMB=false&splitEndCity=false&initializedOMB=true&flexible=true&TRIP_TYPE=1&BEGIN_CITY_01={orig}&END_CITY_01={dest}&nombreOrigen={orig_name}&nombreDestino={dest_name}&BEGIN_DAY_01={day_2_digits}&BEGIN_MONTH_01={year_and_month_2_digits}&BEGIN_YEAR_01={year}&END_DAY_01=&END_MONTH_01=&END_YEAR_01=&FARE_TYPE=R&quadrigam=IBHMPA&ADT=1&CHD=0&INF=0&BNN=0&YTH=0&YCD=0&residentCode=&familianumerosa=&BV_UseBVCookie=no&boton=Search&bookingMarket=PT#!/availability'

        self.driver.get(page_url)

        if self.print_ > 1:
            print('Opened Iberia flights page')
        
        self.driver.implicitly_wait(self.timeout_implicitly_wait)

        if repeat:
            if self.print_ > 1:
                print('Refreshing page and waiting for page to load')
            time.sleep(2)
            self.driver.refresh()
            time.sleep(5)

        try:
            if self.print_ > 1:
                print('Trying to close loading overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='ib-loading-container']"):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[class*='ib-loading-container']")))
                if self.print_ > 1:
                    print('Closed loading overlay')
            else:
                if self.print_ > 1:
                    print('No loading overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing loading overlay: {e}')


        if self.cookies == 'not accepted':
            try:
                if self.print_ > 1:
                    print('Trying to close cookies popup')
                if check_element_exists_by_ID(self.driver, 'onetrust-banner-sdk'):
                    cookies_popup = self.driver.find_element(By.ID, 'onetrust-banner-sdk')
                    if self.print_ > 1:
                        print('Found cookies popup')
                    if check_element_exists_by_ID(cookies_popup, 'onetrust-accept-btn-handler'):
                        accept_button = cookies_popup.find_element(By.ID, 'onetrust-accept-btn-handler')
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

        time.sleep(5)

        try:
            if self.print_ > 1:
                print('Checking for problems showing flights')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class='ib-error-amadeus__title']", timeout=2):
                error = self.driver.find_element(By.CSS_SELECTOR, "[class='ib-error-amadeus__title']").text
                if self.print_ > 1:
                    print(f'Error showing flights')
                return "Error"
            else:
                if self.print_ > 1:
                    print('No problems showing flights')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error checking for problems showing flights: {e}')

        try:
            if self.print_ > 1:
                print('Trying to close popup')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='mntt-scrollable-details-wrapper']"):
                popup = self.driver.find_element(By.CSS_SELECTOR, "[class*='mntt-scrollable-details-wrapper']")
                if self.print_ > 1:
                    print('Found popup')
                if check_element_exists_by_TAG_NAME(popup, 'label'):
                    close_button = popup.find_element(By.TAG_NAME, 'label')
                    self.click_with_retry(close_button)
                    if self.print_ > 1:
                        print('Clicked close button')
                else:
                    if self.print_ > 1:
                        print('No close button found')
            else:
                if self.print_ > 1:
                    print('No popup found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing popup: {e}')

        try:
            if self.print_ > 1:
                print('Getting flights div')
            if check_element_exists_by_TAG_NAME(self.driver, 'ib-booking-trip-info'):
                flights_div = self.driver.find_element(By.TAG_NAME, 'ib-booking-trip-info')
                if self.print_ > 1:
                    print('Found flights div')
            else:
                if self.print_ > 1:
                    print('No flights div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flights div: {e}')

        try:
            if self.print_ > 1:
                print('Getting flights')
            if check_element_exists_by_TAG_NAME(flights_div, 'ib-booking-slice-info'):
                flights = flights_div.find_elements(By.TAG_NAME, 'ib-booking-slice-info')
                if self.print_ > 1:
                    print('Found flights')
            else:
                if self.print_ > 1:
                    print('No flights found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting flights: {e}')

        if self.print_ > 1:
            print('Exiting get to flights function')
            print('Returning flights')

        return flights
    
    def get_flight_details(self, flights, index, repeat = False):

        if self.print_ > 1:
            print('Entering get flight details function')

        if repeat:
            flight = self.get_to_flights()[index]
        else:
            flight = flights[index]

        try:
            if self.print_ > 1:
                print('Getting flight departure time')
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='ib-info-journey__content-time--left']"):
                departure_time_div = flight.find_element(By.CSS_SELECTOR, "[class*='ib-info-journey__content-time--left']")
                if self.print_ > 1:
                    print('Found departure time div')
                if check_element_exists_by_TAG_NAME(departure_time_div, 'span'):
                    departure_time = departure_time_div.find_element(By.TAG_NAME, 'span').text
                    departure_time = departure_time.replace('\n', '').replace(' ', '').replace('\"', '')
                    if self.print_ > 1:
                        print('Found departure time')
                else:
                    if self.print_ > 1:
                        print('No departure time found')
            else:
                if self.print_ > 1:
                    print('No departure time div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting departure time: {e}')

        try:
            if self.print_ > 1:
                print('Getting flight arrival time')
            if check_element_exists_by_CSS_SELECTOR(flight, "[class*='ib-info-journey__content-time--right']"):
                arrival_time_div = flight.find_element(By.CSS_SELECTOR, "[class*='ib-info-journey__content-time--right']")
                if self.print_ > 1:
                    print('Found arrival time div')
                if check_element_exists_by_TAG_NAME(arrival_time_div, 'span'):
                    arrival_time = arrival_time_div.find_element(By.TAG_NAME, 'span').text
                    arrival_time = arrival_time.replace('\n', '').replace(' ', '').replace('\"', '')
                    if self.print_ > 1:
                        print('Found arrival time')
                else:
                    if self.print_ > 1:
                        print('No arrival time found')
            else:
                if self.print_ > 1:
                    print('No arrival time div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting arrival time: {e}')

        prices = []


        try:
            if self.print_ > 1:
                print('Getting flight prices')

            if check_element_exists_by_TAG_NAME(flight, 'button'):
                prices_buttons = flight.find_elements(By.TAG_NAME, 'button')
                if self.print_ > 1:
                    print('Found prices')
                for price_button in prices_buttons:
                    if price_button.get_attribute('disabled') is not None:
                        if self.print_ > 1:
                            print('Price button is disabled')
                        if check_element_exists_by_CSS_SELECTOR(price_button, "[class='ib-box-mini-fare__box-title']"):
                            fare = price_button.find_element(By.CSS_SELECTOR, "[class='ib-box-mini-fare__box-title']").text
                            prices.append({'name': fare, 'price': 'Sold Out'})
                        
                    else:
                        if check_element_exists_by_CSS_SELECTOR(price_button, "[class='ib-box-mini-fare__box-title']"):
                            fare = price_button.find_element(By.CSS_SELECTOR, "[class='ib-box-mini-fare__box-title']").text
                            if self.print_ > 2:
                                print(f'Found fare: {fare}')
                            price = price_button.find_element(By.CSS_SELECTOR, "[class='ib-box-mini-fare__box-price']").text
                            if self.print_ > 2:
                                print(f'Found price: {price}')
                            prices.append({'name': fare, 'price': price})
            else:
                if self.print_ > 1:
                    print('No prices found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting prices: {e}')

        if self.print_ > 1:
            print('Exiting get flight details function')
            print('Returning flight details')

        return {'departure_time': departure_time, 'arrival_time': arrival_time, 'prices': prices}
     
    def advance_to_passenger_form_page(self, flights, index, fare_name=current_fare_name, repeat = False):

        if self.print_ > 1:
            print('Entering advance to passenger form page function')

        if repeat:
            flight = self.get_to_flights()[index]
        else:
            flight = flights[index]

        try:
            if self.print_ > 1:
                print('Getting specific fare button')
            if check_element_exists_by_TAG_NAME(flight, 'button'):
                prices_buttons = flight.find_elements(By.TAG_NAME, 'button')
                if self.print_ > 1:
                    print('Found prices')
                if fare_name == 'Economy':
                    button_index = 0
                else:
                    button_index = 1
                if prices_buttons[button_index].get_attribute('disabled') is not None:
                    return "Continue"
                button_to_click = prices_buttons[button_index]
                if self.print_ > 1:
                    print('Found button to click')
                self.click_with_retry(button_to_click)
                if self.print_ > 1:
                    print('Clicked button')
            else:
                if self.print_ > 1:
                    print('No prices found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting specific fare button: {e}')

        fares = []
        
        try:
            if self.print_ > 1:
                print('Getting booking fare details')
            if check_element_exists_by_TAG_NAME(self.driver, 'ib-booking-fare-details'):
                fare_details_divs = self.driver.find_elements(By.TAG_NAME, 'ib-booking-fare-details')
                for i in range(len(fare_details_divs)):
                    if check_element_exists_by_CSS_SELECTOR(fare_details_divs[i], "[class='ib-box-select-radio__header-left']"):
                        fare_name_div = fare_details_divs[i].find_element(By.CSS_SELECTOR, "[class='ib-box-select-radio__header-left']")
                        fare_name = fare_name_div.find_element(By.TAG_NAME, 'a').text
                        if self.print_ > 2:
                            print(f'Found fare details: {fare_name}')
                        if check_element_exists_by_CSS_SELECTOR(fare_details_divs[i], "[class='ib-box-select-radio__header-right']"):
                            fare_price_div = fare_details_divs[i].find_element(By.CSS_SELECTOR, "[class='ib-box-select-radio__header-right']")
                            fare_price = fare_price_div.find_element(By.TAG_NAME, 'span').text
                            if self.print_ > 2:
                                print(f'Found fare details: {fare_name} - {fare_price}')
                        else:
                            if self.print_ > 1:
                                print('No fare price found')
                    else:
                        if self.print_ > 1:
                            print('No fare name found')
                    fare = {'name': fare_name, 'price': fare_price}
                    fares.append(fare)
            else:
                if self.print_ > 1:
                    print('No booking fare details found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting booking fare details: {e}')


        try:
            if self.print_ > 1:
                print('Getting continue button')
            if check_element_exists_by_ID(self.driver, 'totalprice-availability-continue-flow'):
                continue_button_div = self.driver.find_element(By.ID, 'totalprice-availability-continue-flow')
                if self.print_ > 1:
                    print('Found continue button div')
                if check_element_exists_by_TAG_NAME(continue_button_div, 'button'):
                    continue_button = continue_button_div.find_element(By.TAG_NAME, 'button')
                    self.click_with_retry(continue_button)
                    if self.print_ > 1:
                        print('Clicked continue button')
                else:
                    if self.print_ > 1:
                        print('No continue button found')
            else:
                if self.print_ > 1:
                    print('No continue button div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting continue button: {e}')

        if self.print_ > 1:
            print('Exiting advance to passenger form page function')
            print('Returning fares')

        return fares
    
    def fill_text_input_fields(self, field, input, tab=False, timeout=inputs.input_timeout_checks):

        if self.print_ > 1:
            print(f'Filling text input field with {input}')
        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, field, timeout=timeout):
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
    
    def fill_passenger_form(self, first_name = "Miguel", last_name = "Cunha", email = "abc@gmail.com", phone = "123456789"):

        if self.print_ > 1:
            print('Entering fill passenger form function')

        try:
            if self.print_ > 1:
                print('Trying to close loading overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[id='bbki-loading-plane-loading-elem']", self.timeout_little):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[id='bbki-loading-plane-loading-elem']")))
                if self.print_ > 1:
                    print('Closed loading overlay')
            else:
                if self.print_ > 1:
                    print('No loading overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing loading overlay: {e}')  
            

        try:
            if self.print_ > 1:
                print('Filling text fields')
            self.fill_text_input_fields("[id='name_0']", first_name, timeout=self.timeout_little)
            self.fill_text_input_fields("[id='first_surname_0']", last_name)
            self.fill_text_input_fields("[id='IBAIRP_CONTACT_FORM_EMAIL']", email)
            self.fill_text_input_fields("[id='IBAIRP_CONTACT_FORM_REPEATED_EMAIL']", email)
            self.fill_text_input_fields("[id='IBAIRP_CONTACT_FORM_PHONE']", phone)
            if self.print_ > 1:
                print('Filled text fields')	
        except Exception as e:
            if self.print_ > 0:
                print(f'Error filling text fields: {e}')

        # try:
        #     if self.print_ > 1:
        #         print('Clicking on remember data checkbox')
        #     if check_element_exists_by_ID(self.driver, 'save_passengers_data'):
        #         remember_checkbox = self.driver.find_element(By.ID, 'save_passengers_data')
        #         if remember_checkbox.is_selected():
        #             if self.print_ > 1:
        #                 print('Checkbox already checked')
        #         else:
        #             remember_checkbox.click()
        #             if self.print_ > 1:
        #                 print('Clicked on remember data checkbox')
        #         if self.print_ > 1:
        #             print('Clicked on remember data checkbox')
        #         self.saved_data = True
        #     else:
        #         if self.print_ > 1:
        #             print('No remember data checkbox found')
        # except Exception as e:
        #     if self.print_ > 0:
        #         print(f'Error clicking on remember data checkbox: {e}')

        try:
            if self.print_ > 1:
                print('Clicking continue button')
            if check_element_exists_by_ID(self.driver, 'AVAILABILITY_CONTINUE_BUTTON'):
                continue_button = self.driver.find_element(By.ID, 'AVAILABILITY_CONTINUE_BUTTON')
                self.click_with_retry(continue_button)
                if self.print_ > 1:
                    print('Clicked continue button')
            else:
                if self.print_ > 1:
                    print('No continue button found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking continue button: {e}')


        if self.print_ > 1:
            print('Exiting fill passenger form function')
            print('Going to next page')

    def get_bag_info(self):

        if self.print_ > 1:
            print('Entering get bag info function')

        try:
            if self.print_ > 1:
                print('Trying to close loading overlay')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[id='bbki-loading-plane-loading-elem']", self.timeout_little):
                WebDriverWait(self.driver, timeout=self.timeout).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[id='bbki-loading-plane-loading-elem']")))
                if self.print_ > 1:
                    print('Closed loading overlay')
            else:
                if self.print_ > 1:
                    print('No loading overlay found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error closing loading overlay: {e}')

        infos = []

        try:
            if self.print_ > 1:
                print('Trying to get the infos in bags and info page')
            
            if check_element_exists_by_TAG_NAME(self.driver, 'ib-baggages-box'):
                baggages_div = self.driver.find_element(By.TAG_NAME, 'ib-baggages-box')
                if self.print_ > 1:
                    print('Found baggages div')
                if check_element_exists_by_CSS_SELECTOR(baggages_div, "[class='ib-box-card__subtitle']"):
                    price = baggages_div.find_element(By.CSS_SELECTOR, "[class='ib-box-card__subtitle']").text
                    if self.print_ > 1:
                        print('Found price')
                    # Get only the number from price string
                    price = re.findall(r'\d+', price)[0]
                    info = {'name': 'Extra Bag', 'price': price}
                    infos.append(info)
                else:
                    if self.print_ > 1:
                        print('No price found')
            else:
                if self.print_ > 1:
                    print('No baggages div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting the infos in bags and info page: {e}')

        # do the same thing but the first tag name to look for is ib-ancillaries-components and we are doing for accillaries
        try:
            if self.print_ > 1:
                print('Trying to get the infos in accillaries and info page')
            
            if check_element_exists_by_TAG_NAME(self.driver, 'ib-ancillaries-components'):
                accillaries_div = self.driver.find_element(By.TAG_NAME, 'ib-ancillaries-components')
                if self.print_ > 1:
                    print('Found accillaries div')
                if check_element_exists_by_CSS_SELECTOR(accillaries_div, "[class='ib-box-card__subtitle']"):
                    price = accillaries_div.find_element(By.CSS_SELECTOR, "[class='ib-box-card__subtitle']").text
                    if self.print_ > 1:
                        print('Found price')
                    # Get only the number from price string
                    price = re.findall(r'\d+', price)[0]
                    info = {'name': 'Extra Bag', 'price': price}
                    infos.append(info)
                else:
                    if self.print_ > 1:
                        print('No price found')
            else:
                if self.print_ > 1:
                    print('No accillaries div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting the infos in accillaries and info page: {e}')

        try:
            if self.print_ > 1:
                print('Clicking on seats button')
            if check_element_exists_by_TAG_NAME(self.driver, 'ib-seat-map-box'):
                seats_div = self.driver.find_element(By.TAG_NAME, 'ib-seat-map-box')
                if self.print_ > 1:
                    print('Found seats div')
                if check_element_exists_by_TAG_NAME(seats_div, 'button'):
                    seats_button = seats_div.find_element(By.TAG_NAME, 'button')
                    self.click_with_retry(seats_button)
                    if self.print_ > 1:
                        print('Clicked on seats button')
                else:
                    if self.print_ > 1:
                        print('No seats button found')
            else:
                if self.print_ > 1:
                    print('No seats div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on seats button: {e}')

        if self.print_ > 1:
            print('Exiting get bag info function')
            print('Returning infos')

        return infos

    def check_seat_availability(self, seat):
        if self.print_ > 1:
            print('Entering check seat availability function')

        seat_class = seat.get_attribute('class')

        if '--occupied' not in seat_class:
            if '--upfront' in seat_class:
                return 'upfront', 'Available'
            elif '--emergency' in seat_class:
                return 'emergency', 'Available'
            elif '--comfort' in seat_class:
                return 'comfort', 'Available'
            elif '--free' in seat_class:
                return 'free', 'Available'
            elif '--promo' in seat_class:
                return 'promo', 'Available'
            elif '--gap' in seat_class:
                return 'gap', 'N/A'
        else:
            return 'N/A', 'Unavailable'
    
    def get_seats(self, fare_name=current_fare_name):

        if self.print_ > 1:
            print('Entering get seats function')

        try:
            if self.print_ > 1:
                print('Getting seatmap')
            if fare_name == 'Economy':
                field = f"[data-index='cabins-2']"
            else:
                field = f"[data-index='cabins-1']"
            if check_element_exists_by_CSS_SELECTOR(self.driver, field):
                seatmap = self.driver.find_element(By.CSS_SELECTOR, field)
                if self.print_ > 1:
                    print('Found seatmap')
            else:
                if self.print_ > 1:
                    print('No seatmap found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting seatmap: {e}')

        # rows = seatmap.find_elements(By.TAG_NAME, 'ul')
        # with open('seatmap.txt', 'w') as f:
        #     add = 1
        #     for i in range(len(rows)):
        #         if i > 12:
        #             add = 2
        #         f.write(f'Row {i+add}: {rows[i].get_attribute("class")}\n')

        try:
            if self.print_ > 1:
                print('Getting seats')
            if check_element_exists_by_TAG_NAME(seatmap, 'li'):
                seats = seatmap.find_elements(By.TAG_NAME, 'li')
                if self.print_ > 1:
                    print('Found seats')
                if self.print_ > 2:
                    print(f'Found {len(seats)} seats')
            else:
                if self.print_ > 1:
                    print('No seats found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting seats: {e}')
            
        seats_infos = []

        try:
            if self.print_ > 1:
                print('Opening seat legend')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='ib-map-seats__leyend-button']"):
                legend_button = self.driver.find_element(By.CSS_SELECTOR, "[class*='ib-map-seats__leyend-button']")
                self.click_with_retry(legend_button)
                if self.print_ > 1:
                    print('Clicked on seat legend')
            else:
                if self.print_ > 1:
                    print('No seat legend found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error opening seat legend: {e}')

        time.sleep(5)

        try:
            if self.print_ > 1:
                print('Getting zones prices')
            # check by class *= ib-map-seats__leyend-block
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='ib-map-seats__leyend-block']"):
                zones_div = self.driver.find_element(By.CSS_SELECTOR, "[class*='ib-map-seats__leyend-block']")
                if self.print_ > 1:
                    print('Found zones div')
                if check_element_exists_by_TAG_NAME(zones_div, 'ul'):
                    zones_list = zones_div.find_elements(By.TAG_NAME, 'ul')[0]
                    if self.print_ > 1:
                        print('Found zones list')
                    zone_items = zones_list.find_elements(By.TAG_NAME, 'li')
                    if self.print_ > 1:
                        print('Found zone items')
                    for zone_item in zone_items:
                        data_hover = zone_item.get_attribute('data-hover')
                        price = zone_item.find_element(By.TAG_NAME, 'div')
                        price_text = price.text
                        if self.print_ > 2:
                            print(f'Zone: {data_hover} - Price element: {price} - Price text: {price_text}')
                        # Get only number from price string
                        price_text = re.findall(r'\d+', price_text)[0]
                        seat_info = {'name': data_hover, 'price': price_text, 'available': 0, 'unavailable': 0}
                        seats_infos.append(seat_info)
                else:
                    if self.print_ > 1:
                        print('No zones list found')
            else:
                if self.print_ > 1:
                    print('No zones div found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting zones prices: {e}')

        if fare_name == 'Economy':
            for seat_info in seats_infos:
                print(seat_info)
                if seat_info['name'] == 'promo':
                    price_promo = seat_info['price']
            seats_infos.append({'name': 'free', 'price': int(price_promo)+2, 'available': 0, 'unavailable': 0})
        else:
            seats_infos.append({'name': 'free', 'price': 0, 'available': 0, 'unavailable': 0})

        zone = 'upfront'

        try:
            if self.print_ > 1:
                print('Getting seats availability')

            for seat in seats:
                seat_zone, seat_availability = self.check_seat_availability(seat)
                if seat_zone == 'gap':
                    continue
                if seat_availability == 'Available':
                    zone = seat_zone
                    for seat_info in seats_infos:
                        if seat_zone == seat_info['name']:
                            seat_info['available'] += 1
                else:
                    for seat_info in seats_infos:
                        if zone == seat_info['name']:
                            seat_info['unavailable'] += 1
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting seats availability: {e}')

        if self.print_ > 1:
            print('Exiting get seats function')
            print('Returning seats infos')

        return seats_infos


if __name__ == "__main__":
        
    iberia = Iberia(headless=False)
    filename = 'Iberia_' + time.strftime("%d-%m-%Y") + '.csv'
    file_exists = os.path.isfile(filename)
    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
    airliner = 'Iberia'
    flights_details = []
    flights_seats = []
    flyout = current_flyout_date
    origin_code = current_origin_code
    origin_name = current_origin
    destination_code = current_destination_code
    destination_name = current_destination
    fare_name = current_fare_name

    fare_names = ['Economy', 'Business']

    flights = iberia.get_to_flights(flyout=flyout, orig_name=origin_name, orig=origin_code, dest_name=destination_name, dest=destination_code, repeat=False)

    if flights == "Error":
        print("Error")
        iberia.driver.quit()
        iberia = Iberia(headless=False)
        flights = iberia.get_to_flights(flyout=flyout, orig_name=origin_name, orig=origin_code, dest_name=destination_name, dest=destination_code)
        if flights == "Error":
            print("Error")
            iberia.driver.quit()
            exit()
    if iberia.print_ > 2:
        print(f'Found {len(flights)} flights')

    if flights is not None:
        for i in range(len(flights)):
            flight_id = flyout.replace('/', '-') + '_' + origin_code + '-' + destination_code + '_' + str(i+1)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for j in range(len(fare_names)):
                observation_id = f'{flight_id}_{fare_names[j]}'
                current_fare_name = fare_names[j]
                if not (i == 0 and j == 0):
                    flights = iberia.get_to_flights(flyout=current_flyout_date, orig_name=current_origin, orig=current_origin_code, dest_name=current_destination, dest=current_destination_code)
                    if flights == "Error":
                        print("Error")
                        iberia.driver.quit()
                        iberia = Iberia(headless=False)
                        flights = iberia.get_to_flights(flyout=flyout, orig_name=origin_name, orig=origin_code, dest_name=destination_name, dest=destination_code)
                        if flights == "Error":
                            print("Error")
                            iberia.driver.quit()
                            exit()
                details = iberia.get_flight_details(flights, index = i)
                flights_details.append(details)
                fares = iberia.advance_to_passenger_form_page(flights, index = i, fare_name = fare_names[j])
                if fares == "Continue":
                    data = {
                        'time': current_time,
                        'airliner': airliner,
                        'flight_ID': flight_id,
                        'observation_id': observation_id,
                        'details': details,
                    }
                else:
                    iberia.fill_passenger_form()
                    infos = iberia.get_bag_info()
                    seats = iberia.get_seats()
                    flights_seats.append(seats)
                    data = {
                        'time': current_time,
                        'airliner': airliner,
                        'flight_ID': flight_id,
                        'observation_id': observation_id,
                        'details': details,
                        'fares': fares,
                        'infos': infos,
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
                        write_to_csv_row(writer, data, first)
                else:
                    with open(filename, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        write_to_csv_row(writer, data)

    if iberia.print_ > 2:
        print(flights_details)
        print(flights_seats)

    iberia.driver.quit()


        


    

# if __name__ == "__main__":

#     iberia = Iberia(headless=False)
#     flights = iberia.get_to_flights(flyout=current_flyout_date, orig_name=current_origin, orig=current_origin_code, dest_name=current_destination, dest=current_destination_code)
#     if flights == "Error":
#         print("Error")
#         iberia.driver.quit()
#         iberia = Iberia(headless=False)
#         flights = iberia.get_to_flights(flyout=current_flyout_date, orig_name=current_origin, orig=current_origin_code, dest_name=current_destination, dest=current_destination_code, repeat=True)
#         if flights == "Error":
#             print("Error")
#             iberia.driver.quit()
#             exit()
#     print(f'Found {len(flights)} flights')
#     flight_details = iberia.get_flight_details(flights, 1)
#     print(flight_details)
#     fares = iberia.advance_to_passenger_form_page(flights, 1)
#     if fares == "Continue":
#         print("Continue")
#         # Go to next iteration
#     print(fares)
#     iberia.fill_passenger_form(first_name="Miguel", last_name="Cunha", email="abc@gmail.com", phone="123456789")
#     infos = iberia.get_bag_info()
#     print(infos)
#     print(iberia.get_seats())
#     time.sleep(50)
#     iberia.driver.quit()
        
