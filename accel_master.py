import os
import csv
from datetime import datetime
import numpy as np
import time
import smbus
import threading
import struct
import socket

import subprocess
import signal
import sys

import pylogix as pl

# Initialize I2C (using SMBus)
bus = smbus.SMBus(1)  # or 0 depending on your Raspberry Pi version
time.sleep(1)
address = 0x68  # MPU6050 address

test_performance = True


#client = ModbusTcpClient('192.168.168.46')
#client.connect()
#print('Connected to plc: {}'.format(client.connect()))

class AccelerometerLogger():
    def __init__(self, filename, save_every, client, tag_X, n_history=500, desired_hz=200, R=2):
        super().__init__()
    
        self.filename = filename
        self.desired_hz = desired_hz  # Desired sample rate in Hz
        self.interval = 1 / desired_hz
        self.timer = None
        
        self.count = 0
        self.alarm_count = 0
        self.N = save_every
        self.lims = 10
        self.millis = 0
        self.current_t = 0
        self.t = 0
        self.dt = 0
        self.R = R
        self.var = 0
        self.last_save_t = 0
        self.i = 0
        
        self.tag_X = tag_X
        self.n_history = n_history
        
        # Initialize random walk starting point
        self.X = 0
        self.Y = 0
        self.Z = 0
        
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0
        #self.GX = 0
        #self.GY = 0
        #self.GZ = 0
        #self.temp = 0
                
        # Create arrays to store previous steps
        self.X_history = [self.X]
        self.Y_history = [self.Y]
        self.Z_history = [self.Z]
        #self.GX_history = [self.GX]
        #self.GY_history = [self.GY]
        #self.GZ_history = [self.GZ]
        self.t_history = [self.t]
        #self.temp_history = [self.temp]}
        
        self.X_history2 = [self.X]
        self.Y_history2 = [self.Y]
        self.Z_history2 = [self.Z]
        
        self.ax_rms = 0
        self.ay_rms = 0
        self.az_rms = 0
            
        self.initialize_csv_file()
    
    def calibrate(self):
        print("Calibrating, please wait")
        Ax_list = []
        Ay_list = []
        Az_list = []
        Gx_list = []
        Gy_list = []
        Gz_list = []
        temp_list = []

        for i in range(1, 1000):
            Ax, Ay, Az = get_values()
            if i == 1:
                time.sleep(1)
            Ax_list.append(Ax)
            Ay_list.append(Ay)
            Az_list.append(Az)
            
        self.x_offset = np.mean(Ax_list)
        self.y_offset = np.mean(Ay_list)
        self.z_offset = np.mean(Az_list)

        #accel_range = 
        print("Calibrated values: Ax: {}, Ay: {}, Az: {}".format(self.x_offset, self.y_offset, self.z_offset))
        #print("Calibrated values: Gx: {}, Gy: {}, Gz: {}".format(gx_offset, gy_offset, gz_offset))
        #print("Initial sensor temp: {}".format(init_temp))

        return self.x_offset, self.y_offset, self.z_offset#, gx_offset, gy_offset, gz_offset, init_temp
        
    def add_to_time(self):
        act_time = time.time()
        dt = act_time - self.current_t
        self.t += dt
        self.dt = dt
        self.current_t = act_time
        
    def update(self):
        self.update_values()
        self.i += 1
        if self.t > 1 and self.i%10:
            self.send_accel(client)


                
    
    def send_accel(self, client):
        send_values = [self.t, self.ax_rms, self.ay_rms, self.az_rms]
        try:
            client.Write(self.tag_X, send_values)
        except:
            print('Failed to send values of acceleration')
    
    def send_alert(self):
        self.alert()
        
    def alert(self):
        client.write_coil(0,1)
        print("Alert sent!")
        #time.sleep(5)
        #client.write_coil(0,0)
      
        
    def calc_rms(self,data_array):
        squared = np.array(data_array) ** 2
        mean_squared = np.mean(squared)
        rms_value = np.sqrt(mean_squared)
        return rms_value
        
    def update_values(self):
        if self.alarm_count != 0:
            self.alarm_count += 1
            
        self.count +=1
        
        Ax, Ay, Az = get_values()
        
        self.X = Ax - self.x_offset
        self.Y = Ay - self.y_offset
        self.Z = Az - self.z_offset

        self.add_to_time()

        self.X_history.append(Ax)
        self.Y_history.append(Ay)
        self.Z_history.append(Az)
        self.t_history.append(self.t)

        self.X_history2.append(Ax)
        self.Y_history2.append(Ay)
        self.Z_history2.append(Az)
        
        if len(self.X_history2) > self.n_history:
            self.X_history2 = self.X_history2[1:]
            self.Y_history2 = self.Y_history2[1:]
            self.Z_history2 = self.Z_history2[1:]
            
        self.ax_rms = self.calc_rms(self.X_history2)
        self.ay_rms = self.calc_rms(self.Y_history2)
        self.az_rms = self.calc_rms(self.Z_history2)
        
        #send_float([self.vx_rms,self.vy_rms,self.vz_rms])
        #print('Rms Velocity values: x:{}, y:{}, z:{}'.format(self.vx_rms, self.vy_rms, self.vz_rms))
        
        if self.count == self.N:
            _ = self.save_data_to_csv()
            #accel_range = read_accel_range()
            #gyro_range = read_gyro_range()
            self.count = 0
        
    def run(self):
        while True:
            start_time = time.perf_counter()  # Record the start time of each sample
            self.update()
            elapsed_time = time.perf_counter() - start_time
            time_to_sleep = self.interval - elapsed_time
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)
                
                
        
    def initialize_csv_file(self):
        # Create the 'accel data' folder if it doesn't exist
        folder_path = os.path.join(os.getcwd(), folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Create the file name based on the current date and time of program start
        start_time = datetime.now()
        file_name = self.filename +"_"+start_time.strftime("%d-%m-%y_%H-%M.csv")
        self.file_path = os.path.join(folder_path, file_name)

        # Write headers to the CSV file
        with open(self.file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['time', 'accel_x', 'accel_y', 'accel_z'])#, 'g_x', 'g_y', 'g_z', 'temp'])
            file.close()
    
    def save_data_to_csv(self):
        dt =  np.round(self.current_t - self.last_save_t,2)
        Hz = np.round(self.N/dt,1)
        print("Writing to csv {}, at time {} sec, dt: {}s, Hz: {}".format(self.filename, np.round(self.t,2),dt,Hz) )
        # Transpose the data to save it as columns
        self.last_save_t = self.current_t
        data_to_write = zip(
            self.t_history,
            self.X_history,
            self.Y_history,
            self.Z_history)
            #self.GX_history,
            #self.GY_history,
            #self.GZ_history,
            #self.temp_history
        #)
        # Write the transposed data to the CSV file
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data_to_write)
            
        self.clear_history()
        
        
    def clear_history(self):
        self.X_history.clear()
        self.Y_history.clear()
        self.Z_history.clear()
        #self.GX_history.clear()
        #self.GY_history.clear()
        #self.GZ_history.clear()
        self.t_history.clear()
        #self.temp_history.clear()
        

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
    
    #data = get_values_gyro()
    #Gx, Gy, Gz = (data['x'],data['y'],data['z'])
    
    #temp = 0#get_values_temp()
    return Ax,Ay,Az#,Gx,Gy,Gz,temp
                  
