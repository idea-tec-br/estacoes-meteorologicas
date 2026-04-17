from machine import Pin, I2C, ADC, SPI
import dht, onewire, ds18x20, network, utime, os
from umqtt.simple import MQTTClient
from libs import bmp280, mq4, mq7, ds3231, dotenv, neo6m, sdcard
from libs.gps_fix_manager import GPSFixManager
from time import sleep, time, mktime
from sys import exit

i2c0 = I2C(0, scl=Pin(22), sda=Pin(21), freq=10000)
i2c1 = I2C(1, sda=Pin(4), scl=Pin(5))
spi = SPI(
    1, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19)
)
cs = Pin(27, Pin.OUT)

topico_data = "em/" + str(dotenv.MQTT_ID)
topico_debug = "em/debugV0"
versao_em = "0"

gps = neo6m.GPS(uart_id=1, baudrate=9600, tx_pin=12, rx_pin=13)
ds18x20 = ds18x20.DS18X20(onewire.OneWire(Pin(15)))
roms = ds18x20.scan()
dht11 = dht.DHT11(Pin(14))
bmp280 = bmp280.BMP280(i2c0)
ds3231 = ds3231.DS3231(i2c=i2c1)
rain = ADC(34)
gps_manager = GPSFixManager(limite_metros=500, tentativas=3)
sd = sdcard.SDCard(spi, cs)

vfs = os.VfsFat(sd)
os.mount(vfs, "/sd")
print(os.listdir("/sd"))

dados = {}

mq4 = mq4.MQ4(pinData=39)
mq4.calibrate()
mq7 = mq7.MQ7(pinData=36)
mq7.calibrate()

print("Ro MQ4:", mq4._ro)
print("Ro MQ7:", mq7._ro)


def timestamp():
    x = ds3231.datetime()
    diference = 946684800
    timestamp = mktime((x[0], x[1], x[2], x[4], x[5], x[6], 0, 0)) + diference
    ts_ns = timestamp * 10**9
    return ts_ns


def espera_gps(timeout_ms=60000):
    print("Esperando fix GPS...")
    inicio = utime.ticks_ms()
    while utime.ticks_diff(utime.ticks_ms(), inicio) < timeout_ms:
        data = gps.read()
        if data:
            return data
        utime.sleep_ms(200)

    print("Sem fix GPS após timeout.")
    return {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}


def bmp280_ler():
    try:
        temp = bmp280.get_temperature()
        press = bmp280.get_pressure() / 100
        return temp, press
    except Exception as e:
        try:
            msg_erro = "erro leitura bmp280: " + str(e)
            client.publish(topico_debug, msg_erro)
        except:
            print("erro mqtt debug")
        print(msg_erro)


def ds18b20_ler():
    try:
        ds18x20.convert_temp()
        sleep(1)
        temp = ds18x20.read_temp(roms[0])
        return temp
    except Exception as e:
        msg_erro = (
            "Erro na leitura do DS18B20: " + str(e) + " no momento: " + str(ts_ns)
        )
        try:
            client.publish(topico_debug, msg_erro)
        except:
            print("erro mqtt debug ds18b20")
        print(msg_erro)
        return 0.0


def sensores_gas():
    try:
        mq4_v = mq4.readMethane()
        mq7_v = mq7.readCarbonMonoxide()
        return mq4_v, mq7_v
    except Exception as e:
        ts_ns = timestamp()
        msg_erro = "Erro na leitura dos gases: " + str(e) + " no momento: " + str(ts_ns)
        print(msg_erro)
        try:
            client.publish(topico_debug, msg_erro)
        except:
            print("erro mqtt debug gases")
        return 0.0, 0.0


