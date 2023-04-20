# import libraries
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
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

        try:
            # get the departure and return dates
            departure_day = soup.find_all('span',
                                      class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm')[0].text
            departure_month = soup.find_all('span',
                                        class_='date-item__month date-item__month--selected body-xl-lg body-xl-sm')[0].text
            departure_date = f'{departure_day} {departure_month}'

        except Exception as e:
            pass

        try:
            return_day = soup.find_all('span',
                                   class_='date-item__day-of-month date-item__day-of-month--selected body-xl-lg body-xl-sm')[1].text
            return_month = soup.find_all('span',
                                     class_='date-item__month date-item__month--selected body-xl-lg body-xl-sm')[1].text
            return_date = f"{return_day} {return_month}"
        except Exception as e:
            retun_date = flyback


        # get the prices
        prices = []
        for selection in soup.find_all('div', class_='date-item__price title-s-lg title-s-sm date-item__price--selected ng-star-inserted'):
            # get the price
            price = selection.find('ry-price', class_='price').text
            # remove blank spaces
            price = price.replace(' ', '')
            # append to the list
            prices.append(price)

        try:
            # get departure and arrival times
            departure_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[0].text.replace(' ', '')
            arrival_flyout_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ', '')
        except Exception as e:
            departure_flyout_times = 'N/A'
            arrival_flyout_times = 'N/A'

        try:
            departure_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[1].text.replace(' ','')
            arrival_flyback_times = soup.find_all('span', class_='title-l-lg title-l-sm time__hour')[2].text.replace(' ', '')
        except Exception as e:
            departure_flyback_times = 'N/A'
            arrival_flyback_times = 'N/A'

        # create the dictionary
        prices = [{'Departure': {'date': departure_date, 'departure_time': departure_flyout_times, 'arrival_time': arrival_flyout_times, 'price': prices[0], }},
                  {'Return': {'Date': return_date, 'departure_time': departure_flyback_times, 'arrival_time': arrival_flyback_times, 'price': prices[1]}}]
        # return the dictionary
        return prices

    # close the driver
    def close(self):
        self.driver.close()


# test
if __name__ == '__main__':
    # create the object
    ryanair = RyanAir(headless=True)

    # get the data
    prices= ryanair.return_flight('2023-05-24', '2023-06-08', 'MAN', 'VLC', '2')

    # print the data
    print(prices)

    # close the driver
    ryanair.close()

