import can
import time
import os
import threading
from collections import deque

# =================================================================
# 1. ASETUKSET (TARKISTA SKANNERILLA)
# =================================================================
ID_RPM = 2364539904                 # EEC1 (DBC:stäsi)
ID_POLTTOAINE = 0x18FEFC00          # Polttoaineen taso (J1939 oletus)
ID_RUISKUTUS = 0x18F00300           # Ruiskutusmäärä (J1939 oletus)

TANKKI_KOKO_L = 230
RUISKUTUKSET_PER_KIERROS = 2
KESKIARVO_MINUUTIT = 15
PAIVITYSVALI = 1.0                  # Sekuntia

# =================================================================
# 2. MUUTTUJAT JA HISTORIA
# =================================================================
# deque pitää automaattisesti vain viimeiset 15 minuuttia (900 näytettä)
historia_koko = int((KESKIARVO_MINUUTIT * 60) / PAIVITYSVALI)
kulutushistoria = deque(maxlen=historia_koko)

# Jaetut muuttujat säikeiden välillä
data_lukko = threading.Lock()
stats = {
    "rpm": 0.0,
    "fuel_pct": 0.0,
    "total_l": 0.0,
    "last_l_s": 0.0
}

# =================================================================
# 3. VÄYLÄN LUKEMINEN (TAUSTASÄIE)
# =================================================================
def can_lukija():
    try:
        # Käytetään can0-väylää (esim. PiCAN2 tai Waveshare CAN-hat)
        bus = can.interface.Bus(channel='can0', bustype='socketcan')
    except Exception as e:
        print(f"VIRHE: CAN-väylää ei saada auki: {e}")
        return

    while True:
        msg = bus.recv(0.1)
        if msg:
            with data_lukko:
                # A) Kierrosluku (DBC: bitit 24-39)
                if msg.arbitration_id == ID_RPM:
                    raw_rpm = msg.data[3] | (msg.data[4] << 8)
                    stats["rpm"] = raw_rpm * 0.125

                # B) Polttoaineen taso (%)
                elif msg.arbitration_id == ID_POLTTOAINE:
                    stats["fuel_pct"] = msg.data[1] * 0.4

                # C) Ruiskutusmäärä (mm3/isku)
                elif msg.arbitration_id == ID_RUISKUTUS:
                    raw_inj = msg.data[4] | (msg.data[5] << 8)
                    mm3 = raw_inj * 0.125
                    
                    if stats["rpm"] > 100:
                        # Muunnos Litraa / sekunti
                        l_per_s = (mm3 * RUISKUTUKSET_PER_KIERROS * stats["rpm"] / 60) / 1000000
                        stats["last_l_s"] = l_per_s
                        stats["total_l"] += l_per_s

# =================================================================
# 4. LASKENTA JA NÄYTTÖ (PÄÄSÄIE)
# =================================================================
def main():
    # Käynnistetään väylän luku taustalle
    t = threading.Thread(target=can_lukija, daemon=True)
    t.start()

    print("Käynnistetään ennustemalli...")
    time.sleep(2) # Odotetaan että dataa alkaa tulla

    try:
        while True:
            with data_lukko:
                current_l_s = stats["last_l_s"]
                rpm = stats["rpm"]
                fuel_pct = stats["fuel_pct"]
                total_l = stats["total_l"]
            
            # Lisätään tämän sekunnin kulutus historiaan
            kulutushistoria.append(current_l_s)

            # Lasketaan 15 minuutin keskikulutus (L/h)
            if len(kulutushistoria) > 0:
                ka_l_s = sum(kulutushistoria) / len(kulutushistoria)
                keskikulutus_lh = ka_l_s * 3600
            else:
                keskikulutus_lh = 0.0

            litrat_jaljella = (fuel_pct / 100) * TANKKI_KOKO_L
            range_h = litrat_jaljella / keskikulutus_lh if keskikulutus_lh > 0.2 else 0.0

            # Tulostus terminaaliin tai myöhemmin HDMI-näytölle
            os.system('clear')
            print("==========================================")
            print("      TRAKTORIN RANGE-MITTARI (Python)    ")
            print("==========================================")
            print(f" MOOTTORI:     {rpm:>7.0f} RPM")
            print(f" TANKISSA:     {fuel_pct:>7.1f} % ({litrat_jaljella:.1f} L)")
            print(f" KESKIKULUTUS: {keskikulutus_lh:>7.2f} L/h (15 min)")
            print(f" KULUTETTU:    {total_l:>7.3f} Litraa")
            print("------------------------------------------")
            print(f" RANGE:        {range_h:>7.1f} TUNTIA")
            print("==========================================")
            
            time.sleep(PAIVITYSVALI)

    except KeyboardInterrupt:
        print("\nSammutetaan...")

if __name__ == "__main__":
    main()
