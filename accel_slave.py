import time
import socket
import signal
import sys
import pylogix as pl
import accel_logger as alo
import accel_utils as aul

host = '0.0.0.0'  # Listen on all available interfaces
port = 65410   # Arbitrary non-privileged port

save_every = 1000
desired_hz = 160
    
tag_init = 'RB_INIT'
tag_X = 'RB_501A_X'

ip_address = '192.168.168.46'
client = pl.PLC(ip_address)
client.SocketTimeout = 100

testing = False
    
if __name__ == '__main__':
    child_script = "heartbeatA.py"
    
    try:
        child_process = aul.start_child_process(child_script)
    except Exception as e:
        print(f"Error starting heartbeat process: {e}")
        sys.exit(1)
    

    signal.signal(signal.SIGINT, aul.signal_handler)
    signal.signal(signal.SIGTERM, aul.signal_handler)

    print(f"Started heartbeat process with PID: {child_process.pid}")
    
    try:
        connection, server_socket = aul.start_server(host, port)
    except Exception as e:
        aul.handle_exception(e, connection, server_socket, child_process)
    
    try:
        print('Waiting for folder and file names')
        foldername = aul.receive_string(connection)
        filename = aul.receive_string(connection)
        
    except Exception as e:
        aul.handle_exception(e, connection, server_socket, child_process)
        
    try:
        print('Init logger')
        sensor = alo.AccelerometerLogger(filename, foldername, save_every, client, tag_X, desired_hz=desired_hz)
        sensor.calibrate()
        sensor.send_after_calib()
     
    except Exception as e:
        aul.handle_exception(e, connection, server_socket, child_process)

    try:
        if not testing:
            aul.wait_for_plc(client,tag_init)
        sensor.current_t = time.time()
        print('Running!')
        sensor.run()
            
    except Exception as e:
        aul.handle_exception(e, connection, server_socket, child_process)
        
    except KeyboardInterrupt:
        aul.cleanup(connection, server_socket, child_process)
        sys.exit(0)

    finally:
        aul.cleanup(connection, server_socket, child_process)
        sys.exit(0)

