# import libraries
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import json
import re

timeout = 1000

class RyanAir:

    def __init__(self, headless=True):
        chromedriver_autoinstaller.install()
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            # options.add_argument('--headless')
            # options.add_argument('--no-sandbox')
            # options.add_argument('--disable-dev-shm-usage')
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = uc.Chrome()

    def return_flight(self, flyout, flyback, orig, dest, adults='1', teens='0', children='0', infants='0'):
        # fly out and fly back dates must be formatted YEAR-MONTH-DAY
        # TODO - add flight duration

        # set the url
        url = f'https://www.ryanair.com/gb/en/trip/flights/select?adults=2&teens=0&children=0&infants=0&dateOut={flyout}&dateIn={flyback}&isConnectedFlight=false&discount=0&isReturn=true&promoCode=&originIata={orig}&destinationIata={dest}&tpAdults={adults}&tpTeens={teens}&tpChildren={children}&tpInfants={infants}&tpStartDate={flyout}&tpEndDate={flyback}&tpDiscount=0&tpPromoCode=&tpOriginIata={orig}&tpDestinationIata={dest}'

        # get the page
        self.driver.get(url)
        self.driver.implicitly_wait(10)

        # close cookies in button tag with cookie-popup-with-overlay__button class
        try:
            self.driver.find_element(By.CLASS_NAME, 'cookie-popup-with-overlay__button').click()

        except Exception as e:
            
            print(f'Error closing cookies: {e}')
            pass


        # get the page source
        page = self.driver.page_source

        # parse the page source
        soup = BeautifulSoup(page, 'html.parser')


        # get the departure and return dates
        day = soup.find_all('span',
                                  class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm')

        if len(day) == 1:
            day = soup.find('span',
                                class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm').text
            month = soup.find('span',
                                  class_='date-item__month date-item__month--selected body-xl-lg body-xl-sm').text
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            date = f'{day} {months.index(month)+1}'

            if date == flyout:
                return_date = 'No flights available on Return date'
                departure_date = f'{day} {month}'

                # get departure and arrival times
                departure_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
                arrival_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')

                departure_flyback_times = 'N/A'
                arrival_flyback_times = 'N/A'

            elif date == flyback:
                departure_date = 'No flights available on Departure date'
                return_date = f'{day} {month}'

                # get departure and arrival times
                departure_flyout_times = 'N/A'
                arrival_flyout_times = 'N/A'

                departure_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
                arrival_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')
            else:
                day = soup.find_all('span', class_='date-item__day-of-month body-xl-lg body-xl-sm')
        else:
            day = soup.find_all('span',
                                class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm')
            month = soup.find_all('span',
                                  class_='date-item__month date-item__month--selected body-xl-lg body-xl-sm')
            departure_date = f'{day[0].text} {month[0].text}'
            return_date = f'{day[1].text} {month[1].text}'

            # get departure and arrival times
            departure_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
            arrival_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ','')

            departure_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')
            arrival_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[2].text.replace(' ', '')

        # get the prices
        prices = []
        for selection in soup.find_all('div', class_='date-item__price title-s-lg title-s-sm date-item__price--selected ng-star-inserted'):
            # get the price
            price = selection.find('ry-price', class_='price').text
            # remove blank spaces
            price = price.replace(' ', '')
            # append to the list
            prices.append(price)

        # create the dictionary
        prices = [{'Departure': {'date': departure_date, 'departure_time': departure_flyout_times, 'arrival_time': arrival_flyout_times, 'price': prices[0], }}, {'Return': {'date': return_date, 'departure_time': departure_flyback_times, 'arrival_time': arrival_flyback_times, 'price': prices[1], }}]

        return prices

    def get_prices_one_way_flight(self, flyout, orig, dest, adults='1', teens='0', children='0', infants='0'):
        # set url
        url = f'https://www.ryanair.com/gb/en/trip/flights/select?adults=2&teens=0&children=0&infants=0&dateOut={flyout}&dateIn=&isConnectedFlight=false&discount=0&isReturn=false&promoCode=&originIata={orig}&destinationIata={dest}&tpAdults={adults}&tpTeens={teens}&tpChildren={children}&tpInfants={infants}&tpStartDate={flyout}&tpEndDate=&tpDiscount=0&tpPromoCode=&tpOriginIata={orig}&tpDestinationIata={dest}'
        # get the page
        self.driver.get(url)
        self.driver.implicitly_wait(10)

        # close cookies in button tag with cookie-popup-with-overlay__button class
        try:
            # wait till button with class name cookie-popup-with-overlay__button is clickable
            WebDriverWait(self.driver, timeout=timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ("[data-ref='cookie.accept-all']"))))
            # Q: what do i need to import for EC?
            # A: from selenium.webdriver.support import expected_conditions as EC
            # click the button
            print('Cookies about to be closed')
            self.driver.find_element(By.CSS_SELECTOR, ("[data-ref='cookie.accept-all']")).click()
            print('Cookies closed')
        except Exception as e:
            
            print(f'Error closing cookies: {e}')


        # get the page source
        page = self.driver.page_source

        # parse the page source
        soup = BeautifulSoup(page, 'html.parser')

        # wait until the element is loaded
        # wait = WebDriverWait(self.driver, 10)
        WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='date-item__day-of-month date-item__day-of-month--selected']")))
        # element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.date-item__day-of-month.date-item__day-of-month--selected.body-xl-lg.body-xl-sm")))

        # get data
        if soup.find('span', class_=re.compile('date-item__day-of-month date-item__day-of-month--selected')) is None:
            print('No flights available on selected date OR invalid input OR invalid class name')
            departure_date = 'No flights available on selected date'
            departure_flyout_times = 'N/A'
            arrival_flyout_times = 'N/A'
        else:
            day = soup.find('span', class_=re.compile('date-item__day-of-month date-item__day-of-month--selected')).text
            month = soup.find('span', class_=re.compile('date-item__month date-item__month--selected')).text
            departure_date = f'{day} {month}'
            # get departure and arrival times
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ref*='flight-segment.departure']")))
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ref*='flight-segment.arrival']")))
            departure_div = self.driver.find_element(By.CSS_SELECTOR, "[data-ref*='flight-segment.departure']")
            departure_flyout_times = departure_div.find_element(By.CSS_SELECTOR, "[class*='flight-info__hour']").text.replace(' ', '')
            arrival_div = self.driver.find_element(By.CSS_SELECTOR, "[data-ref*='flight-segment.arrival']")
            arrival_flyout_times = arrival_div.find_element(By.CSS_SELECTOR, "[class*='flight-info__hour']").text.replace(' ', '')
            print(f'Departure date: {departure_date}')
            print(f'Departure time: {departure_flyout_times}')
            print(f'Arrival time: {arrival_flyout_times}')
            print(f'Travel Times Done')
            # departure_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
            # arrival_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')


        # FIXME: SOMETIMES THE PRICES ARE NOT LOADED
        # get the prices
        prices = []
        for selection in soup.find_all('div', class_='date-item__price title-s-lg title-s-sm date-item__price--selected ng-star-inserted'):
            # get the price
            # self.driver.implicitly_wait(10)
            
            #wait = WebDriverWait(self.driver, 10)
            #wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'ry-price.price')))
            price = selection.find('ry-price', class_='price').text
            # remove blank spaces
            price = price.replace(' ', '')
            # append to the list
            prices.append(price)

        if prices == []:
            prices = ['No flights available']

        # create the dictionary
        prices = [{'Departure': {'date': departure_date, 'departure_time': departure_flyout_times, 'arrival_time': arrival_flyout_times, 'price': prices[0], }}]

        return prices
    
    def check_seat_availability(self, seat):
        try:
            seat_class = seat.get_attribute("class")
            if "seatmap__seat--unavailable" in seat_class:
                return 'unavailable'
            else:
                return 'available'
        except Exception as e:
            
            print(f'Error checking seat {seat.get_attribute("id")} availability: {e}')

    def count_seats(self):
        try:
            seatmap = WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='seatmap__container']")))
            print('Seatmap loaded successfully')
        except Exception as e:
            
            print(f'Error waiting for seatmap to load: {e}')

        try:
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
            print('Seats counted successfully')
            print(f'Total Seats counted {total_seats}')
            print(f'Seats XL Front counted {seats_XL_front}')
            print(f'Seats Quick counted {seats_quick}')
            print(f'Seats Best Front counted {seats_best_front}')
            print(f'Seats XL Back counted {seats_XL_back}')
            print(f'Seats Best Back counted {seats_best_back}')
            extra_price_seats_elements = seatmap.find_elements(By.CSS_SELECTOR, "[class*='price__integers']")
            extra_price_seats = []
            for extra_price_seats_element in extra_price_seats_elements:
                extra_price_seats.append(extra_price_seats_element.text.replace(' ', ''))
            seats_data = {
                'total_seats_available': total_seats[0],
                'total_seats_unavailable': total_seats[1],
                'price_XL_front': extra_price_seats[0],
                'seats_XL_front_available': seats_XL_front[0],
                'seats_XL_front_unavailable': seats_XL_front[1],
                'price_quick': extra_price_seats[1],
                'seats_quick_available': seats_quick[0],
                'seats_quick_unavailable': seats_quick[1],
                'price_best_front': extra_price_seats[3],
                'seats_best_front_available': seats_best_front[0],
                'seats_best_front_unavailable': seats_best_front[1],
                'price_XL_back': extra_price_seats[4],
                'seats_XL_back_available': seats_XL_back[0],
                'seats_XL_back_unavailable': seats_XL_back[1],
                'price_best_back': extra_price_seats[5],
                'seats_best_back_available': seats_best_back[0],
                'seats_best_back_unavailable': seats_best_back[1]
            }      
        except Exception as e:
            print(f'Error counting seats: {e}')
    
        return seats_data

    def advance_to_seats(self):
        # click the button
        try:
            self.driver.find_element(By.CSS_SELECTOR, "[class*='flight-card-summary__select-btn']").click()
            print('Continuing to seats')
        except Exception as e:
            
            print(f'Error continuing to seats: {e}')

        # get the page source
        page = self.driver.page_source

        # parse the page source
        soup = BeautifulSoup(page, 'html.parser')

        try:
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e*='fare-card--']")))
            fare_headers = self.driver.find_elements(By.CSS_SELECTOR, "[data-e2e*='fare-card--']")
            print('Trying to get fares')
            fares = []
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
            print('Fares gotten successfully')
            print('Trying to click on BASIC fare')
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='fare-header__submit-btn']")))
            basic_fare_button = self.driver.find_element(By.CSS_SELECTOR, "[class*='fare-header__submit-btn']")
            self.driver.execute_script("arguments[0].click();", basic_fare_button)
        except Exception as e:
            print(f'Error getting fares or clicking BASIC fare: {e}')

        print(fares)

        try:
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='fare-footer__submit-btn']")))
            basic_fare_button_popup = self.driver.find_elements(By.CSS_SELECTOR, "[class*='fare-footer__submit-btn']")[0]
            self.driver.execute_script("arguments[0].click();", basic_fare_button_popup)
            print('Selected BASIC fare on popup')
        except Exception as e:
            
            print(f'Error selecting BASIC fare on Popup: {e}')

        try:
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='login-touchpoint__expansion-bar']")))
            self.driver.find_element(By.CSS_SELECTOR, "[class*='login-touchpoint__expansion-bar']").click()
            print('Continue without login')
        except Exception as e:
            
            print(f'Error continuing without login: {e}')

        try:
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='dropdown__toggle']")))
            self.driver.find_element(By.CSS_SELECTOR, "[class*='dropdown__toggle']").click()
            print('Clicked dropdown for gender')
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='dropdown-item__link']")))
            self.driver.find_elements(By.CSS_SELECTOR, "[class*='dropdown-item__link']")[0].click()
            print('Selected Sr.')
            self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.name']").send_keys('Miguel')
            print('Entered first name')
            self.driver.find_element(By.CSS_SELECTOR, "[id*='form.passengers.ADT-0.surname']").send_keys('Cunha')
            print('Entered last name')
        except Exception as e:
            
            print(f'Error entering name: {e}')
        
        try:
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='continue-flow__button']")))
            self.driver.find_element(By.CSS_SELECTOR, "[class*='continue-flow__button']").click()
            print('Clicked on continue button')
        except Exception as e:
            
            print(f'Error clicking on continue button: {e}')

        # try:
        #     WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='booking-page']")))
        #     print('New page loaded successfully')
        #     # Add code to interact with the new page here
        # except Exception as e:
            
        #     print(f'Error waiting for new page to load: {e}')

        try:
            WebDriverWait(self.driver, timeout=timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='ry-radio-button--0']")))
            radio_button_small_bag = self.driver.find_element(By.CSS_SELECTOR, "[id*='ry-radio-button--0']")
            self.driver.execute_script("arguments[0].click();", radio_button_small_bag)
            print('Selected small bag')
        except Exception as e:
            
            print(f'Error selecting small bag: {e}')

        # IT IS STRANGE THAT THIS IS NOT NEEDED. MIGHT BE A PROBLEM TO CHECK IN THE FUTURE
        # try:
        #     self.driver.find_element(By.CSS_SELECTOR, "[class*='bags-continue-button']").click()
        #     print('Clicked on continue button')
        # except Exception as e:
            
        #     print(f'Error clicking on continue button: {e}')     

    # close the driver
    def close(self):
        self.driver.close()
        


# test
if __name__ == '__main__':
    # create the object
    ryanair = RyanAir(headless=True)

    # get the data
    prices = ryanair.get_prices_one_way_flight('2024-09-09', 'LIS', 'MAD')

    # fares = ryanair.get_fares()

    ryanair.advance_to_seats()

    seats = ryanair.count_seats()

    print(seats)

    # print the data
    print(prices)

    # close the driver
    ryanair.close()
