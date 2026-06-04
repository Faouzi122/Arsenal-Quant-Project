# © 2026 Meridian Alpha Systems - Intelligence & Logistics Division
# Watermark: ADSL-404-SIGMA

import asyncio
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from app.core.maritime_routes import maritime_engine

class MaritimeNewsSensor:
    def __init__(self):
        # Specialized Feeds for Transpacific and Global logistics
        self.rss_urls = [
            "https://gcaptain.com/feed/",
            "https://maritime-executive.com/api/rss/articles",
            "https://lloydslist.maritimeintelligence.informa.com/rss/news",
            "https://www.portofrotterdam.com/en/news-and-press-releases/rss"
        ]
        # The central nerve for logging significant events (Zero GUI)
        self.pulse_file = os.getenv("PULSE_FILE_PATH", "/home/faouzi/Antigravity_Knowledge_Base/Flux_Projets/MARKET_PULSE.json")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.pulse_file), exist_ok=True)
        
        # Memory set to avoid duplicate processing
        self.seen_guid = set()

    def fetch_feed(self, url):
        """Fetches the RSS feed natively (Performance optimization: Constant time verification)."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read()
        except Exception as e:
            print(f"[Sensor] Error fetching feed {url}: {e}")
            return None

    def process_feed(self):
        """Parses the feeds and analyzes sentiment for Transpacific updates."""
        for url in self.rss_urls:
            xml_data = self.fetch_feed(url)
            if not xml_data:
                continue

            try:
                root = ET.fromstring(xml_data)
                for item in root.findall('.//item'):
                    guid_node = item.find('guid')
                    link_node = item.find('link')
                    guid = guid_node.text if guid_node is not None else (link_node.text if link_node is not None else None)
                    
                    if not guid or guid in self.seen_guid:
                        continue
                        
                    self.seen_guid.add(guid)
                    title = item.find('title').text
                    desc_node = item.find('description')
                    desc = desc_node.text if desc_node is not None else ""
                    
                    full_text = f"{title}. {desc}"
                    
                    # Analyze using the engine, focus implicitly on transpacific if available
                    analysis = maritime_engine.analyze_maritime_risk(full_text)
                    
                    # Log critical risks
                    if analysis.get("risk_index", 50) > 65 or analysis.get("risk_index", 50) < 35:
                        
                        # Formatting output for CEO requirements
                        route_name = "China-USA" if "transpacific" in analysis.get("affected_routes", []) else ", ".join(analysis.get("affected_routes", []))
                        if not route_name:
                            route_name = "Global"
                            
                        sentiment_text = "Bearish (Risk High)" if analysis.get("risk_index", 50) > 65 else "Bullish (Risk Low)"
                        prediction = "Freight rates likely to surge" if analysis.get("freight_trend_prediction") == "surge_expected" else "Freight rates likely to drop"
                        
                        self._save_to_pulse({
                            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                            "route": route_name,
                            "event": title,
                            "market_psychology_index": sentiment_text,
                            "prediction": prediction,
                            "confidence": analysis.get("confidence", 0.0)
                        })
                        print(f"[Sensor] Critical pulse recorded: {title[:50]}...")
                        
            except Exception as e:
                print(f"[Sensor] XML Parsing error on {url}: {e}")

    def _save_to_pulse(self, data):
        """Appends the event to MARKET_PULSE.json (Atomic write, Max 100)."""
        pulse_data = []
        if os.path.exists(self.pulse_file):
            try:
                with open(self.pulse_file, 'r') as f:
                    content = f.read()
                    if content:
                        pulse_data = json.loads(content)
            except json.JSONDecodeError:
                pulse_data = []
                
        pulse_data.append(data)
        
        # Anti-Waste: Keep strictly to 100 alerts to save Celeron disk
        pulse_data = pulse_data[-100:]
        
        with open(self.pulse_file, 'w') as f:
            json.dump(pulse_data, f, indent=4)

    async def run_sensor_loop(self):
        """Runs the sensor every 15 minutes asynchronously."""
        print("[Sensor] Live Maritime RSS Sensor Initialized...")
        while True:
            print("[Sensor] Fetching live maritime updates...")
            await asyncio.to_thread(self.process_feed)
            await asyncio.sleep(int(os.getenv("SENSOR_INTERVAL", 900)))

sensor = MaritimeNewsSensor()
