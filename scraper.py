# import libraries
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json


class RyanAir:

    def __init__(self, headless=True):
        if headless:
            # config headless undetected chromedriver
            options = uc.ChromeOptions()
            options.add_argument('--headless')
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


    def one_way_flight(self, flyout, orig, dest, adults='1', teens='0', children='0', infants='0'):
        # set url
        url = f'https://www.ryanair.com/gb/en/trip/flights/select?adults=2&teens=0&children=0&infants=0&dateOut={flyout}&dateIn=&isConnectedFlight=false&discount=0&isReturn=false&promoCode=&originIata={orig}&destinationIata={dest}&tpAdults={adults}&tpTeens={teens}&tpChildren={children}&tpInfants={infants}&tpStartDate={flyout}&tpEndDate=&tpDiscount=0&tpPromoCode=&tpOriginIata={orig}&tpDestinationIata={dest}'
        # get the page
        self.driver.get(url)
        self.driver.implicitly_wait(10)

        # close cookies in button tag with cookie-popup-with-overlay__button class
        try:
            # wait till button with class name cookie-popup-with-overlay__button is clickable
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'cookie-popup-with-overlay__button')))
            # Q: what do i need to import for EC?
            # A: from selenium.webdriver.support import expected_conditions as EC
            # click the button
            self.driver.find_element(By.CLASS_NAME, 'cookie-popup-with-overlay__button').click()
        except Exception as e:
            print(f'Error closing cookies: {e}')


        # get the page source
        page = self.driver.page_source

        # parse the page source
        soup = BeautifulSoup(page, 'html.parser')

        # get data
        if soup.find('span', class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm') is None:
            departure_date = 'No flights available on selected date'
            departure_flyout_times = 'N/A'
            arrival_flyout_times = 'N/A'
        else:
            day = soup.find('span', class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm').text
            month = soup.find('span', class_='date-item__month date-item__month--selected body-xl-lg body-xl-sm').text
            departure_date = f'{day} {month}'
            # get departure and arrival times
            departure_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
            arrival_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')

        # get the prices
        prices = []
        for selection in soup.find_all('div', class_='date-item__price title-s-lg title-s-sm date-item__price--selected ng-star-inserted'):
            # get the price
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


    # close the driver
    def close(self):
        self.driver.close()


# test
if __name__ == '__main__':
    # create the object
    ryanair = RyanAir(headless=True)

    # get the data
    prices= ryanair.one_way_flight('2023-05-25', 'MAN', 'VLC')

    # print the data
    print(prices)

    # close the driver
    ryanair.close()
