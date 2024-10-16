import time
import socket
import signal
import sys
import pylogix as pl
import accel_logger as alo
import accel_utils as aul

host = '192.168.168.67'  
port = 65410

foldername = 'pruebas-full-1610'  

save_every = 1000
desired_hz = 160

tag_init = 'RB_INIT'
tag_X = 'RB_501B_X'
ip_address = '192.168.168.46'

client = pl.PLC(ip_address)
client.SocketTimeout = 100

testing = False

if __name__ == '__main__':
    child_script = "heartbeatB.py"

    try:
        child_process = aul.start_child_process(child_script)
    except Exception as e:
        print(f"Error starting heartbeat process: {e}")
        sys.exit(1)

    signal.signal(signal.SIGINT, aul.signal_handler)
    signal.signal(signal.SIGTERM, aul.signal_handler)

    print(f"Started heartbeat process with PID: {child_process.pid}")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))

    except socket.error as e:
        print(f"Socket error: {e}")
        aul.stop_child_process(child_process)
        sys.exit(1)

    try:
        aul.send_string(client_socket, foldername)  
        filename = input('File Name: ')
        aul.send_string(client_socket, filename)

    except Exception as e:
        print(f"Error sending data: {e}")
        client_socket.close()
        aul.stop_child_process(child_process)
        sys.exit(1)

    try:
        print('Init Logger')
        sensor = alo.AccelerometerLogger(filename, foldername, save_every, client, tag_X, desired_hz=desired_hz) 
        sensor.calibrate()
        sensor.send_after_calib()

    except Exception as e:
        print(f"Sensor initialization or calibration error: {e}")
        client_socket.close()
        aul.stop_child_process(child_process)
        sys.exit(1)

    try:
        if not testing:
            aul.wait_for_plc(client, tag_init)
        sensor.current_t = time.time()
        print('Running!')
        sensor.run()

    except Exception as e:
        print(f"Communication error or sensor run error: {e}")
        aul.stop_child_process(child_process)
        sys.exit(1)

    except KeyboardInterrupt:
        aul.stop_child_process(child_process)
        sys.exit(0)

    finally:
        client_socket.close()
        aul.stop_child_process(child_process)
        sys.exit(0)
