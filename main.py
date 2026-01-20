import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import time

m1 = Pin(22, Pin.OUT)
m2 = Pin(23, Pin.OUT)

ldr1 = ADC(Pin(33))
ldr1.atten(ADC.ATTN_11DB)
ldr2 = ADC(Pin(32))
ldr2.atten(ADC.ATTN_11DB)
ldr3 = ADC(Pin(35))
ldr3.atten(ADC.ATTN_11DB)

modo = "0"

ble = bluetooth.BLE()                                              #bluetooth
sp = BLESimplePeripheral(ble, "Cortina_ESP32")

def procesar_comando(datos):
    global modo
    # Recibe "1" o "2" desde el bloque WriteStrings de tu App
    modo = datos.decode().strip()
    print("\n" + "="*30)
    print(f" CAMBIO DE MODO RECIBIDO: {modo} ")
    print("="*30 + "\n")
print("ESP32 Listo. Nombre: Cortina_ESP32")
print("Esperando conexión desde MIT App Inventor...")






i = True
estado_anterior = ""

while (i == True):										#chequeo 
    
    if sp.is_connected():
        
        ldr_prom1 = 0
        ldr_g = 0
        
        ldr_value1 = ldr1.read()

        ldr_value2 = ldr2.read()

        ldr_value3 = ldr3.read()
        
        ldr_prom1 = ldr_value1 + ldr_value2 + ldr_value3
        
        ldr_g = ldr_prom1 / 3
        
        estado_actual = ""

        if modo == "1" or modo == "2":                                                                  #modo auto 1
            if modo == "1": 
                if ldr_g < 1800:														#deliveracion 
            
                    estado_actual = "cortina cerrado"
            
                elif ldr_g > 1800 and ldr_g < 3400:  
            
                    estado_actual = "media cortina"
            
                elif ldr_g > 3400 and ldr_g <= 4095:
            
                    estado_actual = "cortina abierta"
                                                                                    #modo auto 2
            if modo == "2":
                if ldr_g > 3400 and ldr_g <= 4095:														#deliveracion 
               
                    estado_actual = "cortina cerrado"
            
                elif ldr_g > 1800 and ldr_g < 3400:  
            
                    estado_actual = "media cortina"
                   
                elif ldr_g < 1800:
            
                    estado_actual = "cortina abierta"
            
            if estado_actual != estado_anterior:
                print (f"Estado: {estado_actual}")
                estado_anterior = estado_actual
            
        
        
    
