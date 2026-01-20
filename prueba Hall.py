import machine 
from machine import Pin
import time

# Pin 14 con Pull-Up interno
sensor_hall = Pin(14, Pin.IN, Pin.PULL_UP)
led = Pin(2, Pin.OUT) 

print("--- PRUEBA PUNTUAL DEL SENSOR HALL ---")
print("Esperando imán...")

while True:
    # Si el valor es 0, significa que el imán ESTÁ presente
    if sensor_hall.value() == 0:
        print("ESTADO: ¡IMÁN DETECTADO!")
        led.value(0)
    else:
        # Si el valor es 1, NO hay imán
        led.value(1)
    
    time.sleep(0.1)