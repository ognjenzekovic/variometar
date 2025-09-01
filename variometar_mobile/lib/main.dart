import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:http/http.dart' as http;

void main() {
  runApp(const VariometerApp());
}

class VariometerApp extends StatelessWidget {
  const VariometerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Variometar',
      theme: ThemeData(
        primarySwatch: Colors.green,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: Color(0xFF1a1a1a),
      ),
      home: const VariometerHomePage(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class VariometerHomePage extends StatefulWidget {
  const VariometerHomePage({super.key});

  @override
  State<VariometerHomePage> createState() => _VariometerHomePageState();
}

class _VariometerHomePageState extends State<VariometerHomePage>
    with TickerProviderStateMixin {
  IO.Socket? socket;

  double temperature = 0.0;
  double pressure = 0.0;
  double altitude = 0.0;
  double climbRate = 0.0;
  String timestamp = '';

  bool isRecording = false;

  bool isAudioEnabled = true;

  List<dynamic> flights = [];

  String get rpiAddress => isHotspotMode ? '192.168.4.1' : '192.168.67.251';
  bool isHotspotMode = true;

  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: Duration(milliseconds: 150),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );

    connectToSocket();
    loadFlights();
    loadAudioStatus();
  }

  void connectToSocket() {
    try {
      socket = IO.io('http://$rpiAddress:5000', <String, dynamic>{
        'transports': ['websocket'],
        'autoConnect': false,
      });

      socket!.connect();

      socket!.on('connect', (_) {
        print('Povezano na RPi5');
        setState(() {});
      });

      socket!.on('disconnect', (_) {
        print('Prekida konekcija sa RPi5');
        setState(() {});
      });

      socket!.on('sensor_data', (data) {
        setState(() {
          temperature = data['temperature'].toDouble();
          pressure = data['pressure'].toDouble();
          altitude = data['altitude'].toDouble();
          climbRate = data['climb_rate'].toDouble();
          timestamp = data['timestamp'];
        });

        // Animacija za climb rate promene
        // if (climbRate.abs() > 0.5) {
        //   _animationController.forward().then((_) {
        //     _animationController.reverse();
        //   });
        // }
      });

      socket!.on('flight_started', (_) {
        setState(() {
          isRecording = true;
        });
      });

      socket!.on('flight_stopped', (data) {
        setState(() {
          isRecording = false;
        });
        loadFlights(); // Osvežava listu letova

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Let završen! Trajanje: ${data['duration']}'),
            backgroundColor: Colors.green,
          ),
        );
      });
    } catch (e) {
      print('Greška pri konekciji: $e');
    }
  }

  Future<void> loadFlights() async {
    try {
      final response =
          await http.get(Uri.parse('http://$rpiAddress:5000/api/flights'));
      if (response.statusCode == 200) {
        setState(() {
          flights = json.decode(response.body);
        });
      }
    } catch (e) {
      print('Greška pri učitavanju letova: $e');
    }
  }

  void startFlight() {
    socket!.emit('start_flight');
  }

  void stopFlight() {
    socket!.emit('stop_flight');
  }

  Future<void> deleteFlight(String filename) async {
    try {
      final response = await http.delete(
        Uri.parse('http://$rpiAddress:5000/api/flight/$filename'),
      );

      if (response.statusCode == 200) {
        final result = json.decode(response.body);
        if (result['success']) {
          loadFlights();
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Let je obrisan')),
          );
        }
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Greška pri brisanju leta')),
      );
    }
  }

  Future<void> loadAudioStatus() async {
    try {
      final response =
          await http.get(Uri.parse('http://$rpiAddress:5000/api/audio'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          isAudioEnabled = data['audio_enabled'] ?? true;
        });
      }
    } catch (e) {
      print('Greška pri učitavanju audio statusa: $e');
    }
  }

  Future<void> toggleAudio(bool enabled) async {
    try {
      final response = await http.post(
        Uri.parse('http://$rpiAddress:5000/api/audio'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'enabled': enabled}),
      );

      if (response.statusCode == 200) {
        setState(() {
          isAudioEnabled = enabled;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(enabled ? 'Audio uključen' : 'Audio isključen'),
            duration: Duration(seconds: 1),
          ),
        );
      }
    } catch (e) {
      print('Greška pri menjanju audio statusa: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Greška pri menjanju audio statusa')),
      );
    }
  }

  Future<void> showFlightDetails(String filename) async {
    try {
      final response = await http.get(
        Uri.parse('http://$rpiAddress:5000/api/flight/$filename'),
      );

      if (response.statusCode == 200) {
        final flight = json.decode(response.body);

        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            backgroundColor: Color(0xFF333333),
            title: Text('Detalji Leta', style: TextStyle(color: Colors.white)),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    'Datum: ${DateTime.parse(flight['start_time']).toLocal().toString().substring(0, 16)}',
                    style: TextStyle(color: Colors.white70)),
                SizedBox(height: 8),
                Text(
                    'Trajanje: ${(flight['duration_seconds'] / 60).round()} min',
                    style: TextStyle(color: Colors.white70)),
                SizedBox(height: 8),
                Text(
                    'Temperatura: ${flight['avg_temperature']?.toStringAsFixed(1) ?? 'N/A'}°C',
                    style: TextStyle(color: Colors.white70)),
                SizedBox(height: 8),
                Text(
                    'Max visina: ${flight['max_altitude']?.toStringAsFixed(1)}m',
                    style: TextStyle(color: Colors.white70)),
                SizedBox(height: 8),
                Text(
                    'Min visina: ${flight['min_altitude']?.toStringAsFixed(1)}m',
                    style: TextStyle(color: Colors.white70)),
                SizedBox(height: 8),
                Text(
                    'Visinska razlika: ${flight['altitude_gain']?.toStringAsFixed(1)}m',
                    style: TextStyle(color: Colors.white70)),
                SizedBox(height: 8),
                Text(
                    'Max penjanje: ${flight['max_climb_rate']?.toStringAsFixed(1)} m/s',
                    style: TextStyle(color: Colors.white70)),
                SizedBox(height: 8),
                Text(
                    'Max spuštanje: ${flight['max_sink_rate']?.toStringAsFixed(1)} m/s',
                    style: TextStyle(color: Colors.white70)),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  showDialog(
                    context: context,
                    builder: (context) => AlertDialog(
                      backgroundColor: Color(0xFF333333),
                      title: Text('Obriši let',
                          style: TextStyle(color: Colors.white)),
                      content: Text(
                          'Da li si siguran da želiš da obrišeš ovaj let?',
                          style: TextStyle(color: Colors.white70)),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: Text('Otkaži'),
                        ),
                        TextButton(
                          onPressed: () {
                            Navigator.of(context).pop();
                            deleteFlight(filename);
                          },
                          child: Text('Obriši',
                              style: TextStyle(color: Colors.red)),
                        ),
                      ],
                    ),
                  );
                },
                child: Text('Obriši', style: TextStyle(color: Colors.red)),
              ),
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text('Zatvori', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Greška pri učitavanju detalja leta')),
      );
    }
  }

  Color getClimbRateColor() {
    if (climbRate > 0.2) return Colors.green;
    if (climbRate < -0.2) return Colors.red;
    return Colors.orange;
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text('Variometar'),
          backgroundColor: Color(0xFF333333),
          bottom: TabBar(
            indicatorColor: Colors.white,
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white70,
            tabs: [
              Tab(text: 'Podaci Uživo'),
              Tab(text: 'Snimljeni Letovi'),
            ],
          ),
          actions: [
            PopupMenuButton<String>(
              onSelected: (value) {
                setState(() {
                  isHotspotMode = value == 'hotspot';
                });
                socket?.disconnect();
                connectToSocket();
                loadFlights();
              },
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'hotspot',
                  child: Text('Hotspot (192.168.4.1)'),
                ),
                PopupMenuItem(
                  value: 'wifi',
                  child: Text('WiFi (192.168.67.251)'),
                ),
              ],
              icon: Icon(isHotspotMode ? Icons.wifi_tethering : Icons.wifi),
            ),
          ],
        ),
        body: TabBarView(
          children: [
            // Live podaci tab
            Column(
              children: [
                Expanded(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Column(
                      children: [
                        // Status konekcije
                        Container(
                          padding: EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: socket?.connected == true
                                ? Colors.green
                                : Colors.red,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text(
                                  socket?.connected == true
                                      ? 'Povezano na $rpiAddress'
                                      : 'Nema konekcije sa $rpiAddress',
                                  style: TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold),
                                ),
                              ),
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    isAudioEnabled
                                        ? Icons.volume_up
                                        : Icons.volume_off,
                                    color: Colors.white,
                                    size: 20,
                                  ),
                                  Switch(
                                    value: isAudioEnabled,
                                    onChanged: socket?.connected == true
                                        ? (value) {
                                            toggleAudio(value);
                                          }
                                        : null,
                                    activeColor: Colors.white,
                                    inactiveThumbColor: Colors.grey,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),

                        SizedBox(height: 20),

                        // Climb Rate - glavni displej
                        Expanded(
                          flex: 2,
                          child: AnimatedBuilder(
                            animation: _scaleAnimation,
                            builder: (context, child) {
                              return Transform.scale(
                                scale: _scaleAnimation.value,
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: Color(0xFF333333),
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  child: Center(
                                    child: Column(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Text(
                                          'Brzina Penjanja/Spuštanja',
                                          style: TextStyle(
                                            color: Colors.white70,
                                            fontSize: 16,
                                          ),
                                        ),
                                        SizedBox(height: 10),
                                        Text(
                                          '${climbRate > 0 ? '+' : ''}${climbRate.toStringAsFixed(1)}',
                                          style: TextStyle(
                                            color: getClimbRateColor(),
                                            fontSize: 48,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        Text(
                                          'm/s',
                                          style: TextStyle(
                                            color: Colors.white70,
                                            fontSize: 18,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),

                        SizedBox(height: 16),

                        // Ostali podaci
                        Expanded(
                          flex: 3,
                          child: Row(
                            children: [
                              Expanded(
                                child: _buildDataCard('Visina',
                                    '${altitude.toStringAsFixed(1)}', 'm'),
                              ),
                              SizedBox(width: 8),
                              Expanded(
                                child: Column(
                                  children: [
                                    Expanded(
                                      child: _buildDataCard(
                                          'Pritisak',
                                          '${pressure.toStringAsFixed(1)}',
                                          'hPa'),
                                    ),
                                    SizedBox(height: 8),
                                    Expanded(
                                      child: _buildDataCard(
                                          'Temperatura',
                                          '${temperature.toStringAsFixed(1)}',
                                          '°C'),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // Kontrole za snimanje
                Container(
                  padding: EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Expanded(
                        child: ElevatedButton(
                          onPressed: isRecording ? null : startFlight,
                          style: ElevatedButton.styleFrom(
                            backgroundColor:
                                isRecording ? Colors.orange : Colors.green,
                            padding: EdgeInsets.symmetric(vertical: 16),
                          ),
                          child: Text(
                            isRecording ? '🔴 SNIMAM...' : '✈️ POKRENI LET',
                            style: TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ),
                      SizedBox(width: 16),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: isRecording ? stopFlight : null,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red,
                            padding: EdgeInsets.symmetric(vertical: 16),
                          ),
                          child: Text(
                            '🛑 ZAVRŠI LET',
                            style: TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Lista letova tab
            RefreshIndicator(
              onRefresh: loadFlights,
              child: flights.isEmpty
                  ? Center(
                      child: Text(
                        'Nema snimljenih letova',
                        style: TextStyle(color: Colors.white70, fontSize: 16),
                      ),
                    )
                  : ListView.builder(
                      padding: EdgeInsets.all(16),
                      itemCount: flights.length,
                      itemBuilder: (context, index) {
                        final filename = flights[index];
                        final parts =
                            filename.replaceAll('.json', '').split('_');
                        final date = parts.length > 1 ? parts[1] : '';
                        final time = parts.length > 2 ? parts[2] : '';

                        String formattedDate = '';
                        String formattedTime = '';

                        if (date.length == 8) {
                          formattedDate =
                              '${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)}';
                        }
                        if (time.length == 6) {
                          formattedTime =
                              '${time.substring(0, 2)}:${time.substring(2, 4)}:${time.substring(4, 6)}';
                        }

                        return Card(
                          color: Color(0xFF444444),
                          margin: EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            title: Text(
                              '$formattedDate $formattedTime',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold),
                            ),
                            subtitle: Text(
                              'Klikni za detalje',
                              style: TextStyle(color: Colors.white70),
                            ),
                            onTap: () => showFlightDetails(filename),
                            trailing: Icon(Icons.chevron_right,
                                color: Colors.white70),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDataCard(String title, String value, String unit) {
    return Container(
      decoration: BoxDecoration(
        color: Color(0xFF333333),
        borderRadius: BorderRadius.circular(12),
      ),
      padding: EdgeInsets.all(16),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            title,
            style: TextStyle(color: Colors.white70, fontSize: 14),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: Colors.green,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            unit,
            style: TextStyle(color: Colors.white70, fontSize: 12),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    socket?.disconnect();
    _animationController.dispose();
    super.dispose();
  }
}
