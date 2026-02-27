import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import time
import _thread 

# --- 1. PINES DRIVER A4988 ---
step_pin = Pin(12, Pin.OUT)
dir_pin = Pin(27, Pin.OUT)
res_slp = Pin(25, Pin.OUT)

# --- 2. SENSORES DE LUZ (LDR) ---
ldr1 = ADC(Pin(33)); ldr1.atten(ADC.ATTN_11DB)
ldr2 = ADC(Pin(32)); ldr2.atten(ADC.ATTN_11DB)
ldr3 = ADC(Pin(35)); ldr3.atten(ADC.ATTN_11DB)

# --- 3. SENSOR HALL (Único final de carrera - ABAJO) ---
hall_0 = Pin(14, Pin.IN) 

# --- 4. VARIABLES GLOBALES ORIGINALES ---
posicion_actual = 0
modo = "0"
objetivo_sugerido = 0 

# --- 5. VARIABLES PARA MOTOR PASO A PASO ---
pasos_actuales = 0
MAX_PASOS = 0 # Se calcula solo en la calibración inicial

ble = bluetooth.BLE()                                              
sp = BLESimplePeripheral(ble, "Cortina_ESP32")

# =================================================================
# FUNCIONES DEL MOTOR
# =================================================================
def detener_motor():
    res_slp.value(0) # Apaga el driver para que el motor no caliente

def mover_motor(sentido):
    if res_slp.value() == 0:
        res_slp.value(1)
        time.sleep_ms(5) # Tiempo para despertar al chip
        
    if sentido == "ABRIR":
        dir_pin.value(0)
    else: # CERRAR
        dir_pin.value(1)
        
    # Pulso del paso (Acá regulás la velocidad total)
    step_pin.value(1)
    time.sleep_us(1200) 
    step_pin.value(0)
    time.sleep_us(1200)

def calibrar_auto_ubicacion():
    global pasos_actuales, posicion_actual, MAX_PASOS
    print("\n[SISTEMA] Calibrando: Midiendo el largo de la ventana...")
    
    contador_pasos = 0
    
    # Baja y cuenta pasos hasta tocar el imán
    while hall_0.value() == 1:
        mover_motor("CERRAR")
        contador_pasos += 1
        
        # Seguridad por si se traba
        if contador_pasos > 50000:
            print("[ERROR] Límite excedido. Sensor no detectado.")
            break
            
    # Asentamiento para tensar la tela
    for _ in range(40): 
        mover_motor("CERRAR")
        contador_pasos += 1
    
    detener_motor()
    
    MAX_PASOS = contador_pasos 
    pasos_actuales = 0 # Cero absoluto
    posicion_actual = 0
    print(f"[EXITO] Cortina cerrada. Ventana medida en: {MAX_PASOS} pasos.\n")

def procesar_comando(datos):
    global modo
    recibido = datos.decode().strip().replace('\x00', '')
    if recibido == "" or recibido == "\x00": return 
    print(f"\nDATO BT RECIBIDO: '{recibido}'\n")
    modo = recibido

sp.on_write(procesar_comando)

# =================================================================
# 🧠 NÚCLEO 1: HILO DEDICADO AL MOTOR (Control exacto de pasos)
# =================================================================
def hilo_motor():
    global posicion_actual, objetivo_sugerido, pasos_actuales
    
    while True:
        if posicion_actual != objetivo_sugerido and MAX_PASOS > 0:
            
            while True:
                # Traducir el objetivo (0, 1, 2) a cantidad de pasos
                if objetivo_sugerido == 0: target = 0
                elif objetivo_sugerido == 1: target = MAX_PASOS // 2
                elif objetivo_sugerido == 2: target = MAX_PASOS
                else: target = pasos_actuales
                
                # Si llegó al objetivo, rompe el bucle de viaje
                if pasos_actuales == target:
                    break
                    
                # Si falta subir
                if target > pasos_actuales:
                    mover_motor("ABRIR")
                    pasos_actuales += 1
                    
                # Si falta bajar
                elif target < pasos_actuales:
                    mover_motor("CERRAR")
                    pasos_actuales -= 1
                    
                    # Interrupción de seguridad: Si el imán toca el sensor antes de tiempo
                    if hall_0.value() == 0:
                        for _ in range(40): mover_motor("CERRAR")
                        pasos_actuales = 0
                        break
            
            # Actualiza el estado final y apaga todo
            posicion_actual = objetivo_sugerido
            detener_motor()
        else:
            time.sleep_ms(10) # Descanso del núcleo si no hay que moverse

# =================================================================
# INICIO DEL SISTEMA
# =================================================================
print("ESP32 Listo. Nombre: Cortina_ESP32")

# IMPORTANTE: La cortina debe estar enrollada ARRIBA al darle corriente
calibrar_auto_ubicacion()

# Iniciamos el motor en el núcleo secundario paralelo
_thread.start_new_thread(hilo_motor, ())

estado_anterior = ""
ultima_sugerencia_temp = -1
tiempo_estabilidad = time.time()

# =================================================================
# 🧠 NÚCLEO 0: HILO PRINCIPAL (Sensores LDR y Bluetooth)
# =================================================================
while True:										
    if sp.is_connected():
        # Lectura promedio de LDR
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
            
            # Temporizador Anti-Nubes de 10 segundos
            if sugerencia_temp != ultima_sugerencia_temp:
                ultima_sugerencia_temp = sugerencia_temp
                tiempo_estabilidad = time.time()
                
            if (time.time() - tiempo_estabilidad) >= 10:
                objetivo_sugerido = sugerencia_temp 
        
        # Modo manual desde la app
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
            
    # El núcleo 0 descansa 100ms porque el motor ya está siendo controlado por el núcleo 1
    time.sleep_ms(100)