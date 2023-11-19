# SCD30 sensor scripts

Python scripts to read and display measurements from a [Sensirion SCD30](https://sensirion.com/products/catalog/SCD30/) CO2 sensor on a single-board computer/microcontroller:

- [ODROID-C2](https://wiki.odroid.com/odroid-c2/odroid-c2) with [3.5 inch LCD shield](https://wiki.odroid.com/legacy/accessory/display/3.5inch_lcd_shield/3.5inch_lcd_shield)
  - connect SCD30 to I2C bus 1 on LCD shield RTC connector
  - outputs to `/dev/console`, could also work on other boards and displays
  - requires Linux i2c-tools for I2C commands
  - requires Python [crcmod](https://pypi.org/project/crcmod/) library for CRC
  
- [Raspberry Pi Pico](https://www.raspberrypi.com/products/raspberry-pi-pico/) board with [Pimoroni Pico Display Pack](https://shop.pimoroni.com/products/pico-display-pack)
  - connect SCD30 to I2C on pins 6 and 7 (GPIO 4 and 5)
  - requires Micropython with Pimoroni display driver (tested with pimoroni-pico-v1.19.0)
  - rename Python file to `main.py` on Pico to automatically run on powerup 
