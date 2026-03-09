# IoT Variometer — Setup Guide

Complete installation and configuration guide for the IoT variometer on Raspberry Pi 5.

*[Srpska verzija](setup_guide_sr.md)*

---

## Required Hardware

### Essential
- **Raspberry Pi 5** (4GB+ RAM recommended)
- **MicroSD card** — 32GB Class 10 minimum
- **BMP390** barometric sensor with I2C interface
- **20,000mAh power bank**
- **Breadboard** and jumper wires

### Optional (future expansions)
- **Buzzer** for audio variometer tones
- **GPS module** for position tracking
- **Enclosure** for weather protection

### Where to buy (Serbia)
- **malina314, Belgrade** — local RPi supplier
- **AliExpress** — cheaper, slower shipping

---

## Hardware Wiring

### BMP390 → Raspberry Pi 5

```
BMP390 PIN    RPi5 PIN    Function
──────────    ────────    ────────
VCC           Pin 1       3.3V Power
GND           Pin 6       Ground
SDA           Pin 3       I2C Data  (GPIO 2)
SCL           Pin 5       I2C Clock (GPIO 3)
INT           —           Do not connect
```

> **IMPORTANT**: Use 3.3V (Pin 1), not 5V (Pin 2). The BMP390 will be damaged by 5V.

### Physical pin layout reference
```
Pin 1 (3.3V) ●○ Pin 2 (5V)
Pin 3 (SDA)  ●○ Pin 4 (5V)
Pin 5 (SCL)  ●○ Pin 6 (GND)
```

---

## Software Installation

### Step 1: Raspberry Pi OS setup

1. Flash **Raspberry Pi OS** (64-bit, Lite recommended) to the SD card using Raspberry Pi Imager
2. Boot the RPi5 and connect it to your local network
3. SSH in: `ssh <your-username>@<rpi-ip-address>`

### Step 2: System dependencies

```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Install required tools
sudo apt install python3-pip git i2c-tools nano curl -y

# Enable I2C interface
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable → Reboot
```

### Step 3: Python virtual environment

```bash
# Create a virtual environment
python3 -m venv variometar_env
source variometar_env/bin/activate

# Install Python libraries
pip install flask==2.3.3
pip install flask-socketio==5.3.6
pip install adafruit-circuitpython-bmp3xx==1.4.3
pip install pytz==2023.3
```

### Step 4: Verify sensor connection

```bash
# Check that the RPi can see the sensor on the I2C bus
i2cdetect -y 1
# You should see "77" appear on the address map
```

---

## WiFi Hotspot Configuration

### Step 1: Install hostapd and dnsmasq

```bash
sudo apt install hostapd dnsmasq -y
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
```

### Step 2: Configure hostapd

```bash
sudo nano /etc/hostapd/hostapd.conf
```

Paste the following:

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

> Change `ssid` and `wpa_passphrase` to your preferred network name and password.

### Step 3: Configure dnsmasq

```bash
sudo nano /etc/dnsmasq.conf
```

Append to the end of the file:

```
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
```

### Step 4: Static IP configuration

```bash
sudo nano /etc/dhcpcd.conf
```

Append to the end of the file:

```
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
```

---

## Application Files

### Step 1: Get the source code

```bash
# Clone the repository
git clone https://github.com/your-username/variometar.git
cd variometar/rpi
```

### Step 2: Startup script

```bash
nano /home/<your-username>/start_variometar.sh
chmod +x /home/<your-username>/start_variometar.sh
```

### Step 3: Autostart on boot via cron

```bash
crontab -e
# Add the following line:
@reboot /home/<your-username>/start_variometar.sh
```

---

## Testing

### Test 1: Hotspot

1. **Reboot** the RPi5: `sudo reboot`
2. **Wait ~20 seconds** for the system to start
3. **Scan for WiFi** on your phone — you should see `rpi_WiFi`
4. **Connect** using the password set in `hostapd.conf`
5. **Open browser** and navigate to `http://192.168.4.1:5000`

### Test 2: Sensor

1. Open the web interface
2. Check the live data — temperature, pressure, and altitude should be updating
3. Move the sensor up and down to verify climb rate responds correctly
4. Test flight recording — press Start, wait a moment, press Stop

### Test 3: Flutter app

1. Install **Flutter SDK** on your development machine
2. Configure dependencies in `pubspec.yaml`
3. Update the IP addresses in `main.dart` if needed
4. Run `flutter run` to test on a connected device

---

## Troubleshooting

### BMP390 not responding (Error 121)

**Cause**: I2C communication failure — usually a wiring issue.

```bash
# Check your cable connections, then restart the I2C bus:
sudo modprobe -r i2c_bcm2835
sudo modprobe i2c_bcm2835
i2cdetect -y 1
```

### Hotspot not working

**Cause**: NetworkManager interfering with hostapd.

```bash
sudo systemctl stop NetworkManager
sudo systemctl restart hostapd dnsmasq
sudo ip addr add 192.168.4.1/24 dev wlan0
```

### Web app not starting

**Cause**: Virtual environment not activated, or a permissions issue.

```bash
# Check the logs:
cat /home/<your-username>/debug.log
cat /home/<your-username>/app.log

# Manual start for debugging:
cd /home/<your-username>
source variometar_env/bin/activate
python3 variometar_web.py
```

### Flask-SocketIO warning on startup

**Cause**: Werkzeug production mode warning.

```python
# Add this flag to the socketio.run() call in variometar_web.py:
socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
```

---

## Performance Tips

### Cooling
RPi5 runs hot under sustained load. A heatsink or small fan is recommended to prevent thermal throttling, especially when mounted in an enclosure.

### Battery
A 20,000mAh power bank with USB-C PD support gives approximately 6–8 hours of runtime. USB-C PD also speeds up charging between flights.

### WiFi channel
Channel 7 (2.4GHz) generally has less interference in open outdoor environments. If you experience connectivity issues near other pilots or infrastructure, try channels 1 or 11.

---

## Maintenance

### Backup your configuration

```bash
tar -czf variometar_backup.tar.gz \
  /home/<your-username>/variometar* \
  /etc/hostapd/ \
  /etc/dnsmasq.conf
```

### Restore from backup

```bash
tar -xzf variometar_backup.tar.gz -C /
```

### Log rotation (add to crontab)

```bash
0 0 * * 0 find /home/<your-username> -name "*.log" -mtime +7 -delete
```

### Updating the application

```bash
cd /home/<your-username>/variometar
git pull origin main
sudo systemctl restart variometar   # if running as a systemd service
```

---

## Security Notes

- The hotspot uses **WPA2-PSK** — change the default password before use in the field
- Use **SSH key authentication** instead of password login for the RPi
- Consider adding a basic firewall to restrict access to only the ports the app needs

---

## Support

1. Check the debug logs at `/home/<your-username>/debug.log`
2. Test hardware components individually using the steps above
3. Open a GitHub Issue for bugs or unexpected behaviour

---

*This guide assumes basic familiarity with Linux and the Raspberry Pi platform. If you're new to either, the [official Raspberry Pi documentation](https://www.raspberrypi.com/documentation/) is a good starting point.*
