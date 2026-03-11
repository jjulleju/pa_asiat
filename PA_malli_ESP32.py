# ================================================================
# ESP32 WROOM - TRAKTORIN RANGE-MITTARI (MicroPython)
# CAN-väylä: SN65HVD230DR transceiver
# Näyttö: MC21605C6W-SPTLYI-V2 (16x2 LCD)
# ================================================================

import machine
import time
from collections import deque
import struct

# =================================================================
# 1. KONFIGURAATIO
# =================================================================

# CAN-asetukset (ESP32 sisäänrakennettu CAN)
CAN_RX_PIN = 16  # GPIO16 - vaihda tarpeen mukaan
CAN_TX_PIN = 17  # GPIO17 - vaihda tarpeen mukaan
CAN_BAUDRATE = 250000  # 250 kbit/s (tyypillinen traktorille)

# CAN ID:t (SAE J1939)
ID_RPM = 2364539904         # EEC1 - Kierrosluku
ID_POLTTOAINE = 0x18FEFC00  # Polttoaineen taso
ID_RUISKUTUS = 0x18F00300   # Ruiskutusmäärä

# LCD I2C asetukset
LCD_ROWS = 2
LCD_COLS = 16
LCD_I2C_ADDR = 0x27      # Osoite (tarkista omastasi: 0x27, 0x3F tai 0x20)
LCD_I2C_SDA = 21         # GPIO21 - Data
LCD_I2C_SCL = 22         # GPIO22 - Clock

# Moottorin/tankin parametrit
TANKKI_KOKO_L = 230
RUISKUTUKSET_PER_KIERROS = 2
KESKIARVO_MINUUTIT = 15
PAIVITYSVALI = 1.0  # Sekuntia

# Historia (deque - tehokas muistin käyttö)
historia_koko = int((KESKIARVO_MINUUTIT * 60) / PAIVITYSVALI)
kulutushistoria = deque(maxlen=historia_koko)

# Tilat
stats = {
    "rpm": 0.0,
    "fuel_pct": 0.0,
    "total_l": 0.0,
    "last_l_s": 0.0,
    "range_h": 0.0,
    "keskikulutus_lh": 0.0
}

# =================================================================
# 2. LCD-NÄYTTÖ (16x2 I2C LCD - PCF8574 backpack)
# ================================================================

class LCD1602_I2C:
    """I2C ohjattu 16x2 LCD (HD44780 + PCF8574 backpack)"""
    
    def __init__(self, i2c, addr=0x27):
        self.i2c = i2c
        self.addr = addr
        self.bl = 0x08  # Backlight on (bit 3)
        self.init_display()
    
    def write_bits(self, bits, mode):
        """Kirjoita 4 bittiä (bitti 0-3)"""
        # bits muoto: [bit7 bit6 bit5 bit4 RS RW E BL]
        # RS (Register Select) = mode (0=cmd, 1=data)
        # RW = 0 (write)
        # E = Enable
        # BL = Backlight
        
        data = bits | (mode << 0) | 0x00 | self.bl
        
        # E pulse
        e_high = data | 0x04
        e_low = data & ~0x04
        
        self.i2c.writeto(self.addr, bytes([e_high]))
        time.sleep_us(1)
        self.i2c.writeto(self.addr, bytes([e_low]))
        time.sleep_us(100)
    
    def write_byte(self, value, mode):
        """Kirjoita 8 bittiä 4-bit moodissa"""
        # Ensin korkeat 4 bittiä
        self.write_bits((value >> 4) & 0x0F, mode)
        # Sitten matalat 4 bittiä
        self.write_bits(value & 0x0F, mode)
    
    def init_display(self):
        """Alusta LCD"""
        time.sleep(0.05)
        
        # 4-bit mode init
        self.write_bits(0x03, 0)  # 8-bit mode
        time.sleep_ms(5)
        self.write_bits(0x03, 0)
        time.sleep_ms(5)
        self.write_bits(0x03, 0)
        time.sleep_ms(1)
        self.write_bits(0x02, 0)  # 4-bit mode
        time.sleep_ms(1)
        
        # Komennot
        self.write_byte(0x28, 0)  # Function set: 4-bit, 2-rivit, 5x8 font
        self.write_byte(0x0C, 0)  # Display ON, cursor OFF, blink OFF
        self.write_byte(0x01, 0)  # Clear display
        time.sleep_ms(2)
        self.write_byte(0x06, 0)  # Entry mode: increment, no shift
    
    def write_string(self, text):
        """Kirjoita merkkijono"""
        for char in text:
            self.write_byte(ord(char), 1)
    
    def set_cursor(self, row, col):
        """Aseta kursori (0-1 rivi, 0-15 sarake)"""
        addresses = [0x00, 0x40]
        self.write_byte(0x80 | (addresses[row] + col), 0)
    
    def clear(self):
        """Tyhjennä näyttö"""
        self.write_byte(0x01, 0)
        time.sleep_ms(2)
    
    def home(self):
        """Kursori alkuun"""
        self.write_byte(0x02, 0)
        time.sleep_ms(2)



# =================================================================
# 3. CAN-VÄYLÄN LUKEMINEN
# =================================================================

def alusta_can():
    """Alusta CAN väylä"""
    try:
        can = machine.CAN(0, extframe=True)  # Käytä laajennettuja kehyksiä (SAE J1939)
        can.init(mode=machine.CAN.NORMAL, baudrate=CAN_BAUDRATE,
                 rx=machine.Pin(CAN_RX_PIN),
                 tx=machine.Pin(CAN_TX_PIN))
        print("CAN väylä alustettu")
        return can
    except Exception as e:
        print(f"VIRHE: CAN-väylää ei saada auki: {e}")
        return None


def lue_can_data(can):
    """Lue ja käsittele CAN-viestit"""
    msg = can.recv(0)
    
    if msg:
        msg_id = msg[0]
        data = msg[1]
        
        # A) Kierrosluku (EEC1 - rpm)
        if msg_id == ID_RPM:
            raw_rpm = data[3] | (data[4] << 8)
            stats["rpm"] = raw_rpm * 0.125
        
        # B) Polttoaineen taso (%)
        elif msg_id == ID_POLTTOAINE:
            stats["fuel_pct"] = data[1] * 0.4
        
        # C) Ruiskutusmäärä
        elif msg_id == ID_RUISKUTUS:
            raw_inj = data[4] | (data[5] << 8)
            mm3 = raw_inj * 0.125
            
            if stats["rpm"] > 100:
                l_per_s = (mm3 * RUISKUTUKSET_PER_KIERROS * stats["rpm"] / 60) / 1000000
                stats["last_l_s"] = l_per_s
                stats["total_l"] += l_per_s


def laske_arvot():
    """Laske kulutus ja range"""
    current_l_s = stats["last_l_s"]
    
    # Lisää historia
    kulutushistoria.append(current_l_s)
    
    # Laske keskiarvo
    if len(kulutushistoria) > 0:
        ka_l_s = sum(kulutushistoria) / len(kulutushistoria)
        stats["keskikulutus_lh"] = ka_l_s * 3600
    else:
        stats["keskikulutus_lh"] = 0.0
    
    # Laske jäljellä olevat liitrat ja range
    litrat_jaljella = (stats["fuel_pct"] / 100) * TANKKI_KOKO_L
    if stats["keskikulutus_lh"] > 0.2:
        stats["range_h"] = litrat_jaljella / stats["keskikulutus_lh"]
    else:
        stats["range_h"] = 0.0


def paivita_lcd(lcd):
    """Päivitä LCD-näyttö"""
    # Rivi 1: RPM ja kulutus
    rivi1 = f"{stats['rpm']:6.0f}rpm {stats['keskikulutus_lh']:5.1f}L/h"
    
    # Rivi 2: Tankki % ja range
    rivi2 = f"{stats['fuel_pct']:5.1f}% {stats['range_h']:6.1f}h"
    
    lcd.set_cursor(0, 0)
    lcd.write_string(rivi1[:16].ljust(16))
    
    lcd.set_cursor(1, 0)
    lcd.write_string(rivi2[:16].ljust(16))


# =================================================================
# 4. PÄÄSILMUKKA
# =================================================================

def main():
    print("Alustetaan ESP32 Range-mittari...")
    
    # Alusta CAN
    can = alusta_can()
    if not can:
        print("VIRHE: CAN väylä ei alustautunut!")
        return
    
    # Alusta I2C
    try:
        i2c = machine.I2C(0, scl=machine.Pin(LCD_I2C_SCL), 
                         sda=machine.Pin(LCD_I2C_SDA), freq=400000)
        print(f"I2C alustettu. Laitteet: {i2c.scan()}")
        
        # Alusta LCD
        lcd = LCD1602_I2C(i2c, addr=LCD_I2C_ADDR)
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.write_string("Range-mittari")
        lcd.set_cursor(1, 0)
        lcd.write_string("Kaynnistetaan...")
        print("LCD alustettu")
        time.sleep(1)
    except Exception as e:
        print(f"VIRHE: I2C/LCD ei alustautunut: {e}")
        lcd = None
    
    # Pääsilmukka
    viimeksi_paiivitetty = 0
    
    try:
        while True:
            # Lue CAN-dataa
            if can:
                lue_can_data(can)
            
            # Päivitä arvot
            laske_arvot()
            
            # Päivitä näyttö (jokaisen sekunnin välein)
            nyt = time.time()
            if nyt - viimeksi_paiivitetty >= PAIVITYSVALI:
                if lcd:
                    paivita_lcd(lcd)
                
                # Konsoliilta tulostus (debuggaus)
                print(f"RPM: {stats['rpm']:.0f} | Polttoaine: {stats['fuel_pct']:.1f}% | "
                      f"Keskikulutus: {stats['keskikulutus_lh']:.2f} L/h | Range: {stats['range_h']:.1f}h")
                
                viimeksi_paiivitetty = nyt
            
            time.sleep_ms(100)
    
    except KeyboardInterrupt:
        print("\nSammutetaan...")
        if lcd:
            lcd.clear()
            lcd.set_cursor(0, 0)
            lcd.write_string("POIS PAALLISTA")


if __name__ == "__main__":
    main()
