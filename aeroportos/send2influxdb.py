from pathlib import Path
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv
import requests

load_dotenv()


def read_text_file(file: str) -> str:
    base = Path(__file__).resolve().parent
    file_path = base / file

    content = ""
    if file_path.is_file():
        content += file_path.read_text(encoding="utf-8", errors="ignore")
    return content


def filter_lines(station: str, lines: list[str]) -> list[str]:
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
    date = datetime.now()
    delta = 344

    latitude = "-27.67"
    longitude = "-48.55"
    altitude = "5.0"

    keys = []
    values = []
    influx_line = ""
    influx_lines = []

    for line in lines:
        if line.startswith(begin):
            line = re.split(r"[\ ,Z]", line)

            station = line[0]
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
                influx_line = f"{station},iata=FLN,icao=SBFL latitude={latitude},longitude={longitude},altitude={altitude}"

                values = line.split()
                date = date + timedelta(seconds=delta)
                for key, value in zip(keys, values):
                    influx_line += f",{key.lower()}={value}"

                influx_line += f" {int(date.timestamp()) * 1000000000}"
                influx_lines.append(influx_line)

    return influx_lines


def send_to_influxdb(lines: list[str]) -> None:
    url = os.getenv("INFLUXDB_URL", "http://localhost:8086").rstrip("/")
    token = os.getenv("INFLUXDB_TOKEN", "")
    org = os.getenv("INFLUXDB_ORG", "feira")
    bucket = os.getenv("INFLUXDB_BUCKET", "weather-stations")

    endpoint = f"{url}/api/v2/write"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "text/plain; charset=utf-8",
    }
    params = {
        "org": org,
        "bucket": bucket,
        "precision": "ns",
    }
    body = "\n".join(lines)

    response = requests.post(endpoint, headers=headers, params=params, data=body.encode("utf-8"))
    if not response.ok:
        print(response.text)
        response.raise_for_status()


if __name__ == "__main__":
    station = "83899"

    file = station + ".txt"
    file_content = read_text_file(file)
    influx_lines = filter_lines(station, file_content.splitlines())
    send_to_influxdb(influx_lines)
