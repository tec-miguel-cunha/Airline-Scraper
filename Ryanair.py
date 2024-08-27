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
        driver.find_element(By.CSS_SELECTOR, css)
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

class RyanAir:

    def __init__(self, headless=True):

        self.timeout = inputs.input_timeout
        self.timeout_cookies = inputs.input_timeout_cookies
        self.timeout_little = inputs.input_timeout_little
        self.timeout_implicitly_wait = inputs.input_timeout_implicitly_wait
        self.cookies = inputs.input_cookies
        self.print_ = inputs.input_print_

        self.buttons = []

        if self.print_ > 1:
            print('Initializing RyanAir')
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = uc.Chrome()
        if self.print_ > 1:
            print('Initialized RyanAir')

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

    def get_flights(self, flyout, orig, dest, adults='1', teens='0', children='0', infants='0'):
        # set url
        if self.print_ > 1:
            print('Getting flights')
        
        formatted_date = datetime.strptime(flyout, '%Y/%m/%d').strftime('%Y-%m-%d')

        url = f'https://www.ryanair.com/gb/en/trip/flights/select?adults=2&teens=0&children=0&infants=0&dateOut={formatted_date}&dateIn=&isConnectedFlight=false&discount=0&isReturn=false&promoCode=&originIata={orig}&destinationIata={dest}&tpAdults={adults}&tpTeens={teens}&tpChildren={children}&tpInfants={infants}&tpStartDate={flyout}&tpEndDate=&tpDiscount=0&tpPromoCode=&tpOriginIata={orig}&tpDestinationIata={dest}'
        self.driver.get(url)
        if self.cookies == "not accepted":
            try:
                if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-ref*='cookie.accept-all']"):
                    self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[data-ref*='cookie.accept-all']"))
                    self.cookies = "accepted"
                    if self.print_ > 1:
                        print('Accepted cookies on cookie banner')
                else:
                    if self.print_ > 1:
                        print('No cookies banner found')
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error accepting cookies: {e}')
        
        if check_element_exists_by_TAG_NAME(self.driver, 'flight-card-new'):
            if self.print_ > 1:
                print('Found flight-card-new: one card with a flight')
            try:
                flight_list = self.driver.find_element(By.TAG_NAME, 'flight-list')
                flights = flight_list.find_elements(By.TAG_NAME, 'flight-card-new')
                if self.print_ > 1:
                    print('Found flight cards')
                return flights
            except Exception as e:
                if self.print_ > 0:
                    print(f'Error getting flights: {e}')
                return None
    
    def get_flight_details(self, flight):

        if self.print_ > 1:
            print('Getting flight details')
        
        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='date-item__day-of-month--selected']"):
                day = self.driver.find_element(By.CSS_SELECTOR, "[class*='date-item__day-of-month--selected']").text
                month = self.driver.find_element(By.CSS_SELECTOR, "[class*='date-item__month--selected']").text.replace('.', '')
                departure_date = f'{day} {month}'
                if self.print_ > 2:
                    print(f'Departure date: {departure_date}')
            else:
                departure_date = 'N/A'
                if self.print_ > 0:
                    print('Date not found')
        except Exception as e:
            departure_date = 'N/A'
            if self.print_ > 0:
                print(f'Error getting departure date: {e}')
        
        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[data-ref*='flight-segment.departure']"):
                departure_div = flight.find_element(By.CSS_SELECTOR, "[data-ref*='flight-segment.departure']")
                departure_flyout_times = departure_div.find_element(By.CSS_SELECTOR, "[class*='flight-info__hour']").text.replace(' ', '')
                if self.print_ > 2:
                    print(f'Departure time: {departure_flyout_times}')
            else:
                departure_flyout_times = 'N/A'
                if self.print_ > 0:
                    print('Departure time not found')
        except Exception as e:
            departure_flyout_times = 'N/A'
            if self.print_ > 0:
                print(f'Error getting departure time: {e}')
        
        try:
            if check_element_exists_by_CSS_SELECTOR(flight, "[data-ref*='flight-segment.arrival']"):
                arrival_div = flight.find_element(By.CSS_SELECTOR, "[data-ref*='flight-segment.arrival']")
                arrival_flyout_times = arrival_div.find_element(By.CSS_SELECTOR, "[class*='flight-info__hour']").text.replace(' ', '')
                if self.print_ > 2:
                    print(f'Arrival time: {arrival_flyout_times}')
            else:
                arrival_flyout_times = 'N/A'
                if self.print_ > 0:
                    print('Arrival time not found')
        except Exception as e:
            arrival_flyout_times = 'N/A'
            if self.print_ > 0:
                print(f'Error getting arrrival time: {e}')

        try:
            if check_element_exists_by_TAG_NAME(flight, 'flights-price-simple'):
                price_element = flight.find_element(By.TAG_NAME, 'flights-price-simple')
                price = price_element.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ',' + price_element.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                price = price.replace(' ', '')
            else:
                price = 'N/A'
                if self.print_ > 0:
                    print('Price not found')
        except Exception as e:
            price = 'N/A'
            if self.print_ > 0:
                print(f'Error getting price: {e}')
        
        details = {
            'date': departure_date,
            'departure_time': departure_flyout_times,
            'arrival_time': arrival_flyout_times,
            'price': price
            }
        
        return details

    def check_seat_availability(self, seat):
        try:
            seat_class = seat.get_attribute("class")
            if "seatmap__seat--unavailable" in seat_class:
                return 'unavailable'
            else:
                return 'available'
        except Exception as e:
            
            print(f'Error checking seat {seat.get_attribute("id")} availability: {e}')

    def get_flight_seats(self):
        if self.print_ > 1:
            print('Getting flight seats')
        try:
            if self.print_ > 1:
                print('Checking for seatmap')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='seatmap__container']"):
                seatmap = self.driver.find_element(By.CSS_SELECTOR, "[class*='seatmap__container']")
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
            row_numbers = self.driver.find_elements(By.CSS_SELECTOR, "[class*='seatmap__seat seatmap__seat--aisle']")
            number_of_rows = len(row_numbers) + 1 # offset for row 13
            seats = []
            total_seats = [0, 0]
            seats_XL_front = [0, 0]
            seats_quick = [0, 0]
            seats_best_front = [0, 0]
            seats_XL_back = [0, 0]
            seats_best_back = [0, 0]
            for i in range(1, number_of_rows+1):
                if (i == 13):
                    continue
                else:
                    for letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                        if (i == 1 and (letter == 'D' or letter == 'E' or letter == 'F')):
                            continue
                        if (i < 10):
                            seat = self.driver.find_element(By.CSS_SELECTOR, f"[id*='seat-0{i}{letter}']")
                        else:
                            seat = self.driver.find_element(By.CSS_SELECTOR, f"[id*='seat-{i}{letter}']")
                        if ((i == 1 and (letter == 'A' or letter == 'B' or letter == 'C')) or (i == 2 and (letter == 'D' or letter == 'E' or letter == 'F'))):
                            availability = self.check_seat_availability(seat)
                            if availability == 'available':
                                seats_XL_front[0] += 1
                                total_seats[0] += 1
                            else:
                                seats_XL_front[1] += 1
                                total_seats[1] += 1
                        else:
                            if ((i == 2 and (letter == 'A' or letter == 'B' or letter == 'C')) or i == 3 or i == 4 or i == 5):
                                availability = self.check_seat_availability(seat)
                                if availability == 'available':
                                    seats_quick[0] += 1
                                    total_seats[0] += 1
                                else:
                                    seats_quick[1] += 1
                                    total_seats[1] += 1
                            else:
                                if (i >= 6 and i <= 15):
                                    availability = self.check_seat_availability(seat)
                                    if availability == 'available':
                                        seats_best_front[0] += 1
                                        total_seats[0] += 1
                                    else:
                                        seats_best_front[1] += 1
                                        total_seats[1] += 1
                                else:
                                    if (i == 16 or i == 17):
                                        availability = self.check_seat_availability(seat)
                                        if availability == 'available':
                                            seats_XL_back[0] += 1
                                            total_seats[0] += 1
                                        else:
                                            seats_XL_back[1] += 1
                                            total_seats[1] += 1
                                    else:
                                        availability = self.check_seat_availability(seat)
                                        if availability == 'available':
                                            seats_best_back[0] += 1
                                            total_seats[0] += 1
                                        else:
                                            seats_best_back[1] += 1
                                            total_seats[1] += 1
                        seats.append(seat)
            if self.print_ > 1:
                print('Seats counted successfully')
            if self.print_ > 2:
                print(f'Total Seats counted {total_seats}')
                print(f'Seats XL Front counted {seats_XL_front}')
                print(f'Seats Quick counted {seats_quick}')
                print(f'Seats Best Front counted {seats_best_front}')
                print(f'Seats XL Back counted {seats_XL_back}')
                print(f'Seats Best Back counted {seats_best_back}')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error counting seats: {e}')
            
        try:
            if self.print_ > 1:
                print('Getting extra prices')
            extra_price_seats_elements = seatmap.find_elements(By.CSS_SELECTOR, "[class*='priceband__pricetag']")
            extra_price_seats = []
            XL_front = False
            quick = False
            best_front = False
            XL_back = False
            best_back = False
            for extra_price_seats_element in extra_price_seats_elements:
                extra_price = '0'
                if "--dark-blue" in extra_price_seats_element.get_attribute("class") and not XL_front:
                    extra_price = extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ','
                    if check_element_exists_by_CSS_SELECTOR(extra_price_seats_element, "[class*='price__decimals']"):
                        extra_price = extra_price + extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                    else:
                        extra_price = extra_price + '00'
                    extra_price = extra_price.replace(' ', '')
                    extra_price = extra_price.replace('\n', '')
                    extra_price = extra_price.replace('€', '')
                    extra_price_seats.append({'area': 'XL Front', 'price': extra_price})
                    XL_front = True
                if "--yellow" in extra_price_seats_element.get_attribute("class") and not quick:
                    extra_price = extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ','
                    if check_element_exists_by_CSS_SELECTOR(extra_price_seats_element, "[class*='price__decimals']"):
                        extra_price = extra_price + extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                    else:
                        extra_price = extra_price + '00'
                    extra_price = extra_price.replace(' ', '')
                    extra_price = extra_price.replace('\n', '')
                    extra_price = extra_price.replace('€', '')
                    extra_price_seats.append({'area': 'Quick', 'price': extra_price})
                    quick = True
                if "--light-blue" in extra_price_seats_element.get_attribute("class") and not best_front:
                    extra_price = extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ','
                    if check_element_exists_by_CSS_SELECTOR(extra_price_seats_element, "[class*='price__decimals']"):
                        extra_price = extra_price + extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                    else:
                        extra_price = extra_price + '00'
                    extra_price = extra_price.replace(' ', '')
                    extra_price = extra_price.replace('\n', '')
                    extra_price = extra_price.replace('€', '')
                    extra_price_seats.append({'area': 'Best Front', 'price': extra_price})
                    best_front = True
                if "--dark-blue" in extra_price_seats_element.get_attribute("class") and not XL_back:
                    extra_price = extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ','
                    if check_element_exists_by_CSS_SELECTOR(extra_price_seats_element, "[class*='price__decimals']"):
                        extra_price = extra_price + extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                    else:
                        extra_price = extra_price + '00'
                    extra_price = extra_price.replace(' ', '')
                    extra_price = extra_price.replace('\n', '')
                    extra_price = extra_price.replace('€', '')
                    extra_price_seats.append({'area': 'XL Back', 'price': extra_price})
                    XL_back = True
                if "--light-blue" in extra_price_seats_element.get_attribute("class") and not best_back:
                    extra_price = extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ','
                    if check_element_exists_by_CSS_SELECTOR(extra_price_seats_element, "[class*='price__decimals']"):
                        extra_price = extra_price + extra_price_seats_element.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                    else:
                        extra_price = extra_price + '00'
                    extra_price = extra_price.replace(' ', '')
                    extra_price = extra_price.replace('\n', '')
                    extra_price = extra_price.replace('€', '')
                    extra_price_seats.append({'area': 'Best Back', 'price': extra_price})
                    best_back = True
            
            seats_data = {
                'total_seats_available': total_seats[0],
                'total_seats_unavailable': total_seats[1],
                'seats_info': extra_price_seats,
                'seats_XL_front_available': seats_XL_front[0],
                'seats_XL_front_unavailable': seats_XL_front[1],
                'seats_quick_available': seats_quick[0],
                'seats_quick_unavailable': seats_quick[1],
                'seats_best_front_available': seats_best_front[0],
                'seats_best_front_unavailable': seats_best_front[1],
                'seats_XL_back_available': seats_XL_back[0],
                'seats_XL_back_unavailable': seats_XL_back[1],
                'seats_best_back_available': seats_best_back[0],
                'seats_best_back_unavailable': seats_best_back[1]
            }     

        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting extra prices: {e}')
        
        return seats_data

    def fill_form_flights_page(self):
        
        if self.print_ > 1:
            print('Filling form on flights page')

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='flight-card-summary__select-btn']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='flight-card-summary__select-btn']"))
                # TODO: Implement button logic
                if self.print_ > 2:
                    print('Clicked on select button')
            else:
                if self.print_ > 0:
                    print('Select button not found')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking select button: {e}')

        fares = []

        try:
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[data-e2e*='fare-card--']"):
                fare_headers = self.driver.find_elements(By.CSS_SELECTOR, "[data-e2e*='fare-card--']")
                if self.print_ > 1:
                    print('Trying to get fares')
                for fare_header in fare_headers:
                    fare_name = fare_header.find_element(By.CSS_SELECTOR, "[class*='fare-header__name']").text
                    fare_price_tag = fare_header.find_element(By.CSS_SELECTOR, "[class*='price']")
                    fare_price = fare_price_tag.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ',' + fare_price_tag.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                    fare_price = fare_price.replace(' ', '')
                    fare = {
                        'name': fare_name,
                        'price': fare_price
                    }
                    fares.append(fare)
                if self.print_ > 1:
                    print('Fares gotten successfully')
            else:
                if self.print_ > 0:
                    print('Fares not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting fares: {e}')
            # TODO: Implement button logic to solve the problem
            
        try:
            if self.print_ > 1:
                print('Trying to click on BASIC fare')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='fare-header__submit-btn']"):
                basic_fare_button = self.driver.find_element(By.CSS_SELECTOR, "[class*='fare-header__submit-btn']")
                self.click_with_retry(basic_fare_button)
            else:
                if self.print_ > 0:
                    print('BASIC fare button not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
            if self.print_ > 1:
                print('Clicked on BASIC fare')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking BASIC fare: {e}')

        try:
            if self.print_ > 1:
                print('Trying to click on BASIC fare on popup')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='fare-footer__submit-btn']"):
                basic_fare_button_popup = self.driver.find_elements(By.CSS_SELECTOR, "[class*='fare-footer__submit-btn']")[0]
                self.click_with_retry(basic_fare_button_popup)
                if self.print_ > 1:
                    print('Selected BASIC fare on popup')
            else:
                if self.print_ > 0:
                    print('BASIC fare button on popup not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting BASIC fare on Popup: {e}')
            # TODO: Implement button logic to solve the problem

        try:
            if self.print_ > 1:
                print('Trying to continue without login')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='login-touchpoint__expansion-bar']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='login-touchpoint__expansion-bar']"))
                if self.print_ > 1:
                    print('Continue without login')
            else:
                if self.print_ > 0:
                    print('Continue without login button not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error continuing without login: {e}')
            # TODO: Implement button logic to solve the problem

        try:
            if self.print_ > 1:
                print('Trying to enter title')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='dropdown__toggle']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='dropdown__toggle']"))
                if self.print_ > 1:
                    print('Clicked dropdown')
            else:
                if self.print_ > 0:
                    print('Dropdown for title not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking dropdown for title: {e}. Trying to solve the problem')
            # TODO: Implement button logic to solve the problem
        
        try:
            if self.print_ > 1:
                print('Trying to select Sr.')
            
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='dropdown-item__link']"):
                self.click_with_retry(self.driver.find_elements(By.CSS_SELECTOR, "[class*='dropdown-item__link']")[0])
                if self.print_ > 1:
                    print('Selected Sr.')
            else:
                if self.print_ > 0:
                    print('Sr. not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting Sr.: {e}. Trying to solve the problem')
            # TODO: Implement button logic to solve the problem
    
        try:
            if self.print_ > 1:
                print('Trying to enter first name')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[id*='form.passengers.ADT-0.name']"):
                self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.name']").send_keys('Miguel')
                if self.print_ > 1:
                    print('Entered first name')
            else:
                if self.print_ > 0:
                    print('First name input not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering first name: {e}. Trying to solve the problem')
            # TODO: Implement button logic to solve the problem
        
        try:
            if self.print_ > 1:
                print('Trying to enter last name')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[id*='form.passengers.ADT-0.surname']"):
                self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.surname']").send_keys('Cunha')
                if self.print_ > 1:
                    print('Entered last name')
            else:
                if self.print_ > 0:
                    print('Last name input not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error entering last name: {e}. Trying to solve the problem')
            # TODO: Implement button logic to solve the problem

        try:
            if self.print_ > 1:
                print('Trying to click on continue button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='continue-flow__button']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='continue-flow__button']"))
                if self.print_ > 1:
                    print('Clicked on continue button')
            else:
                if self.print_ > 0:
                    print('Continue button not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on continue button: {e}. Trying to solve the problem')
            # TODO: Implement button logic to solve the problem
        
        if self.print_ > 1:
            print('Continuing to baggage page')
        
        return fares
            

    

        # try:
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='fare-footer__submit-btn']")))
        #     basic_fare_button_popup = self.driver.find_elements(By.CSS_SELECTOR, "[class*='fare-footer__submit-btn']")[0]
        #     self.driver.execute_script("arguments[0].click();", basic_fare_button_popup)
        #     print('Selected BASIC fare on popup')
        # except Exception as e:
            
        #     print(f'Error selecting BASIC fare on Popup: {e}')

        # try:
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='login-touchpoint__expansion-bar']")))
        #     self.driver.find_element(By.CSS_SELECTOR, "[class*='login-touchpoint__expansion-bar']").click()
        #     print('Continue without login')
        # except Exception as e:
            
        #     print(f'Error continuing without login: {e}')

        # try:
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='dropdown__toggle']")))
        #     self.driver.find_element(By.CSS_SELECTOR, "[class*='dropdown__toggle']").click()
        #     print('Clicked dropdown for gender')
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='dropdown-item__link']")))
        #     self.driver.find_elements(By.CSS_SELECTOR, "[class*='dropdown-item__link']")[0].click()
        #     print('Selected Sr.')
        #     self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.name']").send_keys('Miguel')
        #     print('Entered first name')
        #     self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.surname']").send_keys('Cunha')
        #     print('Entered last name')
        # except Exception as e:
            
        #     print(f'Error entering name: {e}')
        
        # try:
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='continue-flow__button']")))
        #     self.driver.find_element(By.CSS_SELECTOR, "[class*='continue-flow__button']").click()
        #     print('Clicked on continue button')
        # except Exception as e:
            
        #     print(f'Error clicking on continue button: {e}')

        # try:
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='booking-page']")))
        #     print('New page loaded successfully')
        #     # Add code to interact with the new page here
        # except Exception as e:
            
        #     print(f'Error waiting for new page to load: {e}')

        # try:
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='ry-radio-button--0']")))
        #     radio_button_small_bag = self.driver.find_element(By.CSS_SELECTOR, "[id*='ry-radio-button--0']")
        #     self.driver.execute_script("arguments[0].click();", radio_button_small_bag)
        #     print('Selected small bag')
        # except Exception as e:
        #     print(f'Error selecting small bag: {e}')

        # IT IS STRANGE THAT THIS IS NOT NEEDED. MIGHT BE A PROBLEM TO CHECK IN THE FUTURE
        # try:
        #     self.driver.find_element(By.CSS_SELECTOR, "[class*='bags-continue-button']").click()
        #     print('Clicked on continue button')
        # except Exception as e:
            
        #     print(f'Error clicking on continue button: {e}')     

    def get_info_luggage_page(self):
        if self.print_ > 1:
            print('Getting luggage info')
        
        try:
            if self.print_ > 1:
                print('Trying to wait for radio button to load')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[id*='ry-radio-button--0']"):
                radio_button_small_bag = self.driver.find_element(By.CSS_SELECTOR, "[id*='ry-radio-button--0']")
                self.click_with_retry(radio_button_small_bag)
                if self.print_ > 1:
                    print('Selected small bag')
            else:
                if self.print_ > 0:
                    print('Small bag radio button not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error selecting small bag: {e}. Trying to solve the problem')
            # TODO: Implement button logic to solve the problem
        
        try:
            if self.print_ > 1:
                print('Trying to get extra luggage prices')
            luggage_prices = {'10 Kg': 'N/A', '20 Kg': 'N/A'}
            if check_element_exists_by_TAG_NAME(self.driver, 'bags-checkin-bag-table-controls'):
                extra_luggage_div = self.driver.find_element(By.TAG_NAME, 'bags-checkin-bag-table-controls')

                # 10 Kg bag
                ten_kg_bag_div = extra_luggage_div.find_element(By.TAG_NAME, 'bags-ten-kg-bags')
                extra_price_ten_kg = ten_kg_bag_div.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ','
                if check_element_exists_by_CSS_SELECTOR(ten_kg_bag_div, "[class*='price__decimals']"):
                    extra_price_ten_kg = extra_price_ten_kg + ten_kg_bag_div.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                else:
                    extra_price_ten_kg = extra_price_ten_kg + '00'
                extra_price_ten_kg = extra_price_ten_kg.replace(' ', '')
                extra_price_ten_kg = extra_price_ten_kg.replace('\n', '')
                extra_price_ten_kg = extra_price_ten_kg.replace('€', '')
                luggage_prices['10 Kg'] = extra_price_ten_kg

                # 20 Kg bag
                twenty_kg_bag_div = extra_luggage_div.find_element(By.TAG_NAME, 'bags-twenty-kg-bags')
                extra_price_twenty_kg = twenty_kg_bag_div.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ','
                if check_element_exists_by_CSS_SELECTOR(ten_kg_bag_div, "[class*='price__decimals']"):
                    extra_price_twenty_kg = extra_price_twenty_kg + ten_kg_bag_div.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
                else:
                    extra_price_twenty_kg = extra_price_twenty_kg + '00'
                extra_price_twenty_kg = extra_price_twenty_kg.replace(' ', '')
                extra_price_twenty_kg = extra_price_twenty_kg.replace('\n', '')
                extra_price_twenty_kg = extra_price_twenty_kg.replace('€', '')
                luggage_prices['20 Kg'] = extra_price_twenty_kg
            else:
                if self.print_ > 0:
                    print('Extra luggage prices not found')
            if self.print_ > 1 and luggage_prices['10 Kg'] != 'N/A' and luggage_prices['20 Kg'] != 'N/A':
                print('Extra luggage prices gotten successfully')
        except Exception as e:
            if self.print_ > 0:
                print(f'Error getting extra luggage prices: {e}')


        try:
            if self.print_ > 1:
                print('Trying to click on continue button')
            if check_element_exists_by_CSS_SELECTOR(self.driver, "[class*='bags-continue-button']"):
                self.click_with_retry(self.driver.find_element(By.CSS_SELECTOR, "[class*='bags-continue-button']"))
                if self.print_ > 1:
                    print('Clicked on continue button')
            else:
                if self.print_ > 0:
                    print('Continue button not found. Trying to solve the problem')
                # TODO: Implement button logic to solve the problem
        except Exception as e:
            if self.print_ > 0:
                print(f'Error clicking on continue button: {e}. Trying to solve the problem')
            # TODO: Implement button logic to solve the problem
        
        if self.print_ > 1:
            print('Continuing to seats page')

        return luggage_prices
            
    # close the driver
    def close(self):
        self.driver.close()
        


