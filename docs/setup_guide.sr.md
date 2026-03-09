# IoT Variometar - Kompletan Setup Guide

Detaljan vodič za instalaciju i podešavanje IoT variometra na Raspberry Pi 5.

*[Srpska verzija](setup_guide.md)*

---

## Potreban hardware

### Obavezni delovi
- **Raspberry Pi 5** (4GB+ RAM preporučeno)
- **MicroSD kartica** - 32GB Class 10 minimum
- **BMP390** barometrijski senzor sa I2C interfejsom
- **Power bank** - 20,000mAh
- **Breadboard** i jumper kablovi za konekcije

### Opciono
- **Buzzer** za audio signale (buduće proširenje)
- **GPS modul** za poziciju (buduće proširenje)
- **Kućište** za zaštitu od elemenata

### Gde kupiti (Srbija)
- **malina314, Beograd**
- **AliExpress** - jeftinije, sporija dostava

## Hardware konekcije

### BMP390 → Raspberry Pi 5 pinovi

```
BMP390 PIN    RPi5 PIN    FUNKCIJA
==========    ========    ========
VCC           Pin 1       3.3V Power
GND           Pin 6       Ground
SDA           Pin 3       I2C Data (GPIO 2)
SCL           Pin 5       I2C Clock (GPIO 3)
INT           -           Ne povezivati
```

**VAŽNO**: Koristi 3.3V (Pin 1), ne 5V (Pin 2)!

### Fizička lokacija pinova
```
Pin 1 (3.3V) ●○ Pin 2 (5V)
Pin 3 (SDA)  ●○ Pin 4 (5V)  
Pin 5 (SCL)  ●○ Pin 6 (GND)
```

## Software instalacija

### Korak 1: Raspberry Pi OS setup

1. **Flash Raspberry Pi OS** na SD karticu
2. **Boot RPi5** i konektuj na mrežu
3. **SSH pristup**: `ssh ime@<rpi-ip-address>`

### Korak 2: Sistemski dependencies

```bash
# Update sistema
sudo apt update && sudo apt upgrade -y

# Instaliraj osnovne alate
sudo apt install python3-pip git i2c-tools nano curl -y

# Enable I2C interfejs
sudo raspi-config
# Interface Options → I2C → Enable → Reboot
```

### Korak 3: Python virtual environment

```bash
# Kreiraj virtual environment (po želji)
python3 -m venv variometar_env
source variometar_env/bin/activate

# Instaliraj Python biblioteke
pip install flask==2.3.3
pip install flask-socketio==5.3.6
pip install adafruit-circuitpython-bmp3xx==1.4.3
pip install pytz==2023.3
```

### Korak 4: Test senzor konekcije

```bash
# Proveri da li RPi vidi senzor
i2cdetect -y 1
# Treba da vidi "77" na mapi
```

## WiFi Hotspot konfiguracija

### Korak 1: Instaliraj hostapd i dnsmasq

```bash
sudo apt install hostapd dnsmasq -y
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
```

### Korak 2: Konfiguracija hostapd

```bash
sudo nano /etc/hostapd/hostapd.conf
```

Sadržaj fajla:
```
interface=wlan0
driver=nl80211
ssid=rpi_WiFi
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=rpi123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

### Korak 3: Konfiguracija dnsmasq

```bash
sudo nano /etc/dnsmasq.conf
```

Dodaj na kraj:
```
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
```

### Korak 4: Statička IP konfiguracija

```bash
sudo nano /etc/dhcpcd.conf
```

Dodaj na kraj:
```
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
```

## Aplikacijski fajlovi

### Korak 1: Preuzmi source kod

```bash
# Clone GitHub repo
git clone https://github.com/ognjenzekovic/variometar.git
cd variometar/rpi

