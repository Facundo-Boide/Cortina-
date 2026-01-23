import machine
from machine import Pin, PWM
import time

# Usamos pines que no interfieren con el sistema
pinIN3 = Pin(25, Pin.OUT)
pinIN4 = Pin(26, Pin.OUT)
# Configuramos PWM en el pin 27
# Frecuencia de 1000Hz es ideal para evitar pitidos
pwm_enb = PWM(Pin(27), freq=1000, duty=0)

def motor_test(velocidad, d3, d4):
    # En ESP32 el duty suele ser de 0 a 1023
    # Mapeamos el '60' de Arduino: (60/255) * 1023 = 240
    valor_duty = int((velocidad / 255) * 1023)
    
    pinIN3.value(d3)
    pinIN4.value(d4)
    pwm_enb.duty(valor_duty)
    print(f"Motor: {d3},{d4} | Velocidad: {valor_duty}")

while True:
    print("Girando sentido B...")
    motor_test(100, 0, 1)

