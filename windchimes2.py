#!/usr/bin/env python3
"""
windchimes2.py — improved wind chime simulator

Improvements over windchimes.py:
  - Poisson process inter-strike timing (exponential distribution)
  - Rayleigh velocity distribution (physically correct dynamics)
  - Per-note clapper cooldown (prevents unnatural rapid same-note repeats)

Based on techniques from:
  Lukkari & Välimäki, "Modal synthesis of wind chime sounds with
  stochastic event triggering", NORSIG 2004.
"""
import fluidsynth
import subprocess
import threading
import random
import time
import signal
import urllib.request
import json
import argparse
import numpy as np

#SF2    = "/home/pisynth/soundfonts/alex_gm.sf2"
SF2    = "/home/pisynth/soundfonts/tubular_bells.sf2"
BANK   = 0
#PRESET = 11   # Vibraphone
PRESET = 0
CH     = 0
GAIN   = 1.0

WEATHER_URL_TEMPLATE = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=wind_speed_10m&wind_speed_unit=mph"
)
WEATHER_INTERVAL = 300

SCALES = {
    'emajor': ([40,42,44,47,49, 52,54,56,59,61, 64], "E major pentatonic"),
    'cmajor': ([36,38,40,43,45, 48,50,52,55,57, 60], "C major pentatonic"),
    'gmajor': ([43,45,47,50,52, 55,57,59,62,64, 67], "G major pentatonic"),
    'eminor': ([40,42,43,45,47, 52,54,55,57,59, 64], "E minor pentatonic"),
    'aminor': ([45,47,48,52,55, 57,59,60,64,67, 69], "A minor pentatonic"),
}

parser = argparse.ArgumentParser(
    description="Wind chime simulator v2 — Poisson timing, Rayleigh velocity, clapper model"
)
parser.add_argument(
    '--scale',
    choices=SCALES.keys(),
    default='emajor',
    metavar='SCALE',
    help='Scale to use. Choices: emajor (default), cmajor, gmajor, eminor, aminor'
)
parser.add_argument(
    '--lat',
    type=float,
    default=27.8006,
    help='Latitude in decimal degrees (default: 27.8006 — Corpus Christi TX)'
)
parser.add_argument(
    '--lon',
    type=float,
    default=-97.3964,
    help='Longitude in decimal degrees (default: -97.3964 — Corpus Christi TX)'
)
args = parser.parse_args()

notes, scale_name = SCALES[args.scale]
WEATHER_URL = WEATHER_URL_TEMPLATE.format(lat=args.lat, lon=args.lon)

# Weighted note pool — higher notes struck more often (lighter chimes)
WEIGHTS   = [1,1,1, 2,2, 3,3,3, 4,4, 3]
NOTE_POOL = [n for n, w in zip(notes, WEIGHTS) for _ in range(w)]

# Clapper cooldown — minimum seconds before a note can re-strike
# Simulates the physical pendulum period of each chime tube
# Longer (lower-pitched) tubes swing slower — longer cooldown
CLAPPER_COOLDOWN = {n: random.uniform(0.8, 1.6) for n in notes}
last_strike_time = {n: 0.0 for n in notes}
clapper_lock = threading.Lock()

def detect_audio():
    out = subprocess.check_output(['aplay', '-l']).decode()
    for line in out.splitlines():
        if 'USB' in line and line.startswith('card'):
            return 'plughw:' + line.split()[1].rstrip(':') + ',0'
    raise RuntimeError("USB audio not found")

fs = fluidsynth.Synth(gain=GAIN)
fs.start(driver='alsa', device=detect_audio())
sfid = fs.sfload(SF2)
fs.program_select(CH, sfid, BANK, PRESET)

running    = True
wind_speed = 0.0

def fetch_wind():
    global wind_speed
    while running:
        try:
            data = json.loads(urllib.request.urlopen(WEATHER_URL, timeout=5).read())
            wind_speed = data['current']['wind_speed_10m']
            print(f"  Wind: {wind_speed:.1f} mph")
        except Exception as e:
            print(f"  Weather fetch failed: {e}")
        for _ in range(WEATHER_INTERVAL * 10):
            if not running:
                break
            time.sleep(0.1)

threading.Thread(target=fetch_wind, daemon=True).start()
time.sleep(1.5)

print(f"Wind chimes v2 ready — {scale_name} — {wind_speed:.1f} mph at ({args.lat}, {args.lon})")
print("Ctrl+C to stop\n")

def poisson_rate(w):
    """Strike rate (events/sec) as a function of wind speed (mph)."""
    if w < 3:   return 0.04
    if w < 8:   return 0.12
    if w < 15:  return 0.35
    if w < 22:  return 0.80
    if w < 30:  return 1.60
    return 3.00

def rayleigh_vel(w):
    """
    Sample strike velocity from Rayleigh distribution.
    σ scales with wind speed — higher wind → harder strikes.
    """
    sigma = max(8, min(55, w * 1.8))
    v = np.random.rayleigh(sigma)
    return int(max(20, min(110, v)))

def try_strike(note):
    """
    Attempt to strike a note. Respects clapper cooldown —
    returns False if the tube hasn't had time to swing back.
    """
    now = time.time()
    with clapper_lock:
        if now - last_strike_time[note] < CLAPPER_COOLDOWN[note]:
            return False
        last_strike_time[note] = now
    v = rayleigh_vel(wind_speed)
    fs.noteon(CH, note, v)
    threading.Timer(random.uniform(0.06, 0.18), fs.noteoff, args=(CH, note)).start()
    return True

def interruptible_sleep(seconds, step=0.05):
    end = time.time() + seconds
    while running and time.time() < end:
        time.sleep(step)

def signal_handler(sig, frame):
    global running
    print("\nStopping...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

# Main loop — pure Poisson process
# Inter-strike interval drawn from exponential distribution
# If chosen note is on cooldown, pick a different one (up to N attempts)
while running:
    rate = poisson_rate(wind_speed)
    interval = random.expovariate(rate)
    interruptible_sleep(interval)
    if not running:
        break
    # Try notes until one clears cooldown (max 5 attempts)
    pool = NOTE_POOL[:]
    random.shuffle(pool)
    for note in pool[:5]:
        if try_strike(note):
            break

time.sleep(0.5)
fs.all_notes_off(CH)
time.sleep(0.3)
fs.delete()
print("Done.")