# test
if __name__ == '__main__':
    # create the object
    ryanair = RyanAir(headless=True)

    filename = 'RyanAir_' + time.strftime("%d-%m-%Y") + '.csv'
    file_exists = os.path.isfile(filename)
    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
    airliner = 'Ryanair'
    flights_details = []
    flights_seats = []

    # get the data
    flights = ryanair.get_flights('2024/09/09', 'LIS', 'MAD')

    if inputs.input_print_ > 2:
        print(f'Number of flights: {len(flights)}')

    if flights is not None:
        for i in range(0, len(flights)):
            flight_id = '09-09-2024_' + 'LIS-' + 'MAD_' + str(i+1)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            flights = ryanair.get_flights('2024-09-09', 'LIS', 'MAD')
            details = ryanair.get_flight_details(flights[i])
            flights_details.append(details)
            fares = ryanair.fill_form_flights_page()
            luggage_prices = ryanair.get_info_luggage_page()
            seats = ryanair.get_flight_seats()
            flights_seats.append(seats)
            data = {
                'time': current_time,
                'airliner': airliner,
                'flight_ID': flight_id,
                'details': details,
                'fares': fares,
                'luggage_prices': luggage_prices,
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


    if ryanair.print_ > 1:
        print(flights_details)
        print(flights_seats)

    # close the driver
    ryanair.close()
