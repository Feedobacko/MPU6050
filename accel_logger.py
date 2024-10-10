import os
import time
import numpy as np
import csv
from datetime import datetime
import i2c_toolkit as i2c

class AccelerometerLogger():
    def __init__(self, filename, foldername, save_every, client, tag_X, n_history=500, desired_hz=200):
        super().__init__()
    
        self.filename = filename
        self.foldername = foldername
        self.desired_hz = desired_hz  # Desired sample rate in Hz
        self.interval = 1 / desired_hz
        self.timer = None
        
        self.count = 0
        self.N = save_every
        self.lims = 10
        self.millis = 0
        self.current_t = 0
        self.t = 0
        self.dt = 0
        self.var = 0
        self.last_save_t = 0
        self.i = 0
        
        self.client = client
        self.tag_X = tag_X
        self.n_history = n_history
        
        # Initialize random walk starting point
        self.X = 0
        self.Y = 0
        self.Z = 0
        
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0
                
        # Create arrays to store previous steps
        self.X_history = [self.X]
        self.Y_history = [self.Y]
        self.Z_history = [self.Z]
        self.t_history = [self.t]
        
        self.X_history2 = [self.X]
        self.Y_history2 = [self.Y]
        self.Z_history2 = [self.Z]
        
        self.ax_rms = 0
        self.ay_rms = 0
        self.az_rms = 0
        self.start_time = time.perf_counter()
        self.initialize_csv_file()
    
    def calibrate(self):
        print("Calibrating, please wait")
        Ax_list = []
        Ay_list = []
        Az_list = []

        for i in range(1, 1000):
            Ax, Ay, Az = i2c.get_values()
            if i == 1:
                time.sleep(1)
            Ax_list.append(Ax)
            Ay_list.append(Ay)
            Az_list.append(Az)
            
        self.x_offset = np.mean(Ax_list)
        self.y_offset = np.mean(Ay_list)
        self.z_offset = np.mean(Az_list)

        if self.x_offset == 0.0 or self.y_offset == 0.0 or self.z_offset == 0.0:
            print('----- Recalibrating -----')
            _, _, _ = self.calibrate()

        print("Calibrated values: Ax: {}, Ay: {}, Az: {}".format(self.x_offset, self.y_offset, self.z_offset))

        return self.x_offset, self.y_offset, self.z_offset
        
    def send_after_calib(self):
        self.update_values()
        self.send_accel()
        
    def add_to_time(self):
        act_time = time.perf_counter()
        dt = act_time - self.current_t
        self.t = act_time - self.start_time
        self.dt = dt
        self.current_t = act_time
        
    def update(self):
        self.update_values()
        self.i += 1
        if self.t > 1 and self.i%10:
            self.send_accel()

    def send_accel(self):
        send_values = [self.t, self.ax_rms, self.ay_rms, self.az_rms]
        try:
            self.client.Write(self.tag_X, send_values)
        except Exception as e:
            print(f'Failed to send values of acceleration: {e}')
        except:
            print('Failed to send values of acceleration')
      
    def calc_rms(self,data_array):
        squared = np.array(data_array) ** 2
        mean_squared = np.mean(squared)
        rms_value = np.sqrt(mean_squared)
        return rms_value
        
    def update_values(self):
            
        self.count +=1
        
        Ax, Ay, Az = i2c.get_values()
        
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
        
        if self.count == self.N:
            _ = self.save_data_to_csv()
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
        folder_path = os.path.join(os.getcwd(), self.foldername)
        os.makedirs(folder_path, exist_ok=True)

        # Create the file name based on the current date and time of program start
        start_time = datetime.now()
        file_name = self.filename +"_"+start_time.strftime("%d-%m-%y_%H-%M.csv")
        self.file_path = os.path.join(folder_path, file_name)

        # Write headers to the CSV file
        with open(self.file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['time', 'accel_x', 'accel_y', 'accel_z'])
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
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data_to_write)
            
        self.clear_history()
        
    def clear_history(self):
        self.X_history.clear()
        self.Y_history.clear()
        self.Z_history.clear()
        self.t_history.clear()