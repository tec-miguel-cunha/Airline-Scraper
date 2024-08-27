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

# timeout = inputs.input_timeout
# timeout_cookies = inputs.input_timeout_cookies
# timeout_little = inputs.input_timeout_little
# timeout_implicitly_wait = inputs.input_timeout_implicitly_wait
# cookies = inputs.input_cookies
# print_ = inputs.input_print_

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

class TAP:

    # TODO: 
    # - Test sold out flights
    ## - Add button logic to the fill_home_page_form function
    ## - Add button logic to the get_flight_seats function
    ## - Add print and timeout to inputs.py and implement logic
    ## - Add a way to check if the buttons are in view and scroll them into view if they are not

    


    def __init__(self, headless=True):

        self.timeout = inputs.input_timeout
        self.timeout_cookies = inputs.input_timeout_cookies
        self.timeout_little = inputs.input_timeout_little
        self.timeout_implicitly_wait = inputs.input_timeout_implicitly_wait
        self.cookies = inputs.input_cookies
        self.print_ = inputs.input_print_

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

    # def return_flight(self, flyout, flyback, orig, dest, adults='1', teens='0', children='0', infants='0'):
    #     # fly out and fly back dates must be formatted YEAR-MONTH-DAY
    #     # TODO - add flight duration

    #     # set the url
    #     url = f'https://www.ryanair.com/gb/en/trip/flights/select?adults=2&teens=0&children=0&infants=0&dateOut={flyout}&dateIn={flyback}&isConnectedFlight=false&discount=0&isReturn=true&promoCode=&originIata={orig}&destinationIata={dest}&tpAdults={adults}&tpTeens={teens}&tpChildren={children}&tpInfants={infants}&tpStartDate={flyout}&tpEndDate={flyback}&tpDiscount=0&tpPromoCode=&tpOriginIata={orig}&tpDestinationIata={dest}'

    #     # get the page
    #     self.driver.get(url)
    #     self.driver.implicitly_wait(10)

    #     # close cookies in button tag with cookie-popup-with-overlay__button class
    #     try:
    #         self.driver.find_element(By.CLASS_NAME, 'cookie-popup-with-overlay__button').click()

    #     except Exception as e:
            
    #         print(f'Error closing cookies: {e}')
    #         pass


    #     # get the page source
    #     page = self.driver.page_source

    #     # parse the page source
    #     soup = BeautifulSoup(page, 'html.parser')


    #     # get the departure and return dates
    #     day = soup.find_all('span',
    #                               class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm')

    #     if len(day) == 1:
    #         day = soup.find('span',
    #                             class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm').text
    #         month = soup.find('span',
    #                               class_='date-item__month date-item__month--selected body-xl-lg body-xl-sm').text
    #         months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    #         date = f'{day} {months.index(month)+1}'

    #         if date == flyout:
    #             return_date = 'No flights available on Return date'
    #             departure_date = f'{day} {month}'

    #             # get departure and arrival times
    #             departure_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
    #             arrival_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')

    #             departure_flyback_times = 'N/A'
    #             arrival_flyback_times = 'N/A'

    #         elif date == flyback:
    #             departure_date = 'No flights available on Departure date'
    #             return_date = f'{day} {month}'

    #             # get departure and arrival times
    #             departure_flyout_times = 'N/A'
    #             arrival_flyout_times = 'N/A'

    #             departure_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
    #             arrival_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')
    #         else:
    #             day = soup.find_all('span', class_='date-item__day-of-month body-xl-lg body-xl-sm')
    #     else:
    #         day = soup.find_all('span',
    #                             class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm')
    #         month = soup.find_all('span',
    #                               class_='date-item__month date-item__month--selected body-xl-lg body-xl-sm')
    #         departure_date = f'{day[0].text} {month[0].text}'
    #         return_date = f'{day[1].text} {month[1].text}'

    #         # get departure and arrival times
    #         departure_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
    #         arrival_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ','')

    #         departure_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')
    #         arrival_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[2].text.replace(' ', '')

    #     # get the prices
    #     prices = []
    #     for selection in soup.find_all('div', class_='date-item__price title-s-lg title-s-sm date-item__price--selected ng-star-inserted'):
    #         # get the price
    #         price = selection.find('ry-price', class_='price').text
    #         # remove blank spaces
    #         price = price.replace(' ', '')
    #         # append to the list
    #         prices.append(price)

    #     # create the dictionary
    #     prices = [{'Departure': {'date': departure_date, 'departure_time': departure_flyout_times, 'arrival_time': arrival_flyout_times, 'price': prices[0], }}, {'Return': {'date': return_date, 'departure_time': departure_flyback_times, 'arrival_time': arrival_flyback_times, 'price': prices[1], }}]

    #     return prices
    
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
    
    # def extract_info_from_popup(popup_text):
    #     # Define the regex pattern
    #     pattern = r"\d{1,2}[A-Z] - (Comfort|Exit Row|Standard) (\d+,\d{2}USD)"
        
    #     # Search for the pattern in the input string
    #     match = re.search(pattern, popup_text)
        
    #     if match:
    #         # Extract the keyword and value
    #         keyword = match.group(1)
    #         value = match.group(2)
    #         return keyword, value
    #     else:
    #         return "Standard", "0,00"

    # The error in this function is not returning the correct error in the cookies section, but let's keep it this way for now because it's working
    def fill_home_page_form(self, flyout, orig, dest, adults='1', teens='0', children='0', infants='0'):
        # set url
        url = f'https://www.flytap.com/en-us/'
        # get the page
        self.driver.get(url)
        if self.print_ > 1:    
            print('Opened TAP homepage')
        self.driver.implicitly_wait(self.timeout_implicitly_wait)

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
            self.driver.find_element(By.CSS_SELECTOR, "[class*='form-control bsdatepicker']").send_keys(flyout + Keys.RETURN)
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

    # def count_seats(self):
    #     try:
    #         seatmap = WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='seatmap__container']")))
    #         print('Seatmap loaded successfully')
    #     except Exception as e:
            
    #         print(f'Error waiting for seatmap to load: {e}')

    #     try:
    #         row_numbers = self.driver.find_elements(By.CSS_SELECTOR, "[class*='seatmap__seat seatmap__seat--aisle']")
    #         number_of_rows = len(row_numbers) + 1 # offset for row 13
    #         seats = []
    #         total_seats = [0, 0]
    #         seats_XL_front = [0, 0]
    #         seats_quick = [0, 0]
    #         seats_best_front = [0, 0]
    #         seats_XL_back = [0, 0]
    #         seats_best_back = [0, 0]
    #         for i in range(1, number_of_rows+1):
    #             if (i == 13):
    #                 continue
    #             else:
    #                 for letter in ['A', 'B', 'C', 'D', 'E', 'F']:
    #                     if (i == 1 and (letter == 'D' or letter == 'E' or letter == 'F')):
    #                         continue
    #                     if (i < 10):
    #                         seat = self.driver.find_element(By.CSS_SELECTOR, f"[id*='seat-0{i}{letter}']")
    #                     else:
    #                         seat = self.driver.find_element(By.CSS_SELECTOR, f"[id*='seat-{i}{letter}']")
    #                     if ((i == 1 and (letter == 'A' or letter == 'B' or letter == 'C')) or (i == 2 and (letter == 'D' or letter == 'E' or letter == 'F'))):
    #                         availability = self.check_seat_availability(seat)
    #                         if availability == 'available':
    #                             seats_XL_front[0] += 1
    #                             total_seats[0] += 1
    #                         else:
    #                             seats_XL_front[1] += 1
    #                             total_seats[1] += 1
    #                     else:
    #                         if ((i == 2 and (letter == 'A' or letter == 'B' or letter == 'C')) or i == 3 or i == 4 or i == 5):
    #                             availability = self.check_seat_availability(seat)
    #                             if availability == 'available':
    #                                 seats_quick[0] += 1
    #                                 total_seats[0] += 1
    #                             else:
    #                                 seats_quick[1] += 1
    #                                 total_seats[1] += 1
    #                         else:
    #                             if (i >= 6 and i <= 15):
    #                                 availability = self.check_seat_availability(seat)
    #                                 if availability == 'available':
    #                                     seats_best_front[0] += 1
    #                                     total_seats[0] += 1
    #                                 else:
    #                                     seats_best_front[1] += 1
    #                                     total_seats[1] += 1
    #                             else:
    #                                 if (i == 16 or i == 17):
    #                                     availability = self.check_seat_availability(seat)
    #                                     if availability == 'available':
    #                                         seats_XL_back[0] += 1
    #                                         total_seats[0] += 1
    #                                     else:
    #                                         seats_XL_back[1] += 1
    #                                         total_seats[1] += 1
    #                                 else:
    #                                     availability = self.check_seat_availability(seat)
    #                                     if availability == 'available':
    #                                         seats_best_back[0] += 1
    #                                         total_seats[0] += 1
    #                                     else:
    #                                         seats_best_back[1] += 1
    #                                         total_seats[1] += 1
    #                     seats.append(seat)
    #         print('Seats counted successfully')
    #         print(f'Total Seats counted {total_seats}')
    #         print(f'Seats XL Front counted {seats_XL_front}')
    #         print(f'Seats Quick counted {seats_quick}')
    #         print(f'Seats Best Front counted {seats_best_front}')
    #         print(f'Seats XL Back counted {seats_XL_back}')
    #         print(f'Seats Best Back counted {seats_best_back}')
    #         extra_price_seats_elements = seatmap.find_elements(By.CSS_SELECTOR, "[class*='price__integers']")
    #         extra_price_seats = []
    #         for extra_price_seats_element in extra_price_seats_elements:
    #             extra_price_seats.append(extra_price_seats_element.text.replace(' ', ''))
    #         seats_data = {
    #             'total_seats_available': total_seats[0],
    #             'total_seats_unavailable': total_seats[1],
    #             'price_XL_front': extra_price_seats[0],
    #             'seats_XL_front_available': seats_XL_front[0],
    #             'seats_XL_front_unavailable': seats_XL_front[1],
    #             'price_quick': extra_price_seats[1],
    #             'seats_quick_available': seats_quick[0],
    #             'seats_quick_unavailable': seats_quick[1],
    #             'price_best_front': extra_price_seats[3],
    #             'seats_best_front_available': seats_best_front[0],
    #             'seats_best_front_unavailable': seats_best_front[1],
    #             'price_XL_back': extra_price_seats[4],
    #             'seats_XL_back_available': seats_XL_back[0],
    #             'seats_XL_back_unavailable': seats_XL_back[1],
    #             'price_best_back': extra_price_seats[5],
    #             'seats_best_back_available': seats_best_back[0],
    #             'seats_best_back_unavailable': seats_best_back[1]
    #         }      
    #     except Exception as e:
    #         print(f'Error counting seats: {e}')
    
    #     return seats_data

    # def advance_to_seats(self):
    #     # click the button
    #     try:
    #         self.driver.find_element(By.CSS_SELECTOR, "[class*='flight-card-summary__select-btn']").click()
    #         print('Continuing to seats')
    #     except Exception as e:
            
    #         print(f'Error continuing to seats: {e}')

    #     # get the page source
    #     page = self.driver.page_source

    #     # parse the page source
    #     soup = BeautifulSoup(page, 'html.parser')

    #     try:
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e*='fare-card--']")))
    #         fare_headers = self.driver.find_elements(By.CSS_SELECTOR, "[data-e2e*='fare-card--']")
    #         print('Trying to get fares')
    #         fares = []
    #         for fare_header in fare_headers:
    #             fare_name = fare_header.find_element(By.CSS_SELECTOR, "[class*='fare-header__name']").text
    #             fare_price_tag = fare_header.find_element(By.CSS_SELECTOR, "[class*='price']")
    #             fare_price = fare_price_tag.find_element(By.CSS_SELECTOR, "[class*='price__integers']").text + ',' + fare_price_tag.find_element(By.CSS_SELECTOR, "[class*='price__decimals']").text
    #             fare_price = fare_price.replace(' ', '')
    #             fare = {
    #                 'name': fare_name,
    #                 'price': fare_price
    #             }
    #             fares.append(fare)
    #         print('Fares gotten successfully')
    #         print('Trying to click on BASIC fare')
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='fare-header__submit-btn']")))
    #         basic_fare_button = self.driver.find_element(By.CSS_SELECTOR, "[class*='fare-header__submit-btn']")
    #         self.driver.execute_script("arguments[0].click();", basic_fare_button)
    #     except Exception as e:
    #         print(f'Error getting fares or clicking BASIC fare: {e}')

    #     print(fares)

    #     try:
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='fare-footer__submit-btn']")))
    #         basic_fare_button_popup = self.driver.find_elements(By.CSS_SELECTOR, "[class*='fare-footer__submit-btn']")[0]
    #         self.driver.execute_script("arguments[0].click();", basic_fare_button_popup)
    #         print('Selected BASIC fare on popup')
    #     except Exception as e:
            
    #         print(f'Error selecting BASIC fare on Popup: {e}')

    #     try:
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='login-touchpoint__expansion-bar']")))
    #         self.driver.find_element(By.CSS_SELECTOR, "[class*='login-touchpoint__expansion-bar']").click()
    #         print('Continue without login')
    #     except Exception as e:
            
    #         print(f'Error continuing without login: {e}')

    #     try:
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='dropdown__toggle']")))
    #         self.driver.find_element(By.CSS_SELECTOR, "[class*='dropdown__toggle']").click()
    #         print('Clicked dropdown for gender')
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='dropdown-item__link']")))
    #         self.driver.find_elements(By.CSS_SELECTOR, "[class*='dropdown-item__link']")[0].click()
    #         print('Selected Sr.')
    #         self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.name']").send_keys('Miguel')
    #         print('Entered first name')
    #         self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.surname']").send_keys('Cunha')
    #         print('Entered last name')
    #     except Exception as e:
            
    #         print(f'Error entering name: {e}')
        
    #     try:
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='continue-flow__button']")))
    #         self.driver.find_element(By.CSS_SELECTOR, "[class*='continue-flow__button']").click()
    #         print('Clicked on continue button')
    #     except Exception as e:
            
    #         print(f'Error clicking on continue button: {e}')

    #     # try:
    #     #     WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='booking-page']")))
    #     #     print('New page loaded successfully')
    #     #     # Add code to interact with the new page here
    #     # except Exception as e:
            
    #     #     print(f'Error waiting for new page to load: {e}')

    #     try:
    #         WebDriverWait(self.driver, timeout=self.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='ry-radio-button--0']")))
    #         radio_button_small_bag = self.driver.find_element(By.CSS_SELECTOR, "[id*='ry-radio-button--0']")
    #         self.driver.execute_script("arguments[0].click();", radio_button_small_bag)
    #         print('Selected small bag')
    #     except Exception as e:
            
    #         print(f'Error selecting small bag: {e}')

    #     # IT IS STRANGE THAT THIS IS NOT NEEDED. MIGHT BE A PROBLEM TO CHECK IN THE FUTURE
    #     # try:
    #     #     self.driver.find_element(By.CSS_SELECTOR, "[class*='bags-continue-button']").click()
    #     #     print('Clicked on continue button')
    #     # except Exception as e:
            
    #     #     print(f'Error clicking on continue button: {e}')     

    # close the driver
    def close(self):
        if self.print_ > 1:
            print('Closing the driver')
        self.driver.close()
        


