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

sensor_hall = Pin(14, Pin.IN, Pin.PULL_UP)


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
    pwm_enb.duty(int((180 / 255) * 1023))


def calibrar_posicion():                           #calibracion de home
    global posicion_actual, estado_anterior
    print("\n[SISTEMA] Iniciando reconocimiento de imanes...")
    mover_motor("CERRAR")
    
    imanes_vistos = 0
    ultimo_hall = 1
    tiempo_inicio = time.time()
    
    # Busca 3 imanes o frena tras 12 segundos por seguridad
    while imanes_vistos < 3 and (time.time() - tiempo_inicio) < 12:
        lectura = sensor_hall.value()
        
        # Detectar flanco de bajada (de 1 a 0)
        if lectura == 0 and ultimo_hall == 1:
            imanes_vistos += 1
            print(f"-> Imán {imanes_vistos} detectado.")
            time.sleep_ms(150) # Anti-rebote
        
        ultimo_hall = lectura
    
    detener_motor()
    posicion_actual = 0
    estado_anterior = "cortina cerrada"
    print("[SISTEMA] Home alcanzado. Posición 0 establecida.\n")

def mover_a_posicion(objetivo):
    global posicion_actual
    if objetivo == posicion_actual: return

    sentido = "ABRIR" if objetivo > posicion_actual else "CERRAR"
    print(f"Moviendo: de {posicion_actual} hacia imán {objetivo}...")
    mover_motor(sentido)

    while posicion_actual != objetivo:
        # Lógica negativa: 0 significa imán frente al sensor
        if sensor_hall.value() == 0:
            if objetivo > posicion_actual:
                posicion_actual += 1
            else:
                posicion_actual -= 1
            
            print(f"Pasando por imán: {posicion_actual}")
            
            if posicion_actual == objetivo:
                frenar_motor()
                print("¡Detenido en el punto puntual!")
                break
            else:
                # Esperar a salir del imán actual para no contarlo doble
                while sensor_hall.value() == 0:
                    pass
                time.sleep_ms(50)
                

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


calibrar_posicion()



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
            
            if sensor_hall.value() == 0:
                led.value(0)
            else:
        # Si el valor es 1, NO hay imán
                led.value(1)
    
    else:
        if estado_anterior != "DESCONECTADO":
            print("Esperando conexión Bluetooth...")
            estado_anterior = "DESCONECTADO"
            modo = "0"            
        
        
    
