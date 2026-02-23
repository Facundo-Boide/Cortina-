import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import time

# --- 1. CONFIGURACIÓN DE HARDWARE ---
pins = [Pin(21, Pin.OUT), Pin(19, Pin.OUT), Pin(18, Pin.OUT), Pin(5, Pin.OUT)]

secuencia = [
    (1, 0, 1, 0),
    (0, 1, 1, 0),
    (0, 1, 0, 1),
    (1, 0, 0, 1)
]

ldr1 = ADC(Pin(33)); ldr2 = ADC(Pin(32)); ldr3 = ADC(Pin(35))
ldr1.atten(ADC.ATTN_11DB); ldr2.atten(ADC.ATTN_11DB); ldr3.atten(ADC.ATTN_11DB)

# Solo conservamos el Hall 0 (Punto de referencia: ABAJO/CERRADO)
hall_0 = Pin(14, Pin.IN) 

# --- 2. VARIABLES DE CONTROL DINÁMICO ---
pasos_actuales = 0
pasos_totales = 0  
posicion_logica = 0 
modo = "0"
delay_paso = 5 / 1000

# --- 3. BLUETOOTH ---
ble = bluetooth.BLE()
sp = BLESimplePeripheral(ble, "Cortina_ESP32")

def procesar_comando(datos):
    global modo
    recibido = datos.decode().strip().replace('\x00', '')
    if recibido in ["1", "2"]:
        modo = recibido
        print(f"[BT] Modo Auto {modo}")
    elif recibido in ["A", "M", "C"]:
        modo = "M"
        if recibido == "A": viajar_a(2) # Abrir (al 100% de pasos medidos)
        elif recibido == "M": viajar_a(1) # Medio (al 50% de pasos medidos)
        elif recibido == "C": viajar_a(0) # Cerrar (al paso 0)

sp.on_write(procesar_comando)

# --- 4. FUNCIONES DEL MOTOR ---
def motor_off():
    for pin in pins: pin.value(0)

def dar_paso_fisico(p):
    # Usamos el valor absoluto del paso para que la secuencia siempre sea positiva
    idx = abs(p) % 4
    for i in range(4):
        pins[i].value(secuencia[idx][i])
    time.sleep(delay_paso)

def viajar_a(id_objetivo):
    global pasos_actuales, posicion_logica, pasos_totales
    
    if pasos_totales == 0: return # No se ha calibrado aún

    objetivos = {0: 0, 1: pasos_totales // 2, 2: pasos_totales}
    target_pasos = objetivos[id_objetivo]
    
    print(f"[MOTOR] Ir a {target_pasos} pasos")

    while pasos_actuales != target_pasos:
        if pasos_actuales < target_pasos:
            pasos_actuales += 1
        else:
            pasos_actuales -= 1
        
        dar_paso_fisico(pasos_actuales)
        
        # Seguridad: Si bajando toca el sensor antes de tiempo
        if pasos_actuales < 50 and hall_0.value() == 0:
            pasos_actuales = 0
            break

    motor_off()
    posicion_logica = id_objetivo

def calibrar_inicial():
    global pasos_actuales, posicion_logica, pasos_totales
    print("\n[INICIO] Calibrando: Bajando para medir pasos...")
    
    contador = 0
    # Bajamos hasta que el Hall 0 detecte el imán (valor 0)
    while hall_0.value() == 1:
        contador += 1
        # Bajamos usando pasos negativos para la secuencia
        dar_paso_fisico(-contador)
        
        # Timeout por si algo falla (evitar que el motor gire infinito)
        if contador > 15000: 
            print("[ERROR] No se detectó sensor.")
            break

    motor_off()
    pasos_totales = contador # Guardamos el recorrido total detectado
    pasos_actuales = 0       # Estamos abajo (0)
    posicion_logica = 0
    print(f"[OK] Medido: {pasos_totales} pasos. Cortina Cerrada.\n")

# --- 5. EJECUCIÓN ---
motor_off()
calibrar_inicial() # Se ejecuta AUTOMÁTICAMENTE al prenderse

while True:
    if sp.is_connected():
        if modo in ["1", "2"]:
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
                viajar_a(sug)
    
    time.sleep_ms(1000)