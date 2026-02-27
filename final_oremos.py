import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import time

# --- 1. CONFIGURACIÓN DE HARDWARE ---
step_pin = Pin(12, Pin.OUT)
dir_pin = Pin(27, Pin.OUT)
res_slp = Pin(25, Pin.OUT) 

ldr1 = ADC(Pin(33)); ldr2 = ADC(Pin(32)); ldr3 = ADC(Pin(35))
ldr1.atten(ADC.ATTN_11DB); ldr2.atten(ADC.ATTN_11DB); ldr3.atten(ADC.ATTN_11DB)

hall_0 = Pin(14, Pin.IN, Pin.PULL_UP) 

# --- 2. VARIABLES DE CONTROL ---
pasos_actuales = 0
pasos_totales = 0  
posicion_logica = 0 
modo = "0"
delay_paso_us = 1200 # Velocidad ajustada para mayor torque

# Variables para el delay de los LDR
ultima_sugerencia = 0
contador_estabilidad = 0
TIEMPO_CONFIRMACION = 5 # Segundos que debe mantenerse la luz para mover

# --- 3. BLUETOOTH ---
ble = bluetooth.BLE()
sp = BLESimplePeripheral(ble, "Cortina_NEMA_Leo")

def procesar_comando(datos):
    global modo
    recibido = datos.decode().strip().replace('\x00', '')
    if recibido in ["1", "2"]:
        modo = recibido
    elif recibido in ["A", "M", "C"]:
        modo = "M"
        if recibido == "A": viajar_a(2)
        elif recibido == "M": viajar_a(1)
        elif recibido == "C": viajar_a(0)

sp.on_write(procesar_comando)

# --- 4. FUNCIONES DEL MOTOR ---
def motor_on():
    res_slp.value(1) 
    time.sleep_ms(5) # Delay de seguridad para despertar el driver

def motor_off():
    res_slp.value(0) 

def dar_paso_fisico():
    step_pin.value(1)
    time.sleep_us(delay_paso_us)
    step_pin.value(0)
    time.sleep_us(delay_paso_us)

def viajar_a(id_objetivo):
    global pasos_actuales, posicion_logica, pasos_totales
    if pasos_totales == 0: return 

    objetivos = {0: 0, 1: pasos_totales // 2, 2: pasos_totales}
    target_pasos = objetivos[id_objetivo]
    
    if target_pasos == pasos_actuales: return

    motor_on()
    dir_pin.value(1 if target_pasos > pasos_actuales else 0)

    while pasos_actuales != target_pasos:
        dar_paso_fisico()
        if target_pasos > pasos_actuales:
            pasos_actuales += 1
        else:
            pasos_actuales -= 1
        
        # --- MEJORA IMÁN: Delay de llegada ---
        if pasos_actuales < 150 and hall_0.value() == 0:
            # Cuando detecta el imán, da 40 pasos extra para "asentar" al fondo
            for _ in range(40): dar_paso_fisico()
            pasos_actuales = 0
            break

    motor_off()
    posicion_logica = id_objetivo

def calibrar_inicial():
    global pasos_actuales, posicion_logica, pasos_totales
    print("Calibrando...")
    motor_on()
    dir_pin.value(0) 
    
    contador = 0
    while hall_0.value() == 1:
        dar_paso_fisico()
        contador += 1
        if contador > 30000: break
    
    # Extra recorrido al final de la calibración
    for _ in range(40): dar_paso_fisico()
            
    motor_off()
    pasos_totales = contador 
    pasos_actuales = 0       
    posicion_logica = 0

# --- 5. EJECUCIÓN ---
motor_off()
calibrar_inicial() 

while True:
    if sp.is_connected() and modo in ["1", "2"]:
        luz = (ldr1.read() + ldr2.read() + ldr3.read()) / 3
        
        # Lógica de sugerencia
        if modo == "1":
            if luz < 1800: sug = 0
            elif 1800 <= luz < 3400: sug = 1
            else: sug = 2
        else: 
            if luz > 3400: sug = 0
            elif 1800 <= luz < 3400: sug = 1
            else: sug = 2

        # --- MEJORA LDR: Filtro de estabilidad ---
        if sug != posicion_logica:
            if sug == ultima_sugerencia:
                contador_estabilidad += 1
            else:
                ultima_sugerencia = sug
                contador_estabilidad = 0
            
            # Solo se mueve si la luz se mantiene estable por 5 segundos
            if contador_estabilidad >= TIEMPO_CONFIRMACION:
                viajar_a(sug)
                contador_estabilidad = 0
        else:
            contador_estabilidad = 0
            
    time.sleep_ms(1000)