# test
if __name__ == '__main__':
    # create the object
    tap = TAP(headless=True)

    # tap.driver.execute_script(mutation_observer_script)

    # get the data

    filename = 'TAP_' + time.strftime("%d-%m-%Y") + '.csv'
    file_exists = os.path.isfile(filename)
    file_not_empty = os.path.getsize(filename) > 0 if file_exists else False
    fares = ["Economy", "Business"]
    flights_details = []
    flights_seats = []

    tap.fill_home_page_form('09/09/2024', 'LIS', 'MAD')
    flights = tap.get_flights()
    if inputs.input_print_ > 2:
        print(f'Number of flights: {len(flights)}')

    for i in range(0,len(flights)):
        flight_id = '09-09-2024_' + 'LIS-' + 'MAD_' + str(i+1)
        airliner, details = tap.get_flight_details(flights[i])
        flights_details.append(details)
        for fare in fares:
            # Add logic to exclude flights that are sold out
            if (details['price_' + fare.lower()] == 'Sold Out'):
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                seats = {
                    'fare': fare,
                    'seat_price': 'N/A',
                    'total_seats_available': 'Sold Out',
                    'total_seats_unavailable': 'Sold Out',
                    'price_bag': 'N/A',
                    'price_preferred_boarding': 'N/A',
                    'seats_comfort_available': 'Sold Out',
                    'seats_comfort_unavailable': 'Sold Out',
                    'seats_emergency_available': 'Sold Out',
                    'seats_emergency_unavailable': 'Sold Out',
                    'seats_standard_available': 'Sold Out',
                    'seats_standard_unavailable': 'Sold Out',
                    'seats_business_available': 'N/A',
                    'seats_business_unavailable': 'N/A'
                }
            else:
                tap.fill_home_page_form('09/09/2024', 'LIS', 'MAD')
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                flights = tap.get_flights()
                seats = tap.get_flight_seats(flights[i], fare)
                flights_seats.append(seats)
            data = {
                'time': current_time,
                'airliner': airliner,
                'flight_ID': flight_id,
                'details': details,
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
    tap.close()
