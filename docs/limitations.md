# Technical Limitations & Future Horizons

## 1. Technical Limitations
1. **Third-Party Telemetry Dependency**: The model relies on Open-Meteo REST APIs for live precipitation telemetry. In the event of upstream API downtime, the system automatically degrades gracefully to 30-minute cached data or historical climatological baselines.
2. **Hydrological River Gauge Feeds**: River water level telemetry is currently derived from precipitation and static river proximity baselines (`distance_to_river_m`, `elevation_m`). Direct real-time physical sensor telemetry integration from the Irrigation Department will further improve lead-time precision.
3. **SMS / WhatsApp Gateway Billing**: External SMS/WhatsApp delivery channels require active provider API credentials and credits. In demonstration environments, the notification engine logs masked delivery dispatches and executes in-app web broadcasts cleanly.

---

## 2. Future Scope & Roadmap
1. **IoT River Water Level Sensor Networks**: Direct LoRaWAN/GSM physical stream-gauge sensor node integration.
2. **High-Resolution Satellite Radar (Sentinel-1 SAR)**: Ingest Synthetic Aperture Radar imagery for real-time flood inundation mapping.
3. **Edge AI Microcontrollers**: Deploy quantized micro-ML models directly on local river monitoring hardware for offline autonomous alert triggers.
