import requests
import random
import time

API_URL = "http://127.0.0.1:8000/sensor-data"

SENSORS = [
    "TEMP_SENSOR_01",
    "TEMP_SENSOR_02",
    "GAS_SENSOR_01",
    "GAS_SENSOR_02",
]

def generate_data(sensor_id):
    return {
        "device_id": sensor_id,
        "temperature": round(random.uniform(25, 95), 2),
        "gas_level": round(random.uniform(40, 450), 2),
    }

while True:
    for sensor in SENSORS:
        payload = generate_data(sensor)
        try:
            r = requests.post(API_URL, json=payload)
            print("Sent:", payload, "| Status:", r.status_code)
        except Exception as e:
            print("Error:", e)

    time.sleep(1)  
