from machine import Pin, PWM, ADC
import time

# --- CONFIGURACIÓN DE PINES ---
pinIN3 = Pin(22, Pin.OUT)
pinIN4 = Pin(23, Pin.OUT)
pwm_enb = PWM(Pin(27), freq=1000)

# Sensores LDR
ldr1 = ADC(Pin(33))
ldr2 = ADC(Pin(32))
ldr3 = ADC(Pin(35))
ldr1.atten(ADC.ATTN_11DB)
ldr2.atten(ADC.ATTN_11DB)
ldr3.atten(ADC.ATTN_11DB)

# --- VARIABLES DE CONTROL ---
estado_actual = ""
estado_anterior = ""
velocidad_motor = 160 # Ajusta según el peso de tu cortina

def mover_motor(segundos, d3, d4):
    # PAUSA DE SEGURIDAD: Evita cambios bruscos de inercia
    print("Estabilizando sistema antes de mover...")
    pinIN3.value(0)
    pinIN4.value(0)
    pwm_enb.duty(0)
    time.sleep(2) # Tiempo muerto para proteger el motor y el puente H
    
    # Iniciar movimiento
    valor_duty = int((velocidad_motor / 255) * 1023)
    pinIN3.value(d3)
    pinIN4.value(d4)
    pwm_enb.duty(valor_duty)
    
    print(f"Ejecutando movimiento por {segundos} segundos...")
    time.sleep(segundos)
    
    # Frenado suave
    pinIN3.value(0)
    pinIN4.value(0)
    pwm_enb.duty(0)
    print("Movimiento finalizado. Motor en reposo.")

print("Sistema de Cortina Inteligente con Protección de Motor Listo.")

while True:
    # 1. Lectura promedio de los 3 LDR
    lectura = (ldr1.read() + ldr2.read() + ldr3.read()) / 3
    
    # 2. Clasificación de estado
    if lectura < 1800:
        estado_actual = "CERRADA"
    elif 1800 <= lectura < 3400:
        estado_actual = "MEDIA"
    else:
        estado_actual = "ABIERTA"

    # 3. Lógica de ejecución por cambio de estado
    if estado_actual != estado_anterior:
        print(f"--- NUEVO ESTADO DETECTADO: {estado_actual} (Luz: {int(lectura)}) ---")
        
        if estado_actual == "ABIERTA":
            # Si se detecta mucha luz, abrir (5 seg)
            mover_motor(5, 1, 0)
            
        elif estado_actual == "MEDIA":
            # Si se detecta luz media, ir a posición media (3 seg)
            mover_motor(3, 1, 0)
            
        elif estado_actual == "CERRADA":
            # Si oscurece, cerrar (sentido inverso)
            mover_motor(5, 0, 1)

        estado_anterior = estado_actual
        print("Esperando nuevo cambio de luz...\n")
    
    time.sleep(0.5) # Escaneo rápido del sensor