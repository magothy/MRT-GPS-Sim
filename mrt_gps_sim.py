#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
import math
import socket
import time
from datetime import datetime, timezone
from typing import final, Tuple


def nmea_checksum(sentence: str) -> str:
    checksum = 0
    for c in sentence:
        checksum ^= ord(c)
    return f"{checksum:02X}"


def dms(value: float) -> Tuple[int, int, float]:
    value_abs = abs(value)
    deg = math.floor(value_abs)
    min = (value_abs - deg) * 60
    sec = (min - math.floor(min)) * 60
    return deg, int(min), sec


@final
class Args(argparse.Namespace):
    lat_deg = 0.0
    lon_deg = 0.0
    heading_deg = 0.0
    host = "127.0.0.1"
    port = 10110


@dataclass
class Rmc:
    time: datetime
    lat_deg: float
    lon_deg: float
    status: str  # A = data valid, V = data invalid
    speed_knots: float
    course_deg: float

    def __str__(self) -> str:
        # https://www.sparkfun.com/datasheets/GPS/NMEA%20Reference%20Manual1.pdf
        lat_deg, lat_min, lat_sec = dms(self.lat_deg)
        lat_min_dec = lat_min + lat_sec / 60
        lat_dir = "N" if self.lat_deg >= 0 else "S"

        lon_deg, lon_min, lon_sec = dms(self.lon_deg)
        lon_min_dec = lon_min + lon_sec / 60
        lon_dir = "E" if self.lon_deg >= 0 else "W"

        inner = f"GPRMC,{self.time:%H%M%S.%f},{self.status},{lat_deg:02}{lat_min_dec:07.4f},{lat_dir},{lon_deg:03}{lon_min_dec:07.4f},{lon_dir},{self.speed_knots:.2f},{self.course_deg:.2f},{self.time:%d%m%y},"
        checksum = nmea_checksum(inner)

        return f"${inner}*{checksum}\r\n"


def main(args: Args):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    rmc = Rmc(
        time=datetime.now(timezone.utc),
        lat_deg=args.lat_deg,
        lon_deg=args.lon_deg,
        status="A",
        speed_knots=0.1,  # set non zero, otherwise OpenCPN will ignore the course
        course_deg=args.heading_deg,
    )

    while True:
        rmc.time = datetime.now(timezone.utc)
        time.sleep(1)
        rmc_str = str(rmc)
        _ = sock.sendto(rmc_str.encode(), (args.host, args.port))
        print(f"Sent {rmc_str.strip()} to {args.host}:{args.port}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    _ = parser.add_argument("lat_deg", help="Latitude in degrees", type=float)
    _ = parser.add_argument("lon_deg", help="Longitude in degrees", type=float)
    _ = parser.add_argument(
        "--heading-deg",
        help="Heading in degrees",
        type=float,
        metavar="DEG",
        default=0.0,
    )
    _ = parser.add_argument(
        "--host", help="Host to send NMEA sentences to", default="127.0.0.1"
    )
    _ = parser.add_argument(
        "--port", help="Port to send NMEA sentences to", type=int, default=10110
    )
    main(parser.parse_args(namespace=Args()))
