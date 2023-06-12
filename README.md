# RyanAir Flight Scraper

This is a Python class that uses Selenium and BeautifulSoup to scrape flight information from the RyanAir website. It can be used to retrieve prices and flight times for one-way and return flights.

## Installation

To use this class, you will need to have the following Python libraries installed:

- selenium
- undetected_chromedriver
- beautifulsoup4

You can install these libraries using pip:

```
pip install selenium undetected_chromedriver beautifulsoup4
```

## Usage

To use the RyanAir class, you will need to create an instance of the class and then call one of its methods to retrieve flight information. Here is an example:

```python
from RyanAir import RyanAir

# create the object
ryanair = RyanAir(headless=True)

# get the data
prices = ryanair.one_way_flight('2023-05-25', 'MAN', 'VLC')

# print the data
print(prices)

# close the driver
ryanair.close()
```

In this example, we create an instance of the RyanAir class with `headless=True` to run the scraper in headless mode. We then call the `one_way_flight` method with the departure date, origin airport code, and destination airport code as arguments. This method returns a list of dictionaries containing flight information, including the departure date, departure time, arrival time, and price. Finally, we close the driver to free up system resources.

## Methods

The RyanAir class has two methods for retrieving flight information:

### `one_way_flight(flyout, orig, dest, adults='1', teens='0', children='0', infants='0')`

This method retrieves flight information for a one-way flight. It takes the following arguments:

- `flyout`: the departure date in the format `YYYY-MM-DD`
- `orig`: the origin airport code
- `dest`: the destination airport code
- `adults`: the number of adults (default: 1)
- `teens`: the number of teenagers (default: 0)
- `children`: the number of children (default: 0)
- `infants`: the number of infants (default: 0)

This method returns a list of dictionaries containing flight information, including the departure date, departure time, arrival time, and price.

### `return_flight(flyout, flyback, orig, dest, adults='1', teens='0', children='0', infants='0')`

This method retrieves flight information for a return flight. It takes the following arguments:

- `flyout`: the departure date in the format `YYYY-MM-DD`
- `flyback`: the return date in the format `YYYY-MM-DD`
- `orig`: the origin airport code
- `dest`: the destination airport code
- `adults`: the number of adults (default: 1)
- `teens`: the number of teenagers (default: 0)
- `children`: the number of children (default: 0)
- `infants`: the number of infants (default: 0)

This method returns a list of dictionaries containing flight information, including the departure date, departure time, arrival time, and price for both the outbound and return flights.

## License

This code is released under the MIT License.