def get_values_accel(g = False):
    
    x = read_i2c_word(ACCEL_XOUT0)
    y = read_i2c_word(ACCEL_YOUT0)
    z = read_i2c_word(ACCEL_ZOUT0)

    accel_scale_modifier = None
    accel_range = ACCEL_RANGE_16G #ACCEL_RANGE_2G

    if accel_range == ACCEL_RANGE_2G:
        accel_scale_modifier = ACCEL_SCALE_MODIFIER_2G
    elif accel_range == ACCEL_RANGE_4G:
        accel_scale_modifier = ACCEL_SCALE_MODIFIER_4G
    elif accel_range == ACCEL_RANGE_8G:
        accel_scale_modifier = ACCEL_SCALE_MODIFIER_8G
    elif accel_range == ACCEL_RANGE_16G:
        accel_scale_modifier = ACCEL_SCALE_MODIFIER_16G
    else:
        print("Unkown range - accel_scale_modifier set to self.ACCEL_SCALE_MODIFIER_2G")
    #accel_scale_modifier = ACCEL_SCALE_MODIFIER_2G

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
        
def get_values_gyro():
    x = read_i2c_word(GYRO_XOUT0)
    y = read_i2c_word(GYRO_YOUT0)
    z = read_i2c_word(GYRO_ZOUT0)

    gyro_scale_modifier = None
    gyro_range = read_gyro_range(True)

    if gyro_range == GYRO_RANGE_250DEG:
        gyro_scale_modifier = GYRO_SCALE_MODIFIER_250DEG
    elif gyro_range == GYRO_RANGE_500DEG:
        gyro_scale_modifier = GYRO_SCALE_MODIFIER_500DEG
    elif gyro_range == GYRO_RANGE_1000DEG:
        gyro_scale_modifier = GYRO_SCALE_MODIFIER_1000DEG
    elif gyro_range == GYRO_RANGE_2000DEG:
        gyro_scale_modifier = sGYRO_SCALE_MODIFIER_2000DEG
    else:
        print("Unkown range - gyro_scale_modifier set to self.GYRO_SCALE_MODIFIER_250DEG")
    gyro_scale_modifier = GYRO_SCALE_MODIFIER_250DEG

    x = (x / gyro_scale_modifier)*np.pi/180.0
    y = (y / gyro_scale_modifier)*np.pi/180.0
    z = (z / gyro_scale_modifier)*np.pi/180.0

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
            

