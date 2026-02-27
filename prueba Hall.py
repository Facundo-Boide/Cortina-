import machine
from machine import Pin
import time

# Configuración de los pines (usando los que definimos para el código principal)
hall_0 = Pin(14, Pin.IN) # Abajo (Cerrado)

print("--- IDENTIFICADOR DE SENSORES HALL ---")
print("Lógica: 1 = Reposo / 0 = Imán detectado")
print("---------------------------------------")

while True:
    # Leemos los 3 sensores
    v0 = hall_0.value()
    
    # Imprimimos los valores en una sola línea para que sea fácil de seguir
    if hall_0.value() == 0:
        print("hall 1")
      
    # Pequeña pausa para que la consola no vuele
    time.sleep_ms(200)