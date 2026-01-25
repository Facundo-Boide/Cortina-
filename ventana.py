import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
from machine import ADC, Pin, PWM
import time

pinIN3 = Pin(25, Pin.OUT)
pinIN4 = Pin(26, Pin.OUT)
pwm_enb = PWM(Pin(27), freq=1000, duty=0)
led = Pin(2, Pin.OUT) 

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

posicion_actual = 0
modo = "0"

ble = bluetooth.BLE()                                              #bluetooth
sp = BLESimplePeripheral(ble, "Cortina_ESP32")

def detener_motor():
    pwm_enb.duty(0)
    pinIN3.value(0)
    pinIN4.value(0)

def mover_motor(sentido):
    if sentido == "ABRIR":
        pinIN3.value(1); pinIN4.value(0)
    else: # CERRAR
        pinIN3.value(0); pinIN4.value(1)
    pwm_enb.duty(int((100 / 255) * 1023))
# ARRANQUE SUAVE (Soft Start) para evitar Brownout
    velocidad_final = int((100 / 255) * 1023) # Ajusté a 190 por ser motor más chico
    for v in range(0, velocidad_final, 80):
        pwm_enb.duty(v)
        time.sleep_ms(30)
    pwm_enb.duty(velocidad_final)

def calibrar_auto_ubicacion():
    global posicion_actual
    print("\n[SISTEMA] Iniciando Auto-Ubicación...")
    encontrado = False
    
    # 1. Intentar buscar hacia ABAJO (CERRAR) durante 5 segundos
    print("Buscando sensor hacia abajo (5s)...")
    mover_motor("CERRAR")
    inicio = time.time()
    
    while (time.time() - inicio) < 10:
        for i in range(3):
            if sensores[i].value() == 0:
                posicion_actual = i
                encontrado = True
                break
        if encontrado: break
        time.sleep_ms(10)
    
    # 2. SI NO SE ENCONTRÓ, buscar hacia ARRIBA (ABRIR)
    if not encontrado:
        detener_motor()
        time.sleep_ms(500)
        print("No detectado abajo. Cambiando sentido hacia arriba...")
        mover_motor("ABRIR")
        inicio = time.time()
        
        while not encontrado:
            for i in range(3):
                if sensores[i].value() == 0:
                    posicion_actual = i
                    encontrado = True
                    break
            if encontrado: break
            
            # Timeout de seguridad de 15 segundos hacia arriba
            if (time.time() - inicio) > 15: 
                print("[ERROR] No se detectó ningún sensor en 15s.")
                break
            time.sleep_ms(10)

    detener_motor()
    if encontrado:
        print(f"[EXITO] Sensor {posicion_actual} detectado. Sistema listo.\n")
        time.sleep(2)      

def mover_a_posicion(objetivo):
    global posicion_actual
    if objetivo == posicion_actual: return

    sentido = "ABRIR" if objetivo > posicion_actual else "CERRAR"
    print(f"Moviendo: de {posicion_actual} hacia sensor {objetivo}...")
    mover_motor(sentido)

    # El motor se detiene cuando el sensor específico (0, 1 o 2) detecta el imán
    while sensores[objetivo].value() == 1:
        
        time.sleep_ms(10)

    detener_motor()
    posicion_actual = objetivo
    print(f"¡Llegamos al sensor {objetivo}! Pausa de 4s...")
    time.sleep(4) # Bloqueo post-movimiento     

def procesar_comando(datos):
    global modo
    # Decodificamos y limpiamos cualquier carácter no deseado
    recibido = datos.decode().strip().replace('\x00', '')
    
    if recibido == "" or recibido == "\x00":
        return # Ignorar mensajes vacíos
        
    print("\n" + "="*30)
    print(f" DATO REAL RECIBIDO: '{recibido}' ")
    print("="*30 + "\n")
    
    modo = recibido
sp.on_write(procesar_comando)


print("ESP32 Listo. Nombre: Cortina_ESP32")
print("Esperando conexión desde MIT App Inventor...")


calibrar_auto_ubicacion()


estado_anterior = ""

while (True):										#chequeo 
    
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
            
                    estado_actual = "cortina cerrado"; objetivo_sugerido = 0
            
                elif ldr_g > 1800 and ldr_g < 3400:  
            
                    estado_actual = "media cortina"; objetivo_sugerido = 1
            
                elif ldr_g > 3400 and ldr_g <= 4095:
            
                    estado_actual = "cortina abierta"; objetivo_sugerido = 2
                                                                                    #modo auto 2
            if modo == "2":
                if ldr_g > 3400 and ldr_g <= 4095:														#deliveracion 
               
                    estado_actual = "cortina cerrado"; objetivo_sugerido = 0
            
                elif ldr_g > 1800 and ldr_g < 3400:  
            
                    estado_actual = "media cortina"; objetivo_sugerido = 1
                   
                elif ldr_g < 1800:
            
                    estado_actual = "cortina abierta"; objetivo_sugerido = 2
            
            if estado_actual != estado_anterior:
                print (f"Estado: {estado_actual}")
                estado_anterior = estado_actual
                time.sleep(1)
    
    else:
        if estado_anterior != "DESCONECTADO":
            print("Esperando conexión Bluetooth...")
            estado_anterior = "DESCONECTADO"
            modo = "0"            
        
        
    
