import time
from System.Media import SoundPlayer

SOUND_HIGH = r".\Sounds\esc_high.wav"
SOUND_CRIT = r".\Sounds\esc_critical.wav"
HIGH_TEMP_THRESHOLD = 35.0
CRITICAL_TEMP_THRESHOLD = 40.0
HYSTERESIS = 3.0
PRINT_INTERVAL = 5.0
ESC_COUNT = 8

def _play_sound(file_path=None, tone=None, duration_ms=800):
    """Play the given WAV file, falling back to a console beep."""
    try:
        if file_path:
            player = SoundPlayer(file_path)
            player.Play()
            return
    except Exception as e:
        print("Audio playback error '{}': {}".format(file_path, e))
    try:
        from System import Console
        freq = tone if tone else 1200
        Console.Beep(freq, duration_ms)
    except Exception as e:
        print("Unable to play system beep: {}".format(e))

def read_esc_temp(idx):
    """Return the ESC temperature for the given index (1-based) or None if unavailable."""
    name = "esc{}_temp".format(idx)
    candidates = []

    try:
        candidates.append(getattr(cs, name))
    except Exception:
        pass

    try:
        esc_list = getattr(MAV.cs, "esc", None)
        if esc_list is not None and len(esc_list) >= idx:
            candidates.append(esc_list[idx - 1].temp)
    except Exception:
        pass

    for value in candidates:
        if value is None:
            continue
        try:
            f = float(value)
        except Exception:
            continue
        if -50.0 <= f <= 300.0:
            return f
    return None

def fmt_temp(t):
    if t is None:
        return "--"
    try:
        return "{:.1f}".format(float(t))
    except Exception:
        return str(t)

print("ESC temperature monitor started...")
high_alarm_active = [False] * ESC_COUNT
crit_alarm_active = [False] * ESC_COUNT

last_print = 0.0

while True:
    now = time.time()

    temps = [read_esc_temp(i) for i in range(1, ESC_COUNT + 1)]

    for i, t in enumerate(temps, start=1):
        if t is None:
            continue

        if crit_alarm_active[i - 1] and t <= (CRITICAL_TEMP_THRESHOLD - HYSTERESIS):
            crit_alarm_active[i - 1] = False
            print("ESC{}: temperature dropped below critical threshold ({} C)".format(i, fmt_temp(t)))

        if high_alarm_active[i - 1] and t <= (HIGH_TEMP_THRESHOLD - HYSTERESIS):
            high_alarm_active[i - 1] = False
            print("ESC{}: temperature dropped below high threshold ({} C)".format(i, fmt_temp(t)))

        if (not crit_alarm_active[i - 1]) and t >= CRITICAL_TEMP_THRESHOLD:
            crit_alarm_active[i - 1] = True
            high_alarm_active[i - 1] = True
            print("ESC{} CRITICAL: {} C >= {} C - critical sound".format(i, fmt_temp(t), CRITICAL_TEMP_THRESHOLD))
            _play_sound(SOUND_CRIT, tone=1600, duration_ms=1000)
        elif (not high_alarm_active[i - 1]) and t >= HIGH_TEMP_THRESHOLD:
            high_alarm_active[i - 1] = True
            print("ESC{} HIGH: {} C >= {} C - high sound".format(i, fmt_temp(t), HIGH_TEMP_THRESHOLD))
            _play_sound(SOUND_HIGH, tone=1100, duration_ms=700)

    if now - last_print >= PRINT_INTERVAL:
        ts = time.strftime("%H:%M:%S")
        parts = ["ESC{} : {} C".format(i, fmt_temp(t)) for i, t in enumerate(temps, start=1)]
        header = "[{}]".format(ts)
        if parts:
            chunk_size = 4
            chunks = [parts[i:i + chunk_size] for i in range(0, len(parts), chunk_size)]
            print(header)
            for chunk in chunks:
                print("   |   ".join(chunk))
            print()
        else:
            print("{} {}".format(header, "No ESC data available"))
        last_print = now

    time.sleep(0.5)
