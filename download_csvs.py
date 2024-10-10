import subprocess

# Define the IPs of the Raspberry Pis and the download details
folder = input('Nombre de carpeta a extraer: ')
raspberry_pis = [
    {
        'ip': '192.168.168.66',
        'folder_name': f'{folder}',
        'output_path': r"C:\Users\Ignacio Medina\Data\BPAE-vibracion\{}_A.zip".format(folder)
    },
    {
        'ip': '192.168.168.32',  # Change this to the second Raspberry Pi's IP
        'folder_name': f'{folder}',
        'output_path': r"C:\Users\Ignacio Medina\Data\BPAE-vibracion\{}_B.zip".format(folder)
    }
]

# Function to call the API and download the ZIP file
def download_csvs(rpi):
    uri = f"http://{rpi['ip']}:5000/get-csvs/{rpi['folder_name']}"
    command = [
        'powershell.exe', 
        '-Command', 
        f"Invoke-WebRequest -Uri '{uri}' -OutFile '{rpi['output_path']}'"
    ]
    
    try:
        subprocess.run(command, check=True)
        print(f"Downloaded from {rpi['ip']} successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to download from {rpi['ip']}: {e}")

# Download from both Raspberry Pis
for rpi in raspberry_pis:
    download_csvs(rpi)
