
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import time
import board
import busio
import adafruit_bmp3xx
import threading
import json
import datetime
import os
import pytz
from gpiozero import PWMOutputDevice

app = Flask(__name__)
app.config['SECRET_KEY'] = 'variometer_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# BMP390 setup
i2c = busio.I2C(board.SCL, board.SDA)
bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)
bmp.sea_level_pressure = 1013.25

#buzzer setup
BUZZER_PIN = 18
try:
    buzzer = PWMOutputDevice(BUZZER_PIN)
    print("Buzzer initialized on GPIO 18")
except Exception as e:
    print(f"Buzzer setup failed: {e}")
    buzzer = None

# Global variables
current_data = {
    "temperature": 0,
    "pressure": 0,
    "altitude": 0,
    "climb_rate": 0,
    "timestamp": ""
}

flight_recording = False
flight_data = []
flight_start_time = None
altitude_history = []

audio_enabled = True
last_audio_time = 0

BELGRADE_TZ = pytz.timezone('Europe/Belgrade')

def get_belgrade_time():
    """Dobij trenutno vreme u Beogradu"""
    return datetime.datetime.now(BELGRADE_TZ)

def play_variometer_sound(climb_rate):
    """Generiše audio feedback na osnovu brzine penjanja/spuštanja"""
    global buzzer, audio_enabled
    
    if not buzzer or not audio_enabled:
        return
        
    try:
        # Ako je brzina mala, nema tona
        if abs(climb_rate) < 0.1:
            buzzer.value = 0  # Stop buzzer
            return
        
        if climb_rate > 0:  # Penjanje
            # Visoki ton, brži kada je veći climb rate
            frequency = int(800 + (climb_rate * 200))  # 800-2000Hz
            buzzer.frequency = min(frequency, 2000)
            buzzer.value = 0.5  # 50% duty cycle
            
        else:  # Spuštanje
            # Nizak ton, sporiji kada je veći sink rate
            frequency = int(400 - (abs(climb_rate) * 50))  # 200-400Hz
            buzzer.frequency = max(frequency, 200)
            buzzer.value = 0.3  # Tiši za spuštanje
            
    except Exception as e:
        print(f"Buzzer error: {e}")

def calculate_climb_rate():
    """Kalkuliše brzinu penjanja/spuštanja"""
    global altitude_history
    try:
        current_alt = bmp.altitude
    
    # Dodaj u istoriju (drži poslednih 5 merenja za smooth-ovanje)
        altitude_history.append(current_alt)
        if len(altitude_history) > 5:
            altitude_history.pop(0)
    
    # Kalkuliraj prosečnu brzinu promene
        if len(altitude_history) >= 2:
        # Brzina promene u metrima po sekundi (merimo svakih 0.5s)
            time_diff = 0.5 * (len(altitude_history) - 1)
            alt_diff = altitude_history[-1] - altitude_history[0]
            climb_rate = alt_diff / time_diff if time_diff > 0 else 0
        
        # Zaokruži na 1 decimalu
            return round(climb_rate, 1)
    
        return 0.0
    except Exception as e:
        print(f"BMP390 read error: {e}")
        return 0.0 

def read_sensor():
    """Background thread za čitanje senzora"""
    global current_data, flight_recording, audio_enabled, last_audio_time
    
    while True:
        try:
            climb_rate = calculate_climb_rate()

            current_time = time.time()
            if audio_enabled and (current_time - last_audio_time) > 0.8:
                play_variometer_sound(climb_rate)
                last_audio_time = current_time
            
            current_data = {
                "temperature": round(bmp.temperature, 1),
                "pressure": round(bmp.pressure, 1),
                "altitude": round(bmp.altitude, 1),
                "climb_rate": climb_rate,
                "timestamp": get_belgrade_time().isoformat()
            }
            
            # Ako je let u toku, ažuriraj statistike
            if flight_recording:
                update_flight_stats(current_data)
            
            # Pošalji podatke svim povezanim klijentima
            socketio.emit('sensor_data', current_data)
            
        except Exception as e:
            print(f"Sensor error: {e}")
        
        time.sleep(1.0)

# Pokreni sensor thread
sensor_thread = threading.Thread(target=read_sensor, daemon=True)
sensor_thread.start()

