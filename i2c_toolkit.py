import smbus

GRAVITY_MS2 = 9.80665

ACCEL_XOUT0 = 0x3B
ACCEL_YOUT0 = 0x3D
ACCEL_ZOUT0 = 0x3F

ACCEL_RANGE_2G = 0x00
ACCEL_RANGE_4G = 0x08
ACCEL_RANGE_8G = 0x10
ACCEL_RANGE_16G = 0x18

ACCEL_SCALE_MODIFIER_2G = 16384.0
ACCEL_SCALE_MODIFIER_4G = 8192.0
ACCEL_SCALE_MODIFIER_8G = 4096.0
ACCEL_SCALE_MODIFIER_16G = 2048.0


PWR_MGMT_1 = 0x6B
PWR_MGMT_2 = 0x6C

ACCEL_CONFIG = 0x1C

bus = smbus.SMBus(1)  # or 0 depending on your Raspberry Pi version
time.sleep(1)
address = 0x68  # MPU6050 address

set_accel_range(ACCEL_RANGE_16G)

try:
    bus.write_byte_data(address, PWR_MGMT_1, 0x00)
except Exception as e:
    print(f"Bus write error: {e}")
    
def read_i2c_word(register):
    """Read two i2c registers and combine them.

    register -- the first register to read from.
    Returns the combined read results.
    """
    try:
        # Read the data from the registers
        high = bus.read_byte_data(address, register)
        low = bus.read_byte_data(address, register + 1)
    except Exception as e:
        raise IOError(f"Failed to read from I2C device at register {register}: {e}")

    value = (high << 8) + low

    if value >= 0x8000:
        return -((65535 - value) + 1)
    else:
        return value

    
def get_values(g = False):
    data = get_values_accel(g=g)
    Ax, Ay, Az = (data['x'],data['y'],data['z'])
    return Ax,Ay,Az
                  
def get_values_accel(g = False):
    
    x = read_i2c_word(ACCEL_XOUT0)
    y = read_i2c_word(ACCEL_YOUT0)
    z = read_i2c_word(ACCEL_ZOUT0)

    accel_scale_modifier = ACCEL_SCALE_MODIFIER_16G
    accel_range = ACCEL_RANGE_16G

    x = x / accel_scale_modifier
    y = y / accel_scale_modifier
    z = z / accel_scale_modifier

    if g is True:
        return {'x': x, 'y': y, 'z': z}
    elif g is False:
        x = x * GRAVITY_MS2
        y = y * GRAVITY_MS2
        z = z * GRAVITY_MS2
        return {'x': x, 'y': y, 'z': z}
        
def set_accel_range(accel_range):
    """Sets the range of the accelerometer to range.

    accel_range -- the range to set the accelerometer to. Using a
    pre-defined range is advised.
    """
    # First change it to 0x00 to make sure we write the correct value later
    bus.write_byte_data(address, ACCEL_CONFIG, 0x00)

    # Write the new range to the ACCEL_CONFIG register
    bus.write_byte_data(address, ACCEL_CONFIG, accel_range)

def read_accel_range(raw = False):
    """Reads the range the accelerometer is set to.

    If raw is True, it will return the raw value from the ACCEL_CONFIG
    register
    If raw is False, it will return an integer: -1, 2, 4, 8 or 16. When it
    returns -1 something went wrong.
    """
    raw_data = bus.read_byte_data(address, ACCEL_CONFIG)

    if raw is True:
        return raw_data
    
    elif raw is False:
        if raw_data == ACCEL_RANGE_2G:
            return 2
        elif raw_data == ACCEL_RANGE_4G:
            return 4
        elif raw_data == ACCEL_RANGE_8G:
            return 8
        elif raw_data == ACCEL_RANGE_16G:
            return 16
        else:
            return -1