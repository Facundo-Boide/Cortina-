import machine
from machine import Pin
import time

# Configuración de los pines (usando los que definimos para el código principal)
hall_0 = Pin(14, Pin.IN) # Abajo (Cerrado)
hall_1 = Pin(22, Pin.IN) # Medio
hall_2 = Pin(23, Pin.IN) # Arriba (Abierto)

print("--- IDENTIFICADOR DE SENSORES HALL ---")
print("Lógica: 1 = Reposo / 0 = Imán detectado")
print("---------------------------------------")

while True:
    # Leemos los 3 sensores
    v0 = hall_0.value()
    v1 = hall_1.value()
    v2 = hall_2.value()
    
    # Imprimimos los valores en una sola línea para que sea fácil de seguir
    if hall_0.value() == 0:
        print("hall 1")
    if hall_1.value() == 0:
        print("hall 2")
    if hall_2.value() == 0:
        print("hall 3")        
    # Pequeña pausa para que la consola no vuele
    time.sleep_ms(200)