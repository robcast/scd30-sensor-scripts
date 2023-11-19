from machine import Pin, I2C
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY
from pimoroni import RGBLED
import struct
import time

def crc8(data):
    """
    Calculate the CRC of the given data.
    
    inspired by https://github.com/Sensirion/python-i2c-driver/blob/master/sensirion_i2c_driver/crc_calculator.py
    """
    width = 8
    polynomial = 0x31
    init_value = 0xff
    final_xor = 0x00
    
    crc = init_value
    for value in data:
        crc ^= value
        for i in range(width):
            if crc & (1 << (width - 1)):
                crc = (crc << 1) ^ polynomial
            else:
                crc = crc << 1
                
            crc &= (1 << width) - 1
            
    return crc ^ final_xor

def unpack_word(data_bytes):
    """return 16 bit word from data_bytes and check CRC in byte 3"""
    crc = crc8(data_bytes[:2])
    if crc != data_bytes[2]:
        raise ValueError(f"CRC mismatch ({hex(crc)}!={hex(data_bytes[2])}")
    
    word = int.from_bytes(data_bytes[0:2], 'big')
    return word

def unpack_bytes(data_bytes):
    """return 2 bytes from data_bytes and check CRC in byte 3"""
    crc = crc8(data_bytes[:2])
    if crc != data_bytes[2]:
        raise ValueError(f"CRC mismatch ({hex(crc)}!={hex(data_bytes[2])}")
    
    return data_bytes[0:2]

def pack_word(word):
    """return 3 bytes from 16 bit word and CRC"""
    data_bytes = bytearray(3)
    data_bytes[0:2] = word.to_bytes(2, 'big')
    crc = crc8(data_bytes[0:2])
    data_bytes[2] = crc
    return data_bytes

def get_data_ready(bus, addr):
    """return SCD30 data ready status"""
    # send command 0x0202
    bus.writeto(addr, b'\x02\x02')
    time.sleep_ms(3)
    # read 3 bytes
    data = bus.readfrom(addr, 3)
    value = unpack_word(data)
    return value

def get_interval(bus, addr):
    """return SCD30 continuous measurement interval"""
    # send command 0x4600
    bus.writeto(addr, b'\x46\x00')
    time.sleep_ms(3)
    # read 3 bytes
    data = bus.readfrom(addr, 3)
    value = unpack_word(data)
    return value

def set_interval(bus, addr, seconds):
    """set SCD30 continuous measurement interval"""
    # send command 0x4600
    data = pack_word(seconds)
    bus.writeto(addr, b'\x46\x00' + data)
    time.sleep_ms(3)

def set_continuous(bus, addr, pressure):
    """set SCD30 continuous measurement mode"""
    # send command 0x0010
    data = pack_word(pressure)
    bus.writeto(addr, b'\x00\x10' + data)
    time.sleep_ms(3)

def read_measurement(bus, addr):
    """return SCD30 measurement data structure"""
    # send command 0x0300
    bus.writeto(addr, b'\x03\x00')
    time.sleep_ms(3)
    # read 18 bytes
    data = bus.readfrom(addr, 18)
    #print(f"read measurement:{data}")
    # CO2
    co2_h_bytes = data[0:3]
    co2_h = unpack_bytes(co2_h_bytes)
    co2_l_bytes = data[3:6]
    co2_l = unpack_bytes(co2_l_bytes)
    co2 = struct.unpack('!f', co2_h + co2_l)[0]
    # Temp
    temp_h_bytes = data[6:9]
    temp_h = unpack_bytes(temp_h_bytes)
    temp_l_bytes = data[9:12]
    temp_l = unpack_bytes(temp_l_bytes)
    temp = struct.unpack('!f', temp_h + temp_l)[0]
    # RH
    rh_h_bytes = data[12:15]
    rh_h = unpack_bytes(rh_h_bytes)
    rh_l_bytes = data[15:18]
    rh_l = unpack_bytes(rh_l_bytes)
    rh = struct.unpack('!f', rh_h + rh_l)[0]
    
    return {'co2': co2, 'temp': temp, 'rh': rh}

def display_measurement(display, data):
    """show measurement data on display"""
    fg = display.create_pen(255, 255, 255)
    bg = display.create_pen(0, 0, 0)
    #display.set_font('bitmap8')
    display.set_font('sans')
    text_scale = 0.9
    # clear 
    display.set_pen(bg)
    display.clear()
    # print data
    display.set_pen(fg)
    x = 10
    y = 30
    lf = 40
    display.text(f"CO2: {data['co2']:.0f}ppm", x, y, scale=text_scale)
    y += lf
    display.text(f"T: {data['temp']:.2f}C", x, y, scale=text_scale)
    y += lf
    display.text(f"rH: {data['rh']:.1f}%", x, y, scale=text_scale)
    # show
    display.update()

def display_message(display, text_message):
    """show text_message string on display"""
    fg = display.create_pen(255, 255, 255)
    bg = display.create_pen(0, 0, 0)
    #display.set_font('bitmap8')
    display.set_font('sans')
    text_scale = 0.9
    # clear 
    display.set_pen(bg)
    display.clear()
    # print data
    display.set_pen(fg)
    x = 10
    y = 30
    display.text(text_message, x, y, scale=text_scale)
    # show
    display.update()

def led_measurement(led, data):
    """show measurement data on RGB LED"""
    brgt = 0.2
    # range: 500=green - 1500=red
    val = max(data['co2'] - 500, 0)
    r = val / 4
    g = max(255 - r, 0)
    #print(f"led: {r=} {g=}")
    led.set_rgb(r * brgt, g * brgt, 0)

#######################################
## main

# I2C bus on GPIO pins 4 and 5
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)

# scan i2c bus
ids = i2c.scan()

hexids = [hex(id) for id in ids]
print(f"i2c bus scan: {hexids}")

# SCD30 I2C address
scd30_addr = 0x61

if scd30_addr not in ids:
    raise RuntimeError(f"SCD30 sensor not found at 0x{scd30_addr:x}!")

# set up display
display = PicoGraphics(display=DISPLAY_PICO_DISPLAY, rotate=0)
display.set_backlight(1.0)

# set up LED
led = RGBLED(6, 7, 8)
led.set_rgb(0, 0, 0)

# check measurement interval
interval = 10
if get_interval(i2c, scd30_addr) != interval:
    print(f"measurement interval changed to {interval}s")
    set_interval(i2c, scd30_addr, interval)

display_message(display, 'Starting...')
# main loop
busytime = 0
while True:
    rdy = get_data_ready(i2c, scd30_addr)
    if not rdy:
        if busytime <= interval:
            print("not ready, waiting...")
            time.sleep(1)
            busytime += 1
        else:
            print(f"ERROR: not ready longer than {interval}s. Re-triggering measurement.")
            # set continuous measurement at 1013mBar
            set_continuous(i2c, scd30_addr, 1013)
            busytime = 0
           
        continue
    
    else:
        data = read_measurement(i2c, scd30_addr)
        print(f"read {data}")
        display_measurement(display, data)
        led_measurement(led, data)
        busytime = 0
        time.sleep(10)
        