def set_gyro_range(gyro_range):
    """Sets the range of the gyroscope to range.

    gyro_range -- the range to set the gyroscope to. Using a pre-defined
    range is advised.
    """
    # First change it to 0x00 to make sure we write the correct value later
    bus.write_byte_data(address, GYRO_CONFIG, 0x00)

    # Write the new range to the ACCEL_CONFIG register
    bus.write_byte_data(address, GYRO_CONFIG, gyro_range)

def read_gyro_range(self, raw = False):
    """Reads the range the gyroscope is set to.

    If raw is True, it will return the raw value from the GYRO_CONFIG
    register.
    If raw is False, it will return 250, 500, 1000, 2000 or -1. If the
    returned value is equal to -1 something went wrong.
    """
    raw_data = bus.read_byte_data(address, GYRO_CONFIG)

    if raw is True:
        return raw_data
    elif raw is False:
        if raw_data == GYRO_RANGE_250DEG:
            return 250
        elif raw_data == GYRO_RANGE_500DEG:
            return 500
        elif raw_data == GYRO_RANGE_1000DEG:
            return 1000
        elif raw_data == GYRO_RANGE_2000DEG:
            return 2000
        else:
            return -1
            
def get_values_temp():

    raw_temp = read_i2c_word(TEMP_OUT0)

    # Get the actual temperature using the formule given in the
    # MPU-6050 Register Map and Descriptions revision 4.2, page 30
    actual_temp = (raw_temp / 340.0) + 36.53

    return actual_temp

def send_float(data):
    # Pack the floats into bytes using struct
    packed_data = struct.pack('>3f', *data)
    # Create a TCP/IP socket
    try:
        client_socket.sendall(packed_data)
    except Exception as e:
        raise RuntimeError(f'Error sending string: {e}')
        
        

def send_string(data):
    # Encode the string into bytes
    encoded_data = data.encode('utf-8')
    # Create a TCP/IP socket
    try:
        client_socket.sendall(encoded_data)
    except Exception as e:
        raise RuntimeError(f'Error sending string: {e}')


