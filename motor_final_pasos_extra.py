import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin
import time

# --- 1. CONFIGURACIÓN DE HARDWARE (STEPPER L298N) ---
# Pines específicos: IN1=21, IN2=19, IN3=18, IN4=5
pins = [Pin(21, Pin.OUT), Pin(19, Pin.OUT), Pin(18, Pin.OUT), Pin(5, Pin.OUT)]

# Secuencia de pasos (Full Step)
secuencia = [
    (1, 0, 1, 0),
    (0, 1, 1, 0),
    (0, 1, 0, 1),
    (1, 0, 0, 1)
]

# LDRs
ldr1 = ADC(Pin(33)); ldr2 = ADC(Pin(32)); ldr3 = ADC(Pin(35))
ldr1.atten(ADC.ATTN_11DB); ldr2.atten(ADC.ATTN_11DB); ldr3.atten(ADC.ATTN_11DB)

# Hall (Pin 22=Medio, Pin 23=Abierto)
hall_0 = Pin(14, Pin.IN) # Abajo
hall_1 = Pin(22, Pin.IN) # Medio
hall_2 = Pin(23, Pin.IN) # Arriba
sensores = {0: hall_0, 1: hall_1, 2: hall_2}

# --- 2. VARIABLES DE AJUSTE (MODIFICABLES) ---
posicion_actual = 0
modo = "0"
estado_anterior = ""
contador_confirmacion = 0
objetivo_pendiente = -1

# AJUSTE DE RECORRIDO EXTRA (Pasos adicionales tras detectar imán)
PASOS_EXTRA_ABIERTO = 1000  # Ajuste para los cm finales arriba
PASOS_EXTRA_CERRADO = 400   # Ajuste para que apoye bien abajo
TIEMPO_FILTRO = 5           # Segundos de confirmación para luz
delay_paso = 5 / 1000       # Velocidad (5ms)

# --- 3. BLUETOOTH ---
ble = bluetooth.BLE()
sp = BLESimplePeripheral(ble, "Cortina_ESP32")

def procesar_comando(datos):
    global modo, contador_confirmacion
    recibido = datos.decode().strip().replace('\x00', '')
    if recibido in ["1", "2"]:
        modo = recibido
        contador_confirmacion = 0
        print(f"\n[BT] Modo Auto {modo} Activo")
    elif recibido in ["A", "M", "C"]:
        modo = "M"
        print(f"\n[BT] Manual - Comando: {recibido}")
        if recibido == "A": viajar_a(2)
        elif recibido == "M": viajar_a(1)
        elif recibido == "C": viajar_a(0)

sp.on_write(procesar_comando)

# --- 4. FUNCIONES DEL MOTOR PASO A PASO ---
def motor_off():
    """Apaga bobinas para evitar calor"""
    for pin in pins: pin.value(0)

def dar_paso_fisico(indice):
    for i in range(4):
        pins[i].value(secuencia[indice % 4][i])
    time.sleep(delay_paso)

def viajar_a(id_objetivo):
    global posicion_actual
    if id_objetivo == posicion_actual: return
    
    target = sensores[id_objetivo]
    direccion = 1 if id_objetivo > posicion_actual else -1
    paso_local = 0
    
    print(f"[MOTOR] Iniciando viaje a posición {id_objetivo}...")
    
    # 1. Movimiento hasta detectar el imán
    while target.value() == 1:
        dar_paso_fisico(paso_local)
        paso_local += direccion
    
    # 2. Recorrido extra ajustable
    if id_objetivo == 2: # ARRIBA
        print(f"[MOTOR] Imán 2 detectado. Sumando {PASOS_EXTRA_ABIERTO} pasos extra...")
        for _ in range(PASOS_EXTRA_ABIERTO):
            dar_paso_fisico(paso_local)
            paso_local += direccion
    elif id_objetivo == 0: # ABAJO
        print(f"[MOTOR] Imán 0 detectado. Sumando {PASOS_EXTRA_CERRADO} pasos extra...")
        for _ in range(PASOS_EXTRA_CERRADO):
            dar_paso_fisico(paso_local)
            paso_local += direccion
            
    motor_off()
    posicion_actual = id_objetivo
    print(f"[EXITO] Posición {id_objetivo} alcanzada.")

def calibrar_inicial():
    global posicion_actual
    print("\n[SISTEMA] Calibrando hacia abajo (Hall 0)...")
    paso_local = 0
    inicio = time.time()
    while (time.time() - inicio) < 25:
        if hall_0.value() == 0:
            # Aplicar extra al calibrar para asegurar que llegue al final
            for _ in range(PASOS_EXTRA_CERRADO):
                dar_paso_fisico(paso_local)
                paso_local -= 1
            motor_off(); posicion_actual = 0
            print("[SISTEMA] Calibración OK.\n")
            return
        dar_paso_fisico(paso_local)
        paso_local -= 1
    motor_off(); print("[ERROR] No se halló Hall 0.")

# --- 5. BUCLE PRINCIPAL CON MONITOREO ---
motor_off()
calibrar_inicial()

while True:
    if sp.is_connected():
        estado_anterior = "CONECTADO"
        if modo in ["1", "2"]:
            luz = (ldr1.read() + ldr2.read() + ldr3.read()) / 3
            
            # Lógica de decisión según luz
            if modo == "1":
                if luz < 1800: sug = 0
                elif 1800 <= luz < 3400: sug = 1
                else: sug = 2
            else: 
                if luz > 3400: sug = 0
                elif 1800 <= luz < 3400: sug = 1
                else: sug = 2

            # Filtro de confirmación y logs
            if sug != posicion_actual:
                if sug != objetivo_pendiente:
                    objetivo_pendiente = sug
                    contador_confirmacion = TIEMPO_FILTRO
                print(f"[AUTO] Luz: {int(luz)} | Cambio a Pos {sug} en {contador_confirmacion}s...")
                if contador_confirmacion <= 0:
                    viajar_a(sug)
                    objetivo_pendiente = -1
                else:
                    contador_confirmacion -= 1
            else:
                print(f"[AUTO] Luz: {int(luz)} | Pos Actual: {posicion_actual} (Estable)")
                contador_confirmacion = 0
                objetivo_pendiente = -1
    else:
        if estado_anterior != "OFF":
            print("Esperando conexión Bluetooth..."); estado_anterior = "OFF"; modo = "0"
            
    time.sleep_ms(1000)