def formatar(ts_ns):
    data = ""
    data += topico_data + ","
    data += "v=" + versao_em + ","
    data += "lat=" + str(gps_data["latitude"]) + ","
    data += "lng=" + str(gps_data["longitude"]) + ","
    data += "alt=" + str(gps_data["altitude"])
    data += " "
    data += "dht11_temp=" + str(dados["temp.dht11"]) + ","
    data += "dht11_umid=" + str(dados["umid.dht11"]) + ","
    data += "bmp280_temp=" + str(dados["temp.bmp280"]) + ","
    data += "bmp280_press=" + str(dados["press.bmp280"]) + ","
    data += "ds18b20_temp=" + str(dados["temp.ds18b20"]) + ","
    data += "mq7_co=" + str(dados["co.mq7"]) + ","
    data += "mq4_ch4=" + str(dados["ch4.mq4"]) + ","
    data += "sensor_chuva=" + str(dados["valor_chuva"])
    data += " " + str(ts_ns)
    return data


gps_data = gps_manager.carregar_fix()
fix_novo = gps_manager.pegar_fix_consistente(espera_gps)

if (
    fix_novo
    and gps_manager.distancia_metros(
        float(gps_data["latitude"]),
        float(gps_data["longitude"]),
        float(fix_novo["latitude"]),
        float(fix_novo["longitude"]),
    )
    > gps_manager.limite_metros
):
    gps_manager.atualizar_fix(fix_novo)
    gps_data = fix_novo
elif not gps_data:
    gps_data = fix_novo or {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}

print("Fix:", gps_data)


conecta_wifi()
client = MQTTClient(dotenv.MQTT_ID, dotenv.MQTT_BROKER, port=dotenv.MQTT_PORT)
client.connect()

led.value(0)
while False:
    inicio = time()

    print("lendo dht11")
    dht11.measure()
    dados["temp.dht11"] = dht11.temperature()
    dados["umid.dht11"] = dht11.humidity()

    print("lendo bmp280")
    dados["temp.bmp280"], dados["press.bmp280"] = bmp280_ler()

    print("lendo ds18b20")
    dados["temp.ds18b20"] = ds18b20_ler()

    print("lendo gases")
    dados["ch4.mq4"], dados["co.mq7"] = sensores_gas()

    print("lendo chuva")
    dados["valor_chuva"] = rain.read()

    tempo_execucao = time() - inicio
    ts_ns = timestamp()

    data = formatar(ts_ns)
    if client:
        try:
            print("publicando no MQTT")
            client.publish(topico_data, data, qos=1)
            client.check_msg()
            print("dados publicados com sucesso")
        except Exception as e:
            print("erro MQTT ao publicar:", e)
            try:
                conecta_wifi()
                client.connect()
            except Exception as e:
                print("erro na reconexao wifi e mqtt")
    else:
        print("cliente MQTT não está disponível")

    try:
        with open("/sd/data.txt", "a") as f:
            f.write(data + "\n")
        print("dados gravados no sd com sucesso")
    except Exception as e:
        print("Erro ao gravar no SD:", e)

    print(data)

    if tempo_execucao < 60:
        sleep(60 - tempo_execucao)
    else:
        print("Tempo de execução excedido: " + str(tempo_execucao))


def leds():
    led = Pin(2, Pin.OUT)
    led.value(1)


def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(dotenv.WIFI_SSID, dotenv.WIFI_PASS)

        while not wlan.isconnected():
            sleep(0.5)
            print("Connecting...")
        print("Wi-Fi connected:", wlan.ifconfig())

    return wlan


def mqtt_connect(broker, port=1883, id="em"):
    try:
        client = MQTTClient(id, broker, port=port)
        client.connect()
        print("MQTT connected")

    except Exception as e:
        print("MQTT connection error:", e)
        client = None

    return client


if __name__ == "__main__":
    dotenv.load_env()
    try:
        wifi_ssid = os.getenv("WIFI_SSID", "em")
        wifi_pass = os.getenv("WIFI_PASS", "password")
        mqtt_broker = os.getenv("MQTT_BROKER", "mqtt.idea.tec.br")
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        mqtt_id = os.getenv("MQTT_ID", "em_v0")
    except Exception as e:
        print("Erro ao carregar configurações do .env:", e)
        exit(1)

    leds()
    wifi_connect()
    client = mqtt_connect(dotenv.MQTT_BROKER, int(dotenv.MQTT_PORT), dotenv.MQTT_ID)
