#!/usr/bin/python3

import subprocess
import time
import crcmod
import struct

# hash function used by SCD30
crc8hash = crcmod.mkCrcFun(0x131, initCrc=0xff, rev=False)
# I2C bus 1 on ODROID-C2
i2cbus = '1'
# SCD30 I2C bus address
scd30_addr = '0x61'
# SCD30 measurement interval (s)
scd30_measurement_interval = 10
# SCD30 temperature offset (1/100°C)
scd30_temp_offset = 0

def unpack_word(data_bytes):
    crc = crc8hash(data_bytes[:2])
    if crc != data_bytes[2]:
        raise ValueError(f"CRC mismatch ({hex(crc)}!={hex(data_bytes[2])}")
    word = int.from_bytes(data_bytes[0:2], byteorder='big')
    return word

def unpack_bytes(data_bytes):
    crc = crc8hash(data_bytes[:2])
    if crc != data_bytes[2]:
        raise ValueError(f"CRC mismatch ({hex(crc)}!={hex(data_bytes[2])}")
    return data_bytes[0:2]

def pack_word(word):
    data_bytes = bytearray(3)
    data_bytes[0:2] = word.to_bytes(2, byteorder='big')
    crc = crc8hash(data_bytes[0:2])
    data_bytes[2] = crc
    return data_bytes

def get_data_ready(bus, addr):
    # send command 0x0202
    #print(f"sending ready command")
    subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'w2@' + addr, '0x02', '0x02'],
                   check=True)
    # read 3 bytes
    ret = subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'r3@' + addr],
                         capture_output=True, text=True, check=True)
    data = ret.stdout
    #print(f"transfer got:{data}")
    data_bytes = bytearray.fromhex(data.replace('0x', ''))
    ready_status = unpack_word(data_bytes)
    return ready_status

def get_measurement_interval(bus, addr):
    # send command 0x4600
    #print(f"sending get-measurement-interval command")
    subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'w2@' + addr, '0x46', '0x00'],
                   check=True)
    # read 3 bytes
    ret = subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'r3@' + addr],
                         capture_output=True, text=True, check=True)
    data = ret.stdout
    #print(f"transfer got:{data}")
    data_bytes = bytearray.fromhex(data.replace('0x', ''))
    data_word = unpack_word(data_bytes)
    return data_word

def set_measurement_interval(bus, addr, interval):
    data_bytes = pack_word(interval)
    # send command 0x4600
    #print(f"sending set-measurement-interval command")
    cmd = ['/usr/sbin/i2ctransfer', '-y', i2cbus, 'w5@' + addr, '0x46', '0x00']
    cmd += [hex(b) for b in data_bytes]
    print(f"cmd: {cmd}")
    subprocess.run(cmd, check=True)
    return interval

def get_temp_offset(bus, addr):
    # send command 0x5403
    #print(f"sending get-temp-offset command")
    subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'w2@' + addr, '0x54', '0x03'],
                   check=True)
    # read 3 bytes
    ret = subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'r3@' + addr],
                         capture_output=True, text=True, check=True)
    data = ret.stdout
    #print(f"transfer got:{data}")
    data_bytes = bytearray.fromhex(data.replace('0x', ''))
    data_word = unpack_word(data_bytes)
    return data_word

def read_measurement(bus, addr):
    # send command 0x0300
    #print(f"sending read measurement command")
    subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'w2@' + addr, '0x03', '0x00'],
                   check=True)
    # read 18 bytes
    ret = subprocess.run(['/usr/sbin/i2ctransfer', '-y', i2cbus, 'r18@' + addr],
                         capture_output=True, text=True, check=True)
    data = ret.stdout
    #print(f"transfer got:{data}")
    data_bytes = bytearray.fromhex(data.replace('0x', ''))
    #print(f"got read measurement msg={data_bytes.hex(' ')}")
    # CO2
    co2_h_bytes = data_bytes[0:3]
    co2_h = unpack_bytes(co2_h_bytes)
    co2_l_bytes = data_bytes[3:6]
    co2_l = unpack_bytes(co2_l_bytes)
    co2 = struct.unpack('!f', co2_h + co2_l)[0]
    #print(f"co2_h={co2_h.hex()}, co2_l={co2_l.hex()}, co2={co2}")
    # Temp
    temp_h_bytes = data_bytes[6:9]
    temp_h = unpack_bytes(temp_h_bytes)
    temp_l_bytes = data_bytes[9:12]
    temp_l = unpack_bytes(temp_l_bytes)
    temp = struct.unpack('!f', temp_h + temp_l)[0]
    # RH
    rh_h_bytes = data_bytes[12:15]
    rh_h = unpack_bytes(rh_h_bytes)
    rh_l_bytes = data_bytes[15:18]
    rh_l = unpack_bytes(rh_l_bytes)
    rh = struct.unpack('!f', rh_h + rh_l)[0]
    
    return {'co2': co2, 'temp': temp, 'rh': rh}


## main

mi = get_measurement_interval(i2cbus, scd30_addr)
print(f"measurement interval: {mi}s")
if mi != scd30_measurement_interval:
    print(f"set measurement interval to {scd30_measurement_interval}s")
    set_measurement_interval(i2cbus, scd30_addr, scd30_measurement_interval)
    mi = get_measurement_interval(i2cbus, scd30_addr)
    print(f"measurement interval: {mi}s")
    
temp_offset = get_temp_offset(i2cbus, scd30_addr)
print(f"temperature offset: {temp_offset}/100°C")

con = open('/dev/console', 'w')

while True:
    try:
        ready = get_data_ready(i2cbus, scd30_addr)
        #print(f"ready = {ready}")
        if (ready == 1):
            m = read_measurement(i2cbus, scd30_addr)
            #print(f"measurement = {measurement}")
            print(f"CO2: {m['co2']:.0f}ppm T: {m['temp']:.2f}° RH: {m['rh']:.1f}%", file=con, flush=True)
        else:
            print("not ready", file=con, flush=True)

        time.sleep(10)

    except Exception as e:
        print(f"ERROR: {e}", file=con, flush=True)
