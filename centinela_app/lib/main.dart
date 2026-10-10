import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:ota_update/ota_update.dart';

void main() {
  runApp(const CentinelaApp());
}

class CentinelaApp extends StatelessWidget {
  const CentinelaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Centinela Pro',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF131722), // Fondo TradingView
        cardColor: const Color(0xFF1E222D),
        primaryColor: const Color(0xFF2962FF),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF2962FF),
          secondary: Color(0xFF089981),
          surface: Color(0xFF1E222D),
          error: Color(0xFFF23645),
        ),
      ),
      home: const MainNavigationScreen(),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  final String baseUrl = "https://centinela-pro-dopr.onrender.com";
  final String versionApp = "1.0.1"; // Versión sincronizada

  Map<String, dynamic>? datosMercado;
  List<dynamic> todasLasEntradas = [];
  bool cargando = true;
  String? mensajeError;

  @override
  void initState() {
    super.initState();
    cargarDatos();
    verificarActualizacion();
  }

  Future<void> verificarActualizacion() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/version')).timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final versionServidor = data['version'];
        final urlDescarga = data['url_descarga'];
        final novedades = data['novedades'] ?? 'Mejoras y señales de Crypto.';

        if (versionServidor != null && versionServidor != versionApp && urlDescarga != null) {
          if (!mounted) return;
          _mostrarModalActualizacion(versionServidor, urlDescarga, novedades);
        }
      }
    } catch (_) {}
  }

  void _mostrarModalActualizacion(String nuevaVersion, String url, String novedades) {
    String estadoDescarga = "";
    double progreso = 0.0;
    bool descargando = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) {
          return AlertDialog(
            backgroundColor: const Color(0xFF1E222D),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: const BorderSide(color: Color(0xFF2962FF), width: 1.2),
            ),
            title: Row(
              children: [
                const Icon(Icons.system_update_rounded, color: Color(0xFF2962FF)),
                const SizedBox(width: 10),
                Text(
                  "Actualización v$nuevaVersion",
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "Hay una nueva versión disponible para Centinela Pro:",
                  style: TextStyle(color: Color(0xFFD1D4DC), fontSize: 13),
                ),
                const SizedBox(height: 8),
                Text(
                  "• $novedades",
                  style: const TextStyle(color: Color(0xFF787B86), fontSize: 12),
                ),
                const SizedBox(height: 16),
                if (descargando) ...[
                  LinearProgressIndicator(
                    value: progreso > 0 ? progreso : null,
                    color: const Color(0xFF2962FF),
                    backgroundColor: const Color(0xFF131722),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    estadoDescarga,
                    style: const TextStyle(color: Color(0xFF58A6FF), fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ],
              ],
            ),
            actions: [
              if (!descargando)
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2962FF),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: () {
                    setModalState(() {
                      descargando = true;
                      estadoDescarga = "Iniciando descarga...";
                    });

                    try {
                      OtaUpdate().execute(url).listen(
                        (OtaEvent event) {
                          setModalState(() {
                            if (event.status == OtaStatus.DOWNLOADING) {
                              estadoDescarga = "Descargando: ${event.value}%";
                              progreso = (double.tryParse(event.value ?? '0') ?? 0) / 100.0;
                            } else if (event.status == OtaStatus.INSTALLING) {
                              estadoDescarga = "Abriendo instalador...";
                            } else {
                              estadoDescarga = "Preparando actualización...";
                            }
                          });
                        },
                        onError: (e) {
                          setModalState(() {
                            descargando = false;
                            estadoDescarga = "Error en la descarga.";
                          });
                        },
                      );
                    } catch (e) {
                      setModalState(() {
                        descargando = false;
                        estadoDescarga = "Error de conexión.";
                      });
                    }
                  },
                  child: const Text(
                    "Actualizar Ahora",
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Future<void> cargarDatos() async {
    setState(() {
      cargando = true;
      mensajeError = null;
    });

    try {
      final resMercado = await http.get(Uri.parse('$baseUrl/mercado')).timeout(const Duration(seconds: 40));
      final resEntradas = await http.get(Uri.parse('$baseUrl/entradas')).timeout(const Duration(seconds: 40));

      if (resMercado.statusCode == 200 && resEntradas.statusCode == 200) {
        final decodedEntradas = json.decode(resEntradas.body);
        setState(() {
          datosMercado = json.decode(resMercado.body);
          todasLasEntradas = decodedEntradas is Map && decodedEntradas.containsKey('entradas')
              ? decodedEntradas['entradas']
              : (decodedEntradas is List ? decodedEntradas : []);
          cargando = false;
        });
      } else {
        setState(() {
          mensajeError = 'Error del servidor (${resMercado.statusCode})';
          cargando = false;
        });
      }
    } on TimeoutException {
      setState(() {
        mensajeError = 'El servidor tardó en responder. Desliza para reintentar.';
        cargando = false;
      });
    } catch (e) {
      setState(() {
        mensajeError = 'Error de conexión:\n$e';
        cargando = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF131722),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF2962FF).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF2962FF), width: 1.2),
              ),
              child: const Icon(Icons.shield_rounded, color: Color(0xFF2962FF), size: 20),
            ),
            const SizedBox(width: 10),
            const Text(
              "CENTINELA",
              style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: 1.2, fontSize: 18),
            ),
            Container(
              margin: const EdgeInsets.only(left: 6),
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF2962FF),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                "PRO",
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Color(0xFF787B86)),
            onPressed: cargarDatos,
          ),
        ],
      ),
      body: RefreshIndicator(
        color: const Color(0xFF2962FF),
        backgroundColor: const Color(0xFF1E222D),
        onRefresh: cargarDatos,
        child: cargando
            ? const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CircularProgressIndicator(color: Color(0xFF2962FF)),
                    SizedBox(height: 16),
                    Text(
                      "Escaneando pares de Binance y mercado...",
                      style: TextStyle(color: Color(0xFF787B86), fontSize: 13),
                    ),
                  ],
                ),
              )
            : mensajeError != null
                ? ListView(
                    children: [
                      SizedBox(height: MediaQuery.of(context).size.height * 0.25),
                      Center(
                        child: Column(
                          children: [
                            const Icon(Icons.wifi_off_rounded, color: Color(0xFFF23645), size: 48),
                            const SizedBox(height: 14),
                            Text(
                              mensajeError!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: Color(0xFFD1D4DC), fontSize: 14),
                            ),
                            const SizedBox(height: 20),
                            ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2962FF)),
                              onPressed: cargarDatos,
                              icon: const Icon(Icons.replay_rounded),
                              label: const Text("Reintentar"),
                            ),
                          ],
                        ),
                      ),
                    ],
                  )
                : ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    children: [
                      if (datosMercado != null) _buildMarketHeader(datosMercado!),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            "SEÑALES DEL DÍA (MÁX. 10)",
                            style: TextStyle(
                              color: Color(0xFF787B86),
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 0.8,
                            ),
                          ),
                          Text(
                            "${todasLasEntradas.length} activas",
                            style: const TextStyle(color: Color(0xFF2962FF), fontSize: 11, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      todasLasEntradas.isEmpty
                          ? const Padding(
                              padding: EdgeInsets.symmetric(vertical: 50),
                              child: Center(
                                child: Text(
                                  "No hay señales abiertas en este ciclo.",
                                  style: TextStyle(color: Color(0xFF787B86)),
                                ),
                              ),
                            )
                          : ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: todasLasEntradas.length,
                              itemBuilder: (context, index) {
                                return _buildTelegramStyleCard(todasLasEntradas[index], index + 1);
                              },
                            ),
                    ],
                  ),
      ),
    );
  }

  Widget _buildMarketHeader(Map<String, dynamic> datos) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E222D),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF2A2E39)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(color: Color(0xFF089981), shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Text(
                datos['macro_detalle'] ?? "Límite: 10/día",
                style: const TextStyle(color: Color(0xFFD1D4DC), fontWeight: FontWeight.bold, fontSize: 12),
              ),
            ],
          ),
          Text(
            "Sentimiento: ${datos['sentimiento_fear_greed'] ?? 'ESTABLE'}",
            style: const TextStyle(color: Color(0xFF787B86), fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildTelegramStyleCard(dynamic item, int posicion) {
    final ticker = item['ticker'] ?? 'N/A';
    final empresa = item['nombre_empresa'] ?? ticker;
    final dinamica = item['dinamica'] ?? 'Swing';
    final precio = item['precio']?.toString() ?? '0.00';
    final rango = item['rango_entrada'] ?? '\$$precio';
    final rsi = item['rsi']?.toString() ?? '--';
    final descuento = item['descuento']?.toString() ?? '0';
    final tp = item['take_profit']?.toString() ?? '0.00';
    final sl = item['stop_loss']?.toString() ?? '0.00';
    final pctTp = item['pct_tp']?.toString() ?? '0.0';
    final pctSl = item['pct_sl']?.toString() ?? '0.0';
    final fecha = item['fecha_deteccion'] ?? 'Hoy';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E222D),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF2A2E39)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 16,
                    backgroundColor: const Color(0xFF2962FF).withOpacity(0.18),
                    child: Text(
                      "#$posicion",
                      style: const TextStyle(color: Color(0xFF2962FF), fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        ticker,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      Text(
                        empresa,
                        style: const TextStyle(color: Color(0xFF787B86), fontSize: 11),
                      ),
                    ],
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF089981).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  dinamica.toString().toUpperCase(),
                  style: const TextStyle(color: Color(0xFF089981), fontWeight: FontWeight.bold, fontSize: 9),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(color: Color(0xFF2A2E39), height: 1),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _metricCol("Zona de Compra", rango, Colors.white),
              _metricCol("Precio Actual", "\$$precio", const Color(0xFF58A6FF)),
              _metricCol("RSI / Caída", "$rsi (-$descuento%)", const Color(0xFFD1D4DC)),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF131722),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF2A2E39)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Row(
                  children: [
                    const Icon(Icons.gps_fixed, color: Color(0xFF089981), size: 16),
                    const SizedBox(width: 6),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("Take-Profit (2:1)", style: TextStyle(color: Color(0xFF787B86), fontSize: 9)),
                        Text("\$$tp (+$pctTp%)", style: const TextStyle(color: Color(0xFF089981), fontWeight: FontWeight.bold, fontSize: 12)),
                      ],
                    ),
                  ],
                ),
                Container(height: 24, width: 1, color: const Color(0xFF2A2E39)),
                Row(
                  children: [
                    const Icon(Icons.shield_outlined, color: Color(0xFFF23645), size: 16),
                    const SizedBox(width: 6),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("Stop-Loss (ATR)", style: TextStyle(color: Color(0xFF787B86), fontSize: 9)),
                        Text("\$$sl (-$pctSl%)", style: const TextStyle(color: Color(0xFFF23645), fontWeight: FontWeight.bold, fontSize: 12)),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("Fuente: Binance Spot", style: TextStyle(color: Color(0xFF787B86), fontSize: 11)),
              Text("🕒 $fecha", style: const TextStyle(color: Color(0xFF787B86), fontSize: 10)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _metricCol(String titulo, String valor, Color colorValor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(titulo, style: const TextStyle(color: Color(0xFF787B86), fontSize: 10)),
        const SizedBox(height: 2),
        Text(valor, style: TextStyle(color: colorValor, fontWeight: FontWeight.bold, fontSize: 13)),
      ],
    );
  }
}