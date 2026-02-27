import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import time
import _thread 

# --- PINES DRIVER A4988 ---
step_pin = Pin(12, Pin.OUT)
dir_pin = Pin(27, Pin.OUT)
res_slp = Pin(25, Pin.OUT)

# --- SENSORES DE LUZ ---
ldr1 = ADC(Pin(33)); ldr1.atten(ADC.ATTN_11DB)
ldr2 = ADC(Pin(32)); ldr2.atten(ADC.ATTN_11DB)
ldr3 = ADC(Pin(35)); ldr3.atten(ADC.ATTN_11DB)

# --- SENSOR HALL (Único final de carrera - ABAJO) ---
hall_0 = Pin(14, Pin.IN) 

# --- VARIABLES GLOBALES ORIGINALES ---
posicion_actual = 0
modo = "0"
objetivo_sugerido = 0 

# --- NUEVAS VARIABLES PARA MOTOR PASO A PASO ---
pasos_actuales = 0
MAX_PASOS = 15000 # <--- AJUSTAR: Cantidad total de pasos desde cerrado hasta abierto al 100%

ble = bluetooth.BLE()                                              
sp = BLESimplePeripheral(ble, "Cortina_ESP32")

def detener_motor():
    res_slp.value(0)

def mover_motor(sentido):
    if res_slp.value() == 0:
        res_slp.value(1)
        time.sleep_ms(5)
        
    if sentido == "ABRIR":
        dir_pin.value(0)
    else: # CERRAR
        dir_pin.value(1)
        
    step_pin.value(1)
    time.sleep_us(1200) # <--- AJUSTAR: Velocidad del motor
    step_pin.value(0)
    time.sleep_us(1200)

def calibrar_auto_ubicacion():
    global pasos_actuales, posicion_actual
    print("\n[SISTEMA] Iniciando Auto-Ubicación (Homing)...")
    
    # El motor baja hasta que el imán toca el sensor
    while hall_0.value() == 1:
        mover_motor("CERRAR")
        
    # Asentamiento para tensar la tela
    for _ in range(40): mover_motor("CERRAR")
    
    detener_motor()
    pasos_actuales = 0 # Definimos el Cero absoluto
    posicion_actual = 0
    print("[EXITO] Cortina cerrada. Posición 0 calibrada.\n")

def procesar_comando(datos):
    global modo
    recibido = datos.decode().strip().replace('\x00', '')
    if recibido == "" or recibido == "\x00": return 
    print(f"\nDATO BT RECIBIDO: '{recibido}'\n")
    modo = recibido

sp.on_write(procesar_comando)

# =================================================================
# 🧠 NÚCLEO 1: HILO DEDICADO AL MOTOR (Control por Pasos)
# =================================================================
def hilo_motor():
    global posicion_actual, objetivo_sugerido, pasos_actuales
    
    while True:
        if posicion_actual != objetivo_sugerido:
            
            # 1. Traducir el objetivo (0, 1, 2) a cantidad de pasos
            if objetivo_sugerido == 0: target = 0
            elif objetivo_sugerido == 1: target = MAX_PASOS // 2  # Mitad matemática
            elif objetivo_sugerido == 2: target = MAX_PASOS       # Apertura total
            else: target = pasos_actuales
            
            # 2. Viajar hasta el objetivo contando pasos
            while pasos_actuales != target:
                
                # Permite cambiar de opinión a mitad de camino
                if objetivo_sugerido == 0: target = 0
                elif objetivo_sugerido == 1: target = MAX_PASOS // 2
                elif objetivo_sugerido == 2: target = MAX_PASOS
                
                if target > pasos_actuales:
                    mover_motor("ABRIR")
                    pasos_actuales += 1
                elif target < pasos_actuales:
                    mover_motor("CERRAR")
                    pasos_actuales -= 1
                    
                    # Seguridad: Si bajando se cruza con el imán antes de llegar a 0
                    if hall_0.value() == 0:
                        for _ in range(40): mover_motor("CERRAR")
                        pasos_actuales = 0
                        break
            
            posicion_actual = objetivo_sugerido
            detener_motor()
        else:
            time.sleep_ms(10)

# =================================================================
# INICIO DEL SISTEMA
# =================================================================
print("ESP32 Listo. Nombre: Cortina_ESP32")
calibrar_auto_ubicacion()

# Iniciamos el motor en el núcleo secundario
_thread.start_new_thread(hilo_motor, ())

estado_anterior = ""
ultima_sugerencia_temp = -1
tiempo_estabilidad = time.time()

# =================================================================
# 🧠 NÚCLEO 0: HILO PRINCIPAL (Sensores LDR y Bluetooth)
# =================================================================
while True:										
    if sp.is_connected():
        ldr_prom1 = (ldr1.read() + ldr2.read() + ldr3.read())
        ldr_g = ldr_prom1 / 3
        
        sugerencia_temp = objetivo_sugerido 

        if modo == "1" or modo == "2":                                                                  
            if modo == "1": 
                if ldr_g < 1800: sugerencia_temp = 0
                elif 1800 <= ldr_g < 3400: sugerencia_temp = 1
                elif ldr_g >= 3400: sugerencia_temp = 2
                                                                                    
            if modo == "2":
                if ldr_g >= 3400: sugerencia_temp = 0
                elif 1800 <= ldr_g < 3400: sugerencia_temp = 1
                elif ldr_g < 1800: sugerencia_temp = 2
            
            # Temporizador de 10 segundos
            if sugerencia_temp != ultima_sugerencia_temp:
                ultima_sugerencia_temp = sugerencia_temp
                tiempo_estabilidad = time.time()
                
            if (time.time() - tiempo_estabilidad) >= 10:
                objetivo_sugerido = sugerencia_temp 
        
        elif modo in ["A", "M", "C"]:
            if modo == "C": objetivo_sugerido = 0
            elif modo == "M": objetivo_sugerido = 1
            elif modo == "A": objetivo_sugerido = 2
            
            tiempo_estabilidad = time.time()
            ultima_sugerencia_temp = -1
            
    else:
        if estado_anterior != "DESCONECTADO":
            print("Esperando conexión Bluetooth...")
            estado_anterior = "DESCONECTADO"
            modo = "0"
            
    time.sleep_ms(100)