def start_child_process(script_path):
    process = subprocess.Popen([sys.executable, script_path])
    return process

def stop_child_process(process):
    process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
    
def signal_handler(sig, frame):
    print("Stopping child process...")
    stop_child_process(child_process)
    sys.exit(0)
   
def wait_for_plc(client,tag):
    print('Waiting for PLC')
    x = True
    while x:
        response = client.Read(tag)
        try:
            bool_val = bool(response.Value)
            if bool_val:
                print('INIT!')
                x = not bool_val
        except:
            continue

    return

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

GYRO_SCALE_MODIFIER_250DEG = 131.0
GYRO_SCALE_MODIFIER_500DEG = 65.5
GYRO_SCALE_MODIFIER_1000DEG = 32.8
GYRO_SCALE_MODIFIER_2000DEG = 16.4

GYRO_RANGE_250DEG = 0x00
GYRO_RANGE_500DEG = 0x08
GYRO_RANGE_1000DEG = 0x10
GYRO_RANGE_2000DEG = 0x18

PWR_MGMT_1 = 0x6B
PWR_MGMT_2 = 0x6C

ACCEL_XOUT0 = 0x3B
ACCEL_YOUT0 = 0x3D
ACCEL_ZOUT0 = 0x3F

TEMP_OUT0 = 0x41

GYRO_XOUT0 = 0x43
GYRO_YOUT0 = 0x45
GYRO_ZOUT0 = 0x47

ACCEL_CONFIG = 0x1C
GYRO_CONFIG = 0x1B

PWR_MGMT_1 = 0x6B
PWR_MGMT_2 = 0x6C

accel_range = ACCEL_RANGE_16G
gyro_range = GYRO_RANGE_250DEG

R = 1000

host = '192.168.168.67'  # Replace with the server's IP address
port = 65410
    
folder_name = 'pruebas-full'#'carga-mecanica'

save_every = 1000
desired_hz = 160
    
tag_init = 'RB_INIT'
tag_X = 'RB_501B_X'
ip_address = '192.168.168.46'


client = pl.PLC(ip_address)
client.SocketTimeout = 100

set_accel_range(accel_range)

if __name__ == '__main__':
    child_script = "heartbeatB.py"  
    try:
        child_process = start_child_process(child_script)
    except Exception as e:
        print(f"Error starting heartbeat process: {e}")
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"Started heartbeat process with PID: {child_process.pid}")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
    except socket.error as e:
        print(f"Socket error: {e}")
        stop_child_process(child_process)
        sys.exit(1)
        
    try:
        send_string(folder_name)
        filename = input('File Name: ')
        send_string(filename)
    except Exception as e:
        print(f"Error sending data: {e}")
        client_socket.close()
        stop_child_process(child_process)
        sys.exit(1)
    
    try:
        print('Init Logger')
        sensor = AccelerometerLogger(filename, save_every, client, tag_X, desired_hz, R=R)
        sensor.calibrate()
        
    except Exception as e:
        print(f"Sensor initialization or calibration error: {e}")
        client_socket.close()
        stop_child_process(child_process)
        sys.exit(1)
    
    try:
        bus.write_byte_data(address, PWR_MGMT_1, 0x00)
    except Exception as e:
        print(f"Bus write error: {e}")
        client_socket.close()
        stop_child_process(child_process)
        sys.exit(1)
    
    try:
        wait_for_plc(client,tag_init)
        sensor.current_t = time.time()
        print('Running!')
        sensor.run()
        
    except Exception as e:
        print(f"Communication error or sensor run error: {e}")
        stop_child_process(child_process)
        sys.exit(1)
    
    except KeyboardInterrupt:
        stop_child_process(child_process)
        sys.exit(1)
        
    finally:
        client_socket.close()
        stop_child_process(child_process)
        sys.exit(1)
    stop_child_process(child_process)
    sys.exit(1)
