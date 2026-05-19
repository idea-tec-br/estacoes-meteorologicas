from pathlib import Path
from datetime import datetime, timedelta
import re
import os
import time
import influxdb_client
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

load_dotenv()

file = "83899.txt"
station = "83899"


def read_text_file(directory: Path) -> str:
    content = ""
    file_path = directory / file
    if file_path.is_file():
        content += file_path.read_text(encoding="utf-8", errors="ignore")
    return content


def send_to_influxdb(lines: list[str]) -> None:
    url = os.getenv("INFLUXDB_URL", "http://localhost:8086").rstrip("/")
    token = os.getenv("INFLUXDB_TOKEN", "")
    org = os.getenv("INFLUXDB_ORG", "")
    bucket = os.getenv("INFLUXDB_BUCKET", "")

    write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
    bucket = "weather-stations"
    write_api = write_client.write_api(write_options=SYNCHRONOUS)

    for line in lines:
        parts = line.split()
        measurement = parts[0]
        fields_str = parts[1]
        timestamp = int(parts[2]) * 1000000000  # ✅ mantém como inteiro, não converte para datetime

        point = (
            Point(measurement)
            .field("lat", -27.67)
            .field("long", -48.55)
            .field("alt", 5.0)
            .time(timestamp)  # ✅ inteiro + precisão em segundos
        )

        # ✅ adiciona todos os fields, não só o último
        for field in fields_str.split(','):
            key, value = field.split('=')
            try:
                point = point.field(key, float(value))  # ✅ grava como número, não string
            except ValueError:
                point = point.field(key, value)

        print(point)
        write_api.write(bucket=bucket, org="feira", record=point)
        #time.sleep(0.1)

if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    content = read_text_file(base)

    begin = station
    header = "   PRES"
    supress = ["-----", "    hPa"]
    end = "Station"
    read_numbers = False

    year = 0
    month = 0
    day = 0
    hour = 0
    minute = 0
    second = 0
    microsecond = 0
    delta = 344
    date = datetime.now()

    LAT = "-27.67"
    LONG = "-48.55"
    ALT = "5.0"
    keys = []
    values = []
    influx_lines = []

    for line in content.splitlines():
        if line.startswith(station):
            line = re.split(r"[\ ,Z]", line)

            year = int(line[9])
            month = datetime.strptime(line[8], "%b").month
            day = int(line[7])
            hour = int(line[5])
            date = datetime(year, month, day, hour, minute, second, microsecond)
        elif line.startswith(tuple(supress)):
            continue
        elif line.startswith(header):
            read_numbers = True
            keys = line.split()
        elif line.startswith(end):
            read_numbers = False
        else:
            if read_numbers:
                values = line.split()
                date = date + timedelta(seconds=delta)

                for key, value in zip(keys, values):
                    line = (
                        f"{station} "
                        f"{key}={value} "
                        f"{int(date.timestamp())}"
                    )
                    influx_lines.append(line)

    send_to_influxdb(influx_lines)

