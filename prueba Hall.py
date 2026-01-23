from machine import Pin
import time

# Pin 14 con tu resistencia física de 10k a 3.3V
sensor_hall = Pin(14, Pin.IN)
led = Pin(2, Pin.OUT) 

print("--- PRUEBA DE CONTEO (LÓGICA LATCH) ---")
print("Alterna los polos del imán frente al sensor...")

contador_imanes = 0
ultimo_estado = sensor_hall.value()

while True:
    estado_actual = sensor_hall.value()
    
    # Si el estado cambió (de 0 a 1 O de 1 a 0) significa que pasó un imán
    if estado_actual != ultimo_estado:
        contador_imanes += 1
        led.value(estado_actual) # El LED reflejará el estado del sensor
        print(f"Imán detectado! Contador: {contador_imanes} | Estado: {estado_actual}")
        
        ultimo_estado = estado_actual
        time.sleep_ms(200) # Anti-rebote para evitar conteos falsos
    
    time.sleep_ms(50)