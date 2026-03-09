# IoT Variometer

> A paragliding variometer with IoT capabilities — built on Raspberry Pi 5 with a BMP390 barometric sensor. Access real-time flight data over WiFi via a web interface or native Flutter mobile app.

**[Pročitaj na srpskom → README.sr.md](README.sr.md)**

---

![Product](docs/images/product.jpg)

---

## Features

### Backend (Raspberry Pi 5)
- Real-time barometric pressure, temperature, and altitude readings
- Climb/sink rate calculation with noise filtering
- WiFi hotspot mode for direct access without internet
- WebSocket communication for real-time data streaming
- Automatic flight recording with statistics
- REST API for managing recorded flights
- JSON-based data storage

### Web Interface
- Mobile-responsive design
- Live sensor data display
- Start/Stop controls for flight recording
- List of recorded flights with details
- Flight deletion support

### Flutter Mobile App
- Native Android/iOS application
- WebSocket connection for real-time data
- Full flight management (start, stop, view, delete)
- Automatic switching between hotspot/WiFi modes

---

## System Architecture

![Architecture](docs/images/architecture.png)

---

## Screenshots

| Main Screen | Recording Active | Flight Details |
|:-----------:|:----------------:|:--------------:|
| ![Main](docs/images/screenshot_main.png) | ![Recording](docs/images/screenshot_recording.png) | ![Details](docs/images/screenshot_details.png) |

---

## Technical Specification

### Hardware
| Component | Description |
|-----------|-------------|
| **Raspberry Pi 5** | Main computing unit |
| **BMP390** | Barometric sensor (±0.03 hPa accuracy) |
| **Power bank 20,000mAh** | Portable power supply |
| **I2C interface** | Sensor connection via GPIO pins |

### Software Stack
| Layer | Technology |
|-------|------------|
| Backend | Python 3.11 + Flask |
| Real-time comms | Flask-SocketIO (WebSocket) |
| Sensor library | Adafruit CircuitPython BMP3xx |
| WiFi hotspot | hostapd + dnsmasq |
| Mobile app | Flutter / Dart |

### Networking
- **Hotspot mode**: RPi creates its own WiFi network (`192.168.4.1`)
- **WiFi client mode**: connects to an existing network
- **Hybrid approach**: automatic switching between modes

---

## Project Structure

```
variometer/
├── backend/
│   ├── variometar_web.py          # Flask web server with WebSocket
│   ├── start_variometer.sh        # Startup script with hotspot setup
│   └── requirements.txt           # Python dependencies
├── flutter_app/
│   ├── lib/main.dart              # Flutter application
│   └── pubspec.yaml               # Flutter dependencies
├── docs/
│   ├── images/                    # Architecture, product, screenshots
│   └── setup_guide.md             # Detailed setup guide
└── README.md
```

---

## Quick Start

1. **Hardware**: Connect BMP390 to RPi5 I2C pins (see [setup guide](docs/setup_guide.md))
2. **Software**: Run the setup script to install dependencies
3. **Network**: Configure WiFi hotspot
4. **Test**: Verify sensor communication and web interface at `http://192.168.4.1:5000`

Full instructions → [docs/setup_guide.md](docs/setup_guide.md)

---

## Key Algorithms

### Climb Rate Filtering
- Moving average over a 3-second window to reduce sensor noise
- Uses real timestamps instead of assumed fixed intervals
- Produces stable, reliable readings during flight

### Flight Statistics
Rather than storing all raw sensor data, the system stores optimized statistics per flight:
- Max/min altitude and temperature
- Max climb and sink rates
- Total duration and sample count
- Altitude delta over the flight

---

## API Reference

### WebSocket Events
| Event | Direction | Description |
|-------|-----------|-------------|
| `sensor_data` | Server → Client | Real-time sensor readings |
| `start_flight` | Client → Server | Begin flight recording |
| `stop_flight` | Client → Server | End flight recording |

### REST API
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/flights` | List all recorded flights |
| `GET` | `/api/flight/<filename>` | Get details of a specific flight |
| `DELETE` | `/api/flight/<filename>` | Delete a flight |

---

## Performance

| Metric | Value |
|--------|-------|
| Sampling rate | 2 Hz (every 0.5s) |
| Altitude accuracy | ±25 cm (BMP390 spec) |
| WiFi range | 50–100 m |
| Battery life | ~6–8h (20,000mAh power bank) |

---

## Roadmap

- [ ] GPS module for position and ground speed tracking
- [ ] Cloud sync functionality
- [ ] Integrated thermal activity analysis

---

## About

Developed as a thesis project at the **Faculty of Technical Sciences, University of Novi Sad**, Department of Computing and Automation. Demonstrates practical application of IoT technologies in sport aviation.
