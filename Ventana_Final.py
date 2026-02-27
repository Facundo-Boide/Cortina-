import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import time
import _thread # <--- Módulo mágico para usar el segundo núcleo

# --- PINES DRIVER A4988 ---
step_pin = Pin(12, Pin.OUT)
dir_pin = Pin(27, Pin.OUT)
res_slp = Pin(25, Pin.OUT)

ldr1 = ADC(Pin(33))
ldr1.atten(ADC.ATTN_11DB)
ldr2 = ADC(Pin(32))
ldr2.atten(ADC.ATTN_11DB)
ldr3 = ADC(Pin(35))
ldr3.atten(ADC.ATTN_11DB)

hall_0 = Pin(14, Pin.IN) # Cerrado hall N°1
hall_1 = Pin(23, Pin.IN) # Medio hall N°2
hall_2 = Pin(22, Pin.IN) # Abierto hall N°3
sensores = [hall_0, hall_1, hall_2]

# --- VARIABLES GLOBALES COMPARTIDAS ENTRE NÚCLEOS ---
posicion_actual = 0
modo = "0"
objetivo_sugerido = 0 # Ahora es global para que ambos núcleos la vean

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
    time.sleep_us(1200) # Velocidad (Clock manual)
    step_pin.value(0)
    time.sleep_us(1200)

def calibrar_auto_ubicacion():
    global posicion_actual
    print("\n[SISTEMA] Iniciando Auto-Ubicación...")
    encontrado = False
    inicio = time.time()
    
    while (time.time() - inicio) < 10:
        mover_motor("CERRAR")
        for i in range(3):
            if sensores[i].value() == 0:
                posicion_actual = i
                encontrado = True
                for _ in range(40): mover_motor("CERRAR")
                break
        if encontrado: break
    
    if not encontrado:
        detener_motor()
        time.sleep_ms(500)
        inicio = time.time()
        
        while not encontrado:
            mover_motor("ABRIR")
            for i in range(3):
                if sensores[i].value() == 0:
                    posicion_actual = i
                    encontrado = True
                    for _ in range(40): mover_motor("ABRIR")
                    break
            if encontrado: break
            if (time.time() - inicio) > 15: break

    detener_motor()
    if encontrado:
        print(f"[EXITO] Sensor {posicion_actual} detectado.\n")

def procesar_comando(datos):
    global modo
    recibido = datos.decode().strip().replace('\x00', '')
    if recibido == "" or recibido == "\x00": return 
    print(f"\nDATO REAL RECIBIDO: '{recibido}'\n")
    modo = recibido

sp.on_write(procesar_comando)

# =================================================================
# 🧠 NÚCLEO 1: HILO DEDICADO EXCLUSIVAMENTE AL MOTOR
# =================================================================
def hilo_motor():
    global posicion_actual, objetivo_sugerido
    
    while True:
        # El motor corre en un núcleo separado. NADA lo frena.
        if posicion_actual != objetivo_sugerido:
            
            if posicion_actual == 0:
                if objetivo_sugerido == 2:
                    mover_motor("ABRIR")
                    if hall_2.value() == 0:
                        for _ in range(40): mover_motor("ABRIR")
                        posicion_actual = objetivo_sugerido
                        detener_motor()
                        
                elif objetivo_sugerido == 1:
                    mover_motor("ABRIR")
                    if hall_1.value() == 0:
                        for _ in range(40): mover_motor("ABRIR")
                        posicion_actual = objetivo_sugerido
                        detener_motor()                         
                        
            elif posicion_actual == 1:
                if objetivo_sugerido == 0:
                    mover_motor("CERRAR")
                    if hall_0.value() == 0:
                        for _ in range(40): mover_motor("CERRAR")
                        posicion_actual = objetivo_sugerido
                        detener_motor()                         
                        
                elif objetivo_sugerido == 2:
                    mover_motor("ABRIR")
                    if hall_2.value() == 0:
                        for _ in range(40): mover_motor("ABRIR")
                        posicion_actual = objetivo_sugerido
                        detener_motor()                            
                        
            elif posicion_actual == 2:
                if objetivo_sugerido == 1:
                    mover_motor("CERRAR")
                    if hall_1.value() == 0:  
                        for _ in range(40): mover_motor("CERRAR")
                        posicion_actual = objetivo_sugerido
                        detener_motor()                            
                        
                elif objetivo_sugerido == 0:
                    mover_motor("CERRAR")
                    if hall_0.value() == 0:
                        for _ in range(40): mover_motor("CERRAR")
                        posicion_actual = objetivo_sugerido
                        detener_motor()
        else:
            # Si no hay que moverse, le damos un pequeñísimo descanso al núcleo
            time.sleep_ms(10)

# =================================================================
# INICIO DEL SISTEMA
# =================================================================
print("ESP32 Listo. Nombre: Cortina_ESP32")
calibrar_auto_ubicacion()

# ¡ACÁ SE ENCIENDE EL SEGUNDO NÚCLEO!
_thread.start_new_thread(hilo_motor, ())

estado_anterior = ""
ultima_sugerencia_temp = -1
tiempo_estabilidad = time.time()

# =================================================================
#   NÚCLEO 0: HILO PRINCIPAL (Sensores LDR y Bluetooth)
# =================================================================
while True:										
    if sp.is_connected():
        ldr_value1 = ldr1.read()
        ldr_value2 = ldr2.read()
        ldr_value3 = ldr3.read()
        
        ldr_prom1 = ldr_value1 + ldr_value2 + ldr_value3
        ldr_g = ldr_prom1 / 3
        
        sugerencia_temp = objetivo_sugerido # Por defecto, mantiene el actual

        if modo == "1" or modo == "2":                                                                  
            if modo == "1": 
                if ldr_g < 1800: sugerencia_temp = 0
                elif 1800 <= ldr_g < 3400: sugerencia_temp = 1
                elif ldr_g >= 3400: sugerencia_temp = 2
                                                                                    
            if modo == "2":
                if ldr_g >= 3400: sugerencia_temp = 0
                elif 1800 <= ldr_g < 3400: sugerencia_temp = 1
                elif ldr_g < 1800: sugerencia_temp = 2
            
            # Validación de 10 segundos
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
            
    # El núcleo 0 puede descansar tranquilamente 100ms, total el motor corre en el otro núcleo
    time.sleep_ms(100)