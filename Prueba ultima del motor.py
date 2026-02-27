from machine import Pin

import utime



# Configuración de pines

step_pin = Pin(25, Pin.OUT)

dir_pin = Pin(27, Pin.OUT)

enable_pin = Pin(12, Pin.OUT)



# El driver A4988 se ACTIVA con LOW y se DESACTIVA con HIGH

# Lo mantenemos desactivado al inicio para evitar ruidos y calor

enable_pin.value(1) 



def mover_motor(pasos, direccion, velocidad_us=1000):

    """

    pasos: cantidad de pasos a dar (200 es una vuelta)

    direccion: 1 para un sentido, 0 para el otro

    velocidad_us: microsegundos entre pulsos (más chico = más rápido)

    """

    # 1. Establecer dirección

    dir_pin.value(direccion)

    

    # 2. Habilitar el motor (aquí empezará a hacer el ruido normal de energía)

    enable_pin.value(0)

    utime.sleep_ms(10) # Pausa para que el driver se estabilice

    

    print(f"Moviendo {pasos} pasos...")

    

    # 3. Generar los pulsos

    for i in range(pasos):

        step_pin.value(1)

        utime.sleep_us(velocidad_us)

        step_pin.value(0)

        utime.sleep_us(velocidad_us)

        

    # 4. Deshabilitar el motor (adiós al ruido y al consumo de corriente)

    enable_pin.value(1)

    print("Movimiento finalizado. Motor en reposo.")



# --- PRUEBA DE FUNCIONAMIENTO ---

try:

    while True:

        # Abrir cortina (ejemplo: 1000 pasos)

        mover_motor(1000, 1, 800) 

        utime.sleep(2)

        

        # Cerrar cortina

        mover_motor(1000, 0, 800)

        utime.sleep(2)

        

except KeyboardInterrupt:

    # Asegurarse de apagar el motor si detenemos el script

    enable_pin.value(1)

    print("Programa detenido.")