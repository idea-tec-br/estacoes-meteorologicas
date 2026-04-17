from machine import Pin
from time import sleep

led = Pin(2, Pin.OUT)

print("esperando calibração")
led.value(0)

sleep(1)

print("calibração geral concluida")
led.value(1)