@app.route('/')
def index():
    """Glavna web stranica"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Variometar Live</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
        <style>
            body { 
                font-family: Arial; margin: 20px; background: #1a1a1a; color: white;
                padding-bottom: 120px;
            }
            .tabs {
                display: flex; background: #333; border-radius: 10px; margin-bottom: 20px;
            }
            .tab {
                flex: 1; padding: 15px; text-align: center; cursor: pointer;
                background: #555; border: none; color: white; font-size: 1em;
            }
            .tab.active { background: #4CAF50; }
            .tab:first-child { border-radius: 10px 0 0 10px; }
            .tab:last-child { border-radius: 0 10px 10px 0; }
            
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            
            .data-box { 
                background: #333; padding: 20px; margin: 10px 0; 
                border-radius: 10px; text-align: center;
            }
            .value { font-size: 2.5em; color: #4CAF50; margin: 10px 0; }
            .climb-rate { font-size: 3em; font-weight: bold; }
            .climb-up { color: #4CAF50; }
            .climb-down { color: #f44336; }
            .climb-stable { color: #ff9800; }
            
            .flight-list {
                background: #333; padding: 20px; border-radius: 10px;
                max-height: 400px; overflow-y: auto;
            }
            .flight-item {
                background: #444; padding: 15px; margin: 10px 0; border-radius: 8px;
                cursor: pointer; transition: background 0.2s;
                display: flex; justify-content: space-between; align-items: center;
            }
            .flight-item:hover { background: #555; }
            .flight-info { flex: 1; }
            .flight-header { font-weight: bold; color: #4CAF50; }
            .flight-details { color: #ccc; font-size: 0.9em; margin-top: 5px; }            
            .delete-btn {
                background: #f44336; color: white; border: none; padding: 8px 12px;
                border-radius: 5px; cursor: pointer; font-size: 0.8em;
                margin-left: 10px;
            }
            .delete-btn:hover { background: #d32f2f; }

            .controls { 
                position: fixed; bottom: 20px; left: 20px; right: 20px;
                display: flex; gap: 10px;
            }
            .btn { 
                flex: 1; padding: 15px; font-size: 1.2em; border: none; 
                border-radius: 8px; cursor: pointer; font-weight: bold;
            }
            .start-btn { background: #4CAF50; color: white; }
            .stop-btn { background: #f44336; color: white; }
            .disabled { background: #666; cursor: not-allowed; }
            .recording { background: #ff9800; animation: pulse 1s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        </style>
    </head>
    <body>
        <h1>Variometar</h1>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('live')">Podaci Uživo</button>
            <button class="tab" onclick="showTab('flights')">Snimljeni Letovi</button>
        </div>
        
        <div id="live-content" class="tab-content active">
            <div class="data-box">
                <h3>Brzina Penjanja/Spuštanja</h3>
                <div class="value climb-rate" id="climb_rate">--</div>
                <span>m/s</span>
            </div>
            
            <div class="data-box">
                <h3>Visina</h3>
                <div class="value" id="altitude">--</div>
                <span>m</span>
            </div>
            
            <div class="data-box">
                <h3>Pritisak</h3>
                <div class="value" id="pressure">--</div>
                <span>hPa</span>
            </div>
            
            <div class="data-box">
                <h3>Temperatura</h3>
                <div class="value" id="temperature">--</div>
                <span>°C</span>
            </div>
        </div>
        
        <div id="flights-content" class="tab-content">
            <div class="flight-list" id="flightList">
                <div style="text-align: center; color: #666;">
                    Učitavam letove...
                </div>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn start-btn" id="startBtn" onclick="startFlight()">
                ✈️ POKRENI LET
            </button>
            <button class="btn stop-btn disabled" id="stopBtn" onclick="stopFlight()">
                🛑 ZAVRŠI LET
            </button>
        </div>
        
        <script>
            const socket = io();
            let recording = false;
            
            socket.on('sensor_data', function(data) {
                document.getElementById('temperature').textContent = data.temperature;
                document.getElementById('pressure').textContent = data.pressure;
                document.getElementById('altitude').textContent = data.altitude;
                
                // Climb rate sa bojama
                const climbRate = data.climb_rate;
                const climbElement = document.getElementById('climb_rate');
                climbElement.textContent = climbRate > 0 ? '+' + climbRate : climbRate;
                
                // Oboji na osnovu brzine
                climbElement.className = 'value climb-rate ';
                if (climbRate > 0.2) {
                    climbElement.className += 'climb-up';
                } else if (climbRate < -0.2) {
                    climbElement.className += 'climb-down';
                } else {
                    climbElement.className += 'climb-stable';
                }
            });
            
            socket.on('flight_started', function() {
                recording = true;
                document.getElementById('startBtn').className = 'btn recording';
                document.getElementById('startBtn').textContent = '🔴 SNIMAM...';
                document.getElementById('stopBtn').className = 'btn stop-btn';
            });
            
            socket.on('flight_stopped', function(data) {
                recording = false;
                document.getElementById('startBtn').className = 'btn start-btn';
                document.getElementById('startBtn').textContent = '✈️ POKRENI LET';
                document.getElementById('stopBtn').className = 'btn stop-btn disabled';
                
                // Osvežava listu letova
                loadFlights();
            });
            
            function showTab(tabName) {
                // Sakrij sve tab-ove
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Prikaži selektovani tab
                document.getElementById(tabName + '-content').classList.add('active');
                event.target.classList.add('active');
                
                // Učitaj letove ako je flights tab
                if (tabName === 'flights') {
                    loadFlights();
                }
            }
            
            function loadFlights() {
                fetch('/api/flights')
                    .then(response => response.json())
                    .then(flights => {
                        const flightList = document.getElementById('flightList');
                        
                        if (flights.length === 0) {
                            flightList.innerHTML = '<div style="text-align: center; color: #666;">Nema snimljenih letova</div>';
                            return;
                        }
                        
                        flightList.innerHTML = flights.map(filename => {
                            const parts = filename.replace('.json', '').split('_');
                            const date = parts[1];
                            const time = parts[2];
                            
                            const formattedDate = date.substring(0,4) + '-' + date.substring(4,6) + '-' + date.substring(6,8);
                            const formattedTime = time.substring(0,2) + ':' + time.substring(2,4) + ':' + time.substring(4,6);
                            
                            return `
                                <div class="flight-item">
                                    <div class="flight-info" onclick="viewFlight('${filename}')">
                                        <div class="flight-header">${formattedDate} ${formattedTime}</div>
                                        <div class="flight-details">Klikni za detalje</div>
                                    </div>
                                    <button class="delete-btn" onclick="deleteFlight('${filename}'); event.stopPropagation();">
                                        🗑️ Obriši
                                    </button>
                                </div>
                            `;
                        }).join('');
                    })
                    .catch(error => {
                        document.getElementById('flightList').innerHTML = 
                            '<div style="text-align: center; color: #f44336;">Greška pri učitavanju letova</div>';
                    });
            }
            
            function viewFlight(filename) {
                fetch(`/api/flight/${filename}`)
                    .then(response => response.json())
                    .then(flight => {
                        const duration = Math.round(flight.duration_seconds / 60);
                        const altGain = flight.max_altitude - flight.min_altitude;
                        
                        const startTime = new Date(flight.start_time);
                        const formattedDateTime = startTime.toLocaleString('sr-RS', {
                            year: 'numeric',
                            month: '2-digit', 
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                        });
                        
                        alert(`Detalji Leta:\\n\\nDatum: ${formattedDateTime}\\nTrajanje: ${duration} min\\nMax visina: ${flight.max_altitude.toFixed(1)}m\\nMin visina: ${flight.min_altitude.toFixed(1)}m\\nVisinska razlika: ${altGain.toFixed(1)}m\\nMax penjanje: ${flight.max_climb_rate.toFixed(1)} m/s\\nMax spuštanje: ${flight.max_sink_rate.toFixed(1)} m/s\\nProsečna temperatura: ${flight.avg_temperature.toFixed(1)} °C`);
                    })
	        .catch(error => {
	            console.error('Error:', error);
	            alert('Greška pri učitavanju leta');
	        });
            }

	    function deleteFlight(filename) {
                if (!confirm('Da li si siguran da želiš da obrišeš ovaj let?')) {
                    return;
                }
    
                fetch(`/api/flight/${filename}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(result => {
                        if (result.success) {
                            loadFlights(); // Osvežava listu
                        } else {
                            alert('Greška pri brisanju leta');
                        }
                    })
	            .catch(error => {
	                console.error('Error:', error);
	                alert('Greška pri brisanju leta');
	            });
            }
	            
            function startFlight() {
                if (!recording) {
                    socket.emit('start_flight');
                }
            }
            
            function stopFlight() {
                if (recording) {
                    socket.emit('stop_flight');
                }
            }
        </script>
    </body>
    </html>
    '''

@app.route('/api/data')
def get_data():
    """API endpoint za trenutne podatke"""
    return jsonify(current_data)

@app.route('/api/flights')
def get_flights():
    """Lista svih snimljenih letova"""
    flights = []
    flights_dir = '/home/milaogi/flights'
    
    if os.path.exists(flights_dir):
        for filename in os.listdir(flights_dir):
            if filename.endswith('.json'):
                flights.append(filename)
    
    return jsonify(flights)

@app.route('/api/flight/<filename>')
def get_flight_data(filename):
    """Dobij podatke određenog leta"""
    flight_path = f'/home/milaogi/flights/{filename}'
    
    if os.path.exists(flight_path):
        with open(flight_path, 'r') as f:
            return jsonify(json.load(f))
    else:
        return jsonify({"error": "Flight not found"}), 404

@app.route('/api/flight/<filename>', methods=['DELETE'])
def delete_flight(filename):
    """Obriši let"""
    flight_path = f'/home/milaogi/flights/{filename}'
    
    try:
        if os.path.exists(flight_path):
            os.remove(flight_path)
            print(f"Flight deleted: {filename}")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Flight not found"}), 404
    except Exception as e:
        print(f"Error deleting flight: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/api/audio', methods=['POST'])
def toggle_audio():
    """Uključi/isključi audio feedback"""
    global audio_enabled, buzzer
    data = request.get_json()
    audio_enabled = data.get('enabled', True)
    
    if not audio_enabled and buzzer:
        buzzer.value = 0  # Sigurno ugasi buzzer
    
    return jsonify({"audio_enabled": audio_enabled})

@app.route('/api/audio', methods=['GET'])
def get_audio_status():
    """Dobij status audio funkcionalnosti"""
    return jsonify({"audio_enabled": audio_enabled})

@socketio.on('start_flight')
def handle_start_flight():
    """WebSocket handler za pokretanje leta"""
    global flight_recording, flight_stats, flight_start_time
    
    if not flight_recording:
        flight_recording = True
        flight_start_time = get_belgrade_time()
        
        # Reset statistike
        flight_stats = {
            "max_altitude": 0,
            "min_altitude": float('inf'),
            "max_climb_rate": 0,
            "max_sink_rate": 0,
            "data_points": 0,
    	    "temp_sum": 0
        }
        
        emit('flight_started', broadcast=True)
        print(f"Flight started at {flight_start_time}")

@socketio.on('stop_flight')
def handle_stop_flight():
    """WebSocket handler za završetak leta"""
    global flight_recording, flight_stats, flight_start_time
    
    if flight_recording:
        flight_recording = False
        flight_end_time = get_belgrade_time()
        duration = flight_end_time - flight_start_time
        
        # Sačuvaj let
        save_flight(flight_stats, flight_start_time, flight_end_time)
        
        emit('flight_stopped', {
            'duration': str(duration).split('.')[0],
            'data_points': flight_stats["data_points"]
        }, broadcast=True)
        
        print(f"Flight stopped. Duration: {duration}, Data points: {flight_stats['data_points']}")

def save_flight(stats, start_time, end_time):
    """Sačuvaj let u JSON fajl - samo statistike"""
    flights_dir = '/home/milaogi/flights'
    os.makedirs(flights_dir, exist_ok=True)

    avg_temp = stats["temp_sum"] / stats["data_points"] if stats["data_points"] > 0 else 0
    
    flight_filename = start_time.strftime('flight_%Y%m%d_%H%M%S.json')
    flight_path = os.path.join(flights_dir, flight_filename)
    
    # Sačuvaj samo korisne statistike
    flight_record = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(), 
        'duration_seconds': (end_time - start_time).total_seconds(),
        'max_altitude': round(stats["max_altitude"], 1),
        'min_altitude': round(stats["min_altitude"], 1),
        'max_climb_rate': round(stats["max_climb_rate"], 1),
        'max_sink_rate': round(stats["max_sink_rate"], 1),
        'altitude_gain': round(stats["max_altitude"] - stats["min_altitude"], 1),
        'avg_temperature': round(avg_temp, 1),
        'data_points': stats["data_points"]
    }
    
    with open(flight_path, 'w') as f:
        json.dump(flight_record, f, indent=2)
    
    print(f"Flight saved to {flight_path}")

def update_flight_stats(data):
    """Ažurira statistike leta"""
    global flight_stats
    
    alt = data["altitude"]
    climb = data["climb_rate"]
    temp = data["temperature"]
    
    flight_stats["max_altitude"] = max(flight_stats["max_altitude"], alt)
    flight_stats["min_altitude"] = min(flight_stats["min_altitude"], alt)
    flight_stats["max_climb_rate"] = max(flight_stats["max_climb_rate"], climb)
    flight_stats["max_sink_rate"] = min(flight_stats["max_sink_rate"], climb)
    flight_stats["data_points"] += 1
    
    # Dodaj temperature tracking
    if "temp_sum" not in flight_stats:
        flight_stats["temp_sum"] = 0
    flight_stats["temp_sum"] += temp

if __name__ == '__main__':
    try:
        print("🌐 Variometer WebSocket server starting on http://192.168.4.1:5000")
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("Shutting down variometer...")
    finally:
        # Cleanup
        if buzzer:
            buzzer.close()
        print("Cleanup completed")