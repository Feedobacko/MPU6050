from flask import Flask, send_file, jsonify
import os
import zipfile

app = Flask(__name__)

@app.route('/get-csvs/<folder_name>', methods=['GET'])
def get_csvs(folder_name):
    home = os.path.expanduser('~') 
    
    folder_path = os.path.join(home,'Desktop', 'MPU6050') # Cambia esto a la ruta donde están tus archivos CSV
    zip_filename = f'{folder_name}.zip'

    # Crear un archivo zip con todos los CSVs
    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        for filename in os.listdir(folder_path):
            if filename.endswith('.csv'):
                zip_file.write(os.path.join(folder_path, filename), filename)

    return send_file(zip_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
