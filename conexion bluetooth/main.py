import machine
import bluetooth
import time
from machine import Pin
from ble_simple_peripheral import BLESimplePeripheral

# Configuración del LED de placa para pruebas
led = Pin(2, Pin.OUT)

# Iniciar Bluetooth
ble = bluetooth.BLE()
sp = BLESimplePeripheral(ble, "Cortina_ESP32")

def procesar_comando(datos):
    # Decodificar el mensaje recibido desde el bloque WriteStrings de la App
    mensaje = datos.decode().strip()
    
    print("-" * 25)
    print(f"RECIBIDO: {mensaje}")
    
    # Lógica de comandos
    if mensaje == "A":
        print("ACCIÓN: Abriendo cortina...")
        led.value(1) # LED Encendido
    elif mensaje == "M":
        print("ACCIÓN: Posición media (50%)")
    elif mensaje == "C":
        print("ACCIÓN: Cerrando cortina...")
        led.value(0) # LED Apagado
    elif mensaje == "1":
        print("MODO: Automático Convencional")
    elif mensaje == "2":
        print("MODO: Automático Invertido")
    else:
        print("Comando no reconocido")
    print("-" * 25)

# Configurar la respuesta al recibir datos
sp.on_write(procesar_comando)

print("ESP32 Listo. Nombre: Cortina_ESP32")
print("Esperando conexión desde MIT App Inventor...")

while True:
    time.sleep(1)