# Ili kreiraj fajlove manualno
nano variometar_web.py
# [kopiraj sadržaj iz repoa]
```

### Korak 2: Startup script

```bash
nano /home/user/start_variometar.sh
chmod +x /home/user/start_variometar.sh
```

### Korak 3: Cron job za autostart

```bash
crontab -e
# Dodaj liniju:
@reboot /home/user/start_variometar.sh
```

## Testiranje sistema

### Test 1: Hotspot funkcionalnost

1. **Reboot RPi5**: `sudo reboot`
2. **Sačekaj 20 sekundi** za startup
3. **Traži WiFi mrežu** "rpi_WiFi" (ili koje god ime da je dodato) na telefonu
4. **Konektuj se** sa šifrom "rpi123" (ili koja god šifra da je postavljena)
5. **Test pristupa**: http://192.168.4.1:5000

### Test 2: Senzor funkcionalnost

1. **Pristupi web interfejsu**
2. **Proveri live podatke** - temperatura, pritisak, visina
3. **Test climb rate** - pomeri senzor gore/dole
4. **Test snimanje leta** - Start/Stop dugmad

### Test 3: Flutter aplikacija

1. **Instaliraj Flutter SDK** na development računar
2. **Configure dependencies** u pubspec.yaml
3. **Update IP adrese** u main.dart ako potrebno
4. **Flutter run** za testiranje

## Debugging česti problemi

### Problem: BMP390 ne odgovara (Error 121)

**Uzrok**: I2C komunikacijski problem
```bash
# Proveri konekcije kablova
# Restartuj I2C bus:
sudo modprobe -r i2c_bcm2835
sudo modprobe i2c_bcm2835
i2cdetect -y 1
```

### Problem: Hotspot ne radi

**Uzrok**: NetworkManager interferiše
```bash
# Manualni reset:
sudo systemctl stop NetworkManager
sudo systemctl restart hostapd dnsmasq
sudo ip addr add 192.168.4.1/24 dev wlan0
```

### Problem: Web aplikacija ne startuje

**Uzrok**: Virtual environment ili permissions
```bash
# Check logove:
cat /home/user/debug.log
cat /home/user/app.log

# Manualni start:
cd /home/user
source variometar_env/bin/activate
python3 variometar_web.py
```

### Problem: Flask-SocketIO greška

**Uzrok**: Werkzeug production warning
```python
# Dodaj u kod:
socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
```

## Performance optimizacija

### Cooling (preporučeno)
- **Ventilator** ili **heatsink** za RPi5
- **Sprečava throttling** pri visokim temperaturama

### Battery management
- **Power bank 20,000mAh** = 6-8h rada
- **USB-C PD** podrška za brže punjenje

### Network optimizacija
- **Channel 7** za 2.4GHz - manja interferencija
- **Domet 50-100m** u otvorenom prostoru

## Održavanje

### Backup konfiguracije
```bash
# Kreiraj backup
tar -czf variometar_backup.tar.gz /home/user/variometar* /etc/hostapd/ /etc/dnsmasq.conf

# Restore
tar -xzf variometar_backup.tar.gz -C /
```

### Log rotation
```bash
# Dodaj u crontab:
0 0 * * 0 find /home/user -name "*.log" -mtime +7 -delete
```

### Update procedure
```bash
cd /home/user/variometar
git pull origin main
sudo systemctl restart variometar  # ako je service kreiran
```

## Sigurnost

### Network security
- **WPA2-PSK** za WiFi hotspot
- **SSH key authentication** umesto password
- **Firewall** za ograničavanje pristupa

## Support

Za probleme i pitanja:
1. **Proveri debug logove**: `/home/user/debug.log`
2. **Test komponente** pojedinačno
3. **GitHub Issues** - reportuj bugove
4. **Forum zajednice** za general support

---

**Napomena**: Ovaj vodič pretpostavlja osnovnu familijarnost sa Linux-om i Raspberry Pi platformom. Za apsolutne početnike, preporučuje se dodatno čitanje o Raspberry Pi OS.
