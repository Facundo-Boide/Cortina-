import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import utime

# --- 1. CONFIGURACIÓN DE HARDWARE (Pines actualizados) ---
step_pin = Pin(25, Pin.OUT)
dir_pin = Pin(27, Pin.OUT)
enable_pin = Pin(12, Pin.OUT) # Pin que silencia el motor

# El A4988 se activa con LOW. Lo iniciamos en HIGH (apagado/silencio)
enable_pin.value(1)

# Sensores LDR
ldr1 = ADC(Pin(33)); ldr2 = ADC(Pin(32)); ldr3 = ADC(Pin(35))
ldr1.atten(ADC.ATTN_11DB); ldr2.atten(ADC.ATTN_11DB); ldr3.atten(ADC.ATTN_11DB)

# Sensor Hall (Imán)
hall_0 = Pin(14, Pin.IN, Pin.PULL_UP) 

# --- 2. VARIABLES DE CONTROL ---
pasos_actuales = 0
pasos_totales = 0  
posicion_logica = 0 
modo = "0"
delay_paso_us = 2000 # Velocidad que te funcionó en la prueba

# Variables para estabilidad de LDR
ultima_sugerencia = 0
contador_estabilidad = 0
TIEMPO_CONFIRMACION = 5 

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

# --- 4. FUNCIONES DEL MOTOR (Lógica de prueba aplicada) ---

def motor_on():
    enable_pin.value(0) # Activa el driver
    utime.sleep_ms(10)  # Estabilización

def motor_off():
    enable_pin.value(1) # Apaga el driver (Silencio total)

def dar_paso_fisico():
    step_pin.value(1)
    utime.sleep_us(delay_paso_us)
    step_pin.value(0)
    utime.sleep_us(delay_paso_us)

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
        
        # Lógica del Imán Hall
        if pasos_actuales < 150 and hall_0.value() == 0:
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
    
    for _ in range(40): dar_paso_fisico()
            
    motor_off()
    pasos_totales = contador 
    pasos_actuales = 0        
    posicion_logica = 0

# --- 5. EJECUCIÓN INICIAL ---
motor_off()
calibrar_inicial() 

# --- 6. BUCLE PRINCIPAL ---
while True:
    if sp.is_connected() and modo in ["1", "2"]:
        luz = (ldr1.read() + ldr2.read() + ldr3.read()) / 3
        
        if modo == "1":
            if luz < 1800: sug = 0
            elif 1800 <= luz < 3400: sug = 1
            else: sug = 2
        else: 
            if luz > 3400: sug = 0
            elif 1800 <= luz < 3400: sug = 1
            else: sug = 2

        if sug != posicion_logica:
            if sug == ultima_sugerencia:
                contador_estabilidad += 1
            else:
                ultima_sugerencia = sug
                contador_estabilidad = 0
            
            if contador_estabilidad >= TIEMPO_CONFIRMACION:
                viajar_a(sug)
                contador_estabilidad = 0
        else:
            contador_estabilidad = 0
            
    utime.sleep_ms(1000)