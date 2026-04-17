from machine import UART, Pin
import utime


class GPS:
    def __init__(self, uart_id, baudrate, tx_pin, rx_pin):
        self.uart = UART(uart_id, baudrate=baudrate, tx=Pin(tx_pin), rx=Pin(rx_pin))

    def convert_to_decimal(self, raw_value, direction):
        if raw_value == "" or direction == "":
            return None
        try:
            raw_float = float(raw_value)
        except:
            return None
        degrees = int(raw_float / 100)
        minutes = raw_float - degrees * 100
        decimal = degrees + minutes / 60.0
        if direction in ["S", "W"]:
            decimal = -decimal
        return decimal

    def read(self):
        if self.uart.any():
            line = self.uart.readline()
            if not line:
                return None
            try:
                sentence = line.decode("ascii").strip()
            except:
                return None

            if sentence.startswith("$GPGGA"):
                parts = sentence.split(",")
                if len(parts) >= 15 and parts[6] != "0":  # fix válido
                    lat = self.convert_to_decimal(parts[2], parts[3])
                    lon = self.convert_to_decimal(parts[4], parts[5])
                    altitude = parts[9]
                    satellites = parts[7]
                    return {
                        "latitude": lat,
                        "longitude": lon,
                        "altitude": altitude,
                        "satellites": satellites,
                    }
        return None
