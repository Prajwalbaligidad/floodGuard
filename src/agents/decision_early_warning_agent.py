"""
Layer 5: Decision and Early Warning Agent
Autonomous Multi-Agent AI System for Disaster Prediction

Responsibilities:
- Ingests Fused Risk Assessment Packet from Layer 4.
- Produces:
  1. Risk Maps (Console ASCII visual map + Interactive HTML Geo-Map with coordinates, inundation buffers, and evacuation routes).
  2. Standardized Multi-Tier Alerts (Red Deluge Evacuation, Orange Warning, Yellow Advisory, Green Routine).
  3. Prioritized Recommended Actions (Tactical 0-1h, 1-3h, 3-12h operational guidance for NDRF, Water Resources, APDCL).
  4. Structured Reports for Human Approval (Incident Action Plan with Human-in-the-Loop verification checklist and audit logs).
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.llm.local_llm_engine import LocalLLMEngine
from src.services.evacuation_routing_engine import EvacuationRoutingEngine
from .risk_assessment_fusion_agent import FusedRiskAssessmentPacket

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "analysis_output"
MAPS_DIR = OUTPUT_DIR / "risk_maps"
REPORTS_DIR = OUTPUT_DIR / "incident_reports"
MAPS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / ".env")

# Map API Key configuration (Optional: CARTO / Stadia Maps)
# You can paste your API key here or in your .env file as STADIA_API_KEY=... or CARTO_API_KEY=...
MAP_API_KEY = os.getenv("STADIA_API_KEY") or os.getenv("CARTO_API_KEY") or ""


class EarlyWarningDecisionPacket(BaseModel):
    """Standardized output packet from the Decision and Early Warning Agent."""
    decision_id: str
    assessment_id: str
    station_name: str
    district: str
    river_name: str
    timestamp: str
    
    # Alerting Outputs
    alert_code: str
    alert_level_display: str
    siren_command: str
    public_broadcast_sms: str
    
    # Decision & Operations
    recommended_tactical_actions: List[Dict[str, Any]]
    human_approval_checklist: List[Dict[str, Any]]
    incident_commander_guidance: str
    
    # Generated Artifacts
    ascii_risk_map: str
    html_risk_map_path: str
    incident_report_md_path: str
    incident_report_json_path: str


class DecisionEarlyWarningAgent:
    """
    Autonomous AI Agent that translates fused risk assessments into early warnings,
    spatial risk maps, tactical emergency actions, and human approval reports.
    """

    def __init__(self, agent_id: str = "AUTONOMOUS_DECISION_EARLY_WARNING_AGENT"):
        self.agent_id = agent_id
        self.agent_type = "DECISION_AND_EARLY_WARNING"
        self.primary_goal = "PRODUCE_RISK_MAPS_ALERTS_ACTIONS_AND_HUMAN_APPROVAL_REPORTS"
        self.llm_engine = LocalLLMEngine()

    def generate_ascii_risk_map(
        self,
        assessment: FusedRiskAssessmentPacket,
        station_profile: Dict[str, Any]
    ) -> str:
        """Generates an informative text-based spatial risk map for console/terminal visualization."""
        stn = assessment.station_name
        river = assessment.river_name
        risk = assessment.composite_risk_score
        severity = assessment.overall_severity_tier
        
        # Color badge
        color_badges = {
            "CRITICAL": "[!!! RED CRITICAL INUNDATION ZONE !!!]",
            "HIGH":     "[!! ORANGE HIGH SURGE ZONE !!]",
            "MODERATE": "[! YELLOW ELEVATED MOISTURE ZONE !]",
            "LOW":      "[* GREEN SAFE / ROUTINE FLOW *]"
        }
        badge = color_badges.get(severity, "[NORMAL]")

        # Progress bar representing danger proximity
        risk_pct = int(risk * 100)
        filled = int(risk * 25)
        bar = "#" * filled + "-" * (25 - filled)

        # ASCII spatial diagram
        ascii_map = f"""
+-----------------------------------------------------------------------------------------+
| SPATIAL RISK MAP: {stn.upper():<25} River: {river.upper():<15} {badge}
+-----------------------------------------------------------------------------------------+
| Risk Level Bar: [{bar}] {risk_pct}% Risk ({severity})
| Coordinates: Lat {station_profile.get('latitude', 26.15):.4f} N | Lon {station_profile.get('longitude', 91.73):.4f} E | Elevation: {station_profile.get('elevation_m', 55.0):.1f}m
|
|   ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
|  [UPSTREAM CATCHMENT] >>>>>>> River Flow Direction >>>>>>> [DOWNSTREAM FLOODPLAIN]
|   ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
|
|         [North Embankment Dykes]
|   ===========================================
|      ^ Sluice Gates: {'[SHUT & SEALED]' if severity == 'CRITICAL' else '[OPEN / REGULATED]'}
|      ^ Primary Monitoring Node: {stn}
|      ^ Water Level: {assessment.flood_risk*50.5:.2f}m | Breach Status: {'BREACHED (+)' if assessment.hard_safety_override_triggered else 'CONTAINED (-)'}
|   ===========================================
|         [South Inhabited Urban / Agrarian Wards]
|
|   Vulnerable Infrastructure Sectors Under Surveillance:
"""
        for idx, loc in enumerate(assessment.identified_vulnerable_locations):
            ascii_map += f"|     {idx+1}. {loc}\n"
        ascii_map += "+-----------------------------------------------------------------------------------------+"
        return ascii_map

    def generate_html_risk_map(
        self,
        assessment: FusedRiskAssessmentPacket,
        station_profile: Dict[str, Any]
    ) -> Path:
        """
        Generates a standalone, beautiful HTML interactive risk map with Leaflet.js
        reflecting the 3 strict operational states:
        1. LOW: Green area circle. NO evacuation searched or allocated.
        2. MODERATE: Yellow circle. Nearest local evacuation spot and safe route shown.
        3. HIGH / CRITICAL: Red alert circle. Primary camp allocated; if and only if
           primary camp is in the flooded region, diverted to alternative safe haven.
        """
        lat = station_profile.get("latitude", 26.1445)
        lon = station_profile.get("longitude", 91.7362)
        stn = assessment.station_name
        district = assessment.district
        river = assessment.river_name
        severity = assessment.overall_severity_tier
        risk = assessment.composite_risk_score
        
        # Color coding for leaflet
        color_hex = {
            "CRITICAL": "#dc2626", # Red
            "HIGH":     "#ea580c", # Orange
            "MODERATE": "#ca8a04", # Yellow
            "LOW":      "#16a34a"  # Green
        }.get(severity, "#16a34a")

        radius_m = {
            "CRITICAL": 3500,
            "HIGH":     2000,
            "MODERATE": 800,
            "LOW":      500
        }.get(severity, 500)

        # Autonomous Evacuation Re-Assessment
        routing_engine = EvacuationRoutingEngine()
        reroute_info = routing_engine.reassess_safety_and_route(
            origin_lat=lat,
            origin_lon=lon,
            origin_elevation=station_profile.get("elevation_m", 50.0),
            severity_tier=severity,
            composite_risk=risk,
            flood_confirmed=assessment.flood_occurrence_confirmed,
            water_level_m=station_profile.get("water_level_m", station_profile.get("elevation_m", 50.0) + (risk * 3.8)),
            danger_level_m=station_profile.get("danger_level_m", station_profile.get("elevation_m", 50.0) + 3.5),
            district=district,
            location_name=stn,
            river_name=river
        )

        river_gauge = reroute_info.get("river_gauge", {})
        river_lat = river_gauge.get("latitude", round(lat + 0.015, 5))
        river_lon = river_gauge.get("longitude", round(lon + 0.005, 5))
        elevation_m = station_profile.get("elevation_m", 50.0)
        water_level_m = station_profile.get("water_level_m", elevation_m + 1.2)
        warning_level_m = station_profile.get("warning_level_m", elevation_m + 2.6)
        danger_level_m = station_profile.get("danger_level_m", elevation_m + 3.5)

        show_evac = reroute_info.get("show_evacuation", False)
        is_diverted = reroute_info.get("reroute_triggered", False)
        active_shelter = reroute_info.get("active_safe_shelter")

        if not show_evac:
            standby = active_shelter or reroute_info.get("secondary_shelter") or {}
            standby_name = standby.get("name", "Regional Civil Defense Sanctuary")
            standby_dist = standby.get("distance_km", 2.5)
            evac_badge_text = "STATUS: NORMAL & SECURE (NO EVACUATION REQUIRED)"
            evac_badge_color = "#16a34a"
            info_shelter_str = f"Standby Haven: {standby_name} ({standby_dist} km)"
            legend_shelter_lines = "<div><span style='color:#10b981;'>🟢</span> <b>Designated Haven</b> (Standby)</div><div><span style='color:#16a34a;'>●</span> <b>Normal Flow:</b> Safe Baseline</div>"
        elif severity == "MODERATE":
            evac_badge_text = "EVACUATION: NEAREST LOCAL RELIEF SPOT ALLOCATED"
            evac_badge_color = "#ca8a04"
            info_shelter_str = f"{active_shelter['name']} ({active_shelter['distance_km']} km)"
            legend_shelter_lines = "<div><span style='color:#ca8a04;'>🟡</span> <b>Nearest Local Shelter</b> (Safe Inland)</div><div><span style='color:#ca8a04;'>━━</span> Safe Transit Corridor</div>"
        elif is_diverted:
            evac_badge_text = "EVACUATION: 🚨 PRIMARY CAMP FLOODED -> DIVERTED TO ALTERNATIVE HAVEN"
            evac_badge_color = "#dc2626"
            elev_diff = active_shelter.get('elevation_delta_m', 0)
            elev_label = f"+{elev_diff}m elevated" if elev_diff > 0 else "Reinforced High Plinth"
            info_shelter_str = f"{active_shelter['name']} ({elev_label})"
            legend_shelter_lines = "<div><span style='color:#dc2626;'>⚠️</span> <b>Compromised Primary Camp</b> (Flooded)</div><div><span style='color:#10b981;'>🟢</span> <b>Alternative Safe Haven</b> (High Ground)</div><div><span style='color:#dc2626;'>╌╌</span> Aborted Inundated Route</div><div><span style='color:#10b981;'>━━</span> Diverted Safe Corridor</div>"
        else:
            evac_badge_text = "EVACUATION: PRIMARY RELIEF CAMP ACTIVE (OUTSIDE FLOOD ZONE)"
            evac_badge_color = "#16a34a"
            info_shelter_str = f"{active_shelter['name']} ({active_shelter['distance_km']} km)"
            legend_shelter_lines = "<div><span style='color:#10b981;'>🟢</span> <b>Primary Camp</b> (Safe & Active)</div><div><span style='color:#10b981;'>━━</span> Designated Safe Route</div>"

        # Generate JavaScript code for shelters and corridors
        shelter_js_code = ""
        if not show_evac:
            standby = active_shelter or reroute_info.get("secondary_shelter") or {}
            if standby and "latitude" in standby:
                shelter_js_code = f"""
        // [LOW RISK - DESIGNATED STANDBY HAVEN]
        var standbyMarker = L.circleMarker([{standby['latitude']}, {standby['longitude']}], {{
            color: '#10b981',
            fillColor: '#059669',
            fillOpacity: 0.88,
            radius: 13,
            weight: 2
        }}).addTo(map).bindPopup("<b style='color:#10b981;'>🟢 DESIGNATED EMERGENCY SAFE HAVEN (STANDBY)</b><br><b>{standby['name']}</b><br><b>Facility:</b> {standby.get('facility_type', 'Civil Defense Sanctuary')}<br><b>Distance:</b> {standby.get('distance_km', 2.0)} km inland<br><b>Capacity:</b> {standby.get('capacity', 20000):,} people<br><b>Elevation:</b> {standby.get('elevation_m', 50.0)}m ASL<br><b>Status:</b> CIVIL DEFENSE STANDBY &bull; Verified Dry Ground");
        """
            else:
                shelter_js_code = 'console.log("Area is safe (LOW risk).");'
        elif severity == "MODERATE":
            near = active_shelter
            route_json = json.dumps(reroute_info.get("active_route_coords", []))
            shelter_js_code = f"""
        // [MODERATE RISK - YELLOW ALERT]
        // Designate Nearest Local Evacuation Spot (Community Relief Center) with safe corridor
        var nearestMarker = L.circleMarker([{near['latitude']}, {near['longitude']}], {{
            color: '#ca8a04',
            fillColor: '#eab308',
            fillOpacity: 0.95,
            radius: 13,
            weight: 3
        }}).addTo(map).bindPopup("<b style='color:#ca8a04;'>🟡 NEAREST LOCAL EVACUATION SPOT</b><br><b>{near['name']}</b><br><b>Facility:</b> {near.get('facility_type', 'Community Relief Center')}<br><b>Distance:</b> {near['distance_km']} km<br><b>Capacity:</b> {near['capacity']:,} people<br><b>Status:</b> ACCESSIBLE & VERIFIED SAFE");

        var moderateRoute = L.polyline({route_json}, {{
            color: '#ca8a04',
            weight: 5,
            opacity: 0.95
        }}).addTo(map).bindPopup("<b>🟡 SAFE ROUTE TO NEAREST LOCAL RELIEF SPOT</b><br>Direct access route to {near['name']}.");
        """
        else: # HIGH or CRITICAL
            primary = reroute_info.get("primary_shelter", {})
            secondary = reroute_info.get("secondary_shelter", {})
            sec_delta = secondary.get('elevation_delta_m', 0)
            sec_elev_txt = f"+{sec_delta}m elevated" if sec_delta > 0 else "Reinforced High Plinth"
            
            if not is_diverted:
                # Primary camp is outside the flood perimeter: ROUTE DIRECTLY TO PRIMARY CAMP!
                p_route_json = json.dumps(reroute_info.get("active_route_coords", []))
                shelter_js_code = f"""
        // [HIGH / CRITICAL RISK - PRIMARY CAMP SAFE OUTSIDE FLOOD ZONE]
        var primaryMarker = L.circleMarker([{primary['latitude']}, {primary['longitude']}], {{
            color: '#10b981',
            fillColor: '#059669',
            fillOpacity: 0.95,
            radius: 14,
            weight: 3
        }}).addTo(map).bindPopup("<b style='color:#10b981;'>🟢 PRIMARY EVACUATION CAMP (OUTSIDE FLOOD ZONE)</b><br><b>{primary['name']}</b><br><b>Distance:</b> {primary['distance_km']} km<br><b>Capacity:</b> {primary['capacity']:,} evacuees<br><b>Status:</b> ACTIVE & SAFE TO OCCUPY");

        var activeRoute = L.polyline({p_route_json}, {{
            color: '#10b981',
            weight: 6,
            opacity: 0.95
        }}).addTo(map).bindPopup("<b style='color:#10b981;'>✅ DESIGNATED SAFE ROUTE TO PRIMARY CAMP</b><br>High-ground route verified clear of flood inundation.");
        """
            else:
                # Primary camp IS IN FLOODED REGION -> Diverted to Alternative Safe Haven!
                aborted_json = json.dumps(reroute_info.get("aborted_route_coords", []))
                diverted_json = json.dumps(reroute_info.get("diverted_safe_route_coords", []))
                shelter_js_code = f"""
        // [CRITICAL RISK - PRIMARY CAMP INUNDATED -> DIVERSION TO ALTERNATIVE SAFE HAVEN]
        // 1. Primary Camp: Marked COMPROMISED & INUNDATED
        var compromisedMarker = L.circleMarker([{primary['latitude']}, {primary['longitude']}], {{
            color: '#dc2626',
            fillColor: '#b91c1c',
            fillOpacity: 0.9,
            radius: 12,
            weight: 3
        }}).addTo(map).bindPopup("<b style='color:#dc2626;'>⚠️ PRIMARY CAMP: COMPROMISED & FLOODED</b><br><b>{primary['name']}</b><br>Status: INUNDATION CUTOFF DETECTED<br>Reason: Flood perimeter ({radius_m}m) covers access path.<br><b style='color:#dc2626;'>DO NOT PROCEED HERE! DIVERT TO HIGH GROUND!</b>");

        // 2. Aborted Inundated Route (Red Dashed)
        var abortedRoute = L.polyline({aborted_json}, {{
            color: '#dc2626',
            weight: 4,
            dashArray: '6, 8',
            opacity: 0.85
        }}).addTo(map).bindPopup("<b style='color:#dc2626;'>❌ ABORTED ROUTE - INUNDATED</b><br>Submerged under flood surge. Impassable for civilian transit.");

        // 3. Alternative Elevated Safe Haven (University / Civic Center / Arena)
        var altMarker = L.circleMarker([{secondary['latitude']}, {secondary['longitude']}], {{
            color: '#10b981',
            fillColor: '#059669',
            fillOpacity: 0.95,
            radius: 14,
            weight: 3
        }}).addTo(map).bindPopup("<b style='color:#10b981;'>🟢 ALTERNATIVE HIGH-GROUND SAFE HAVEN</b><br><b>{secondary['name']}</b><br><b>Facility Type:</b> {secondary.get('facility_type', 'Highland Safe Haven')}<br><b>Elevation:</b> {secondary['elevation_m']}m ({sec_elev_txt})<br><b>Capacity:</b> {secondary['capacity']:,} evacuees<br><b>Status:</b> ACTIVE & VERIFIED SECURE HIGH GROUND");

        // 4. Diverted Safe High-Ground Route (Solid Green)
        var safeRoute = L.polyline({diverted_json}, {{
            color: '#10b981',
            weight: 6,
            opacity: 0.95
        }}).addTo(map).bindPopup("<b style='color:#10b981;'>✅ DESIGNATED SAFE DIVERTED CORRIDOR</b><br>High-ground route leading away from river inundation to <b>{secondary['name']}</b>.");
        """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Disaster Risk & Dynamic Evacuation Map - {stn}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; }}
        #header {{ background: #1e293b; padding: 14px 24px; border-bottom: 2px solid #334155; display: flex; justify-content: space-between; align-items: center; }}
        #header h1 {{ margin: 0; font-size: 20px; color: #38bdf8; }}
        .badge-container {{ display: flex; gap: 10px; }}
        .badge {{ padding: 6px 14px; border-radius: 9999px; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; }}
        #risk-badge {{ background: {color_hex}; color: white; }}
        #evac-badge {{ background: {evac_badge_color}; color: white; }}
        #map {{ height: calc(100vh - 140px); width: 100%; }}
        #info-panel {{ background: #1e293b; padding: 12px 24px; font-size: 13px; color: #cbd5e1; display: flex; gap: 24px; border-top: 1px solid #334155; flex-wrap: wrap; }}
        .badge-tag {{ font-weight: bold; color: #f8fafc; }}
    </style>
</head>
<body>
    <div id="header">
        <div>
            <h1>DYNAMIC RISK & EVACUATION SAFETY MAP &bull; {stn.upper()}</h1>
            <small style="color: #94a3b8;">River {river} Basin &bull; District: {district} &bull; Timestamp: {assessment.timestamp}</small>
        </div>
        <div class="badge-container">
            <div id="risk-badge" class="badge">{severity} RISK ({int(risk*100)}%)</div>
            <div id="evac-badge" class="badge">{evac_badge_text}</div>
        </div>
    </div>
    <div id="map"></div>
    <div id="info-panel">
        <div><span class="badge-tag">Lead Time:</span> {assessment.estimated_lead_time}</div>
        <div><span class="badge-tag">Evacuation Allocation:</span> {info_shelter_str}</div>
        <div><span class="badge-tag">Re-Assessment Directive:</span> {reroute_info['tactical_rerouting_instruction'][:90]}...</div>
    </div>
    <script>
        var map = L.map('map').setView([{lat}, {lon}], 13);

        // 100% Free Public Map Tile Servers (NO API KEY required, NO watermark)
        // 1. Esri World Street & Hydrology Map
        var streetLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
            attribution: 'Tiles &copy; Esri, DeLorme, NAVTEQ | Autonomous Multi-Agent AI System'
        }});

        // 2. Esri High-Resolution World Satellite Imagery
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
            attribution: 'Tiles &copy; Esri, DigitalGlobe, GeoEye, Earthstar Geographics'
        }});

        // 3. Esri National Geographic Topographic Map
        var topoLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 16,
            attribution: 'Tiles &copy; National Geographic, Esri'
        }});

        // Base Layer Catalog
        var baseMaps = {{
            "🗺️ Street & River Network (Esri)": streetLayer,
            "🛰️ Spaceborne Satellite (Esri)": satelliteLayer,
            "⛰️ Topographic Elevation (Esri)": topoLayer
        }};

        var userApiKey = "{MAP_API_KEY}".trim();
        if (userApiKey) {{
            var stadiaSmooth = L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth/{{z}}/{{y}}/{{x}}{{r}}.png?api_key=' + userApiKey, {{
                maxZoom: 20,
                attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a>'
            }});
            var stadiaDark = L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{{z}}/{{y}}/{{x}}{{r}}.png?api_key=' + userApiKey, {{
                maxZoom: 20,
                attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a>'
            }});
            var cartoVoyager = L.tileLayer('https://tiles.stadiamaps.com/tiles/carto_voyager/{{z}}/{{y}}/{{x}}{{r}}.png?api_key=' + userApiKey, {{
                maxZoom: 20,
                attribution: '&copy; CARTO, &copy; Stadia Maps'
            }});

            baseMaps["🧭 CARTO / Stadia Smooth"] = stadiaSmooth;
            baseMaps["🌃 CARTO / Stadia Dark"] = stadiaDark;
            baseMaps["🗺️ CARTO Voyager"] = cartoVoyager;
            stadiaSmooth.addTo(map);
        }} else {{
            streetLayer.addTo(map);
        }}

        // Layer Switcher Control (Top Right)
        L.control.layers(baseMaps).addTo(map);

        // 1. Civic Population & Urban Surveillance Center Marker (Inhabited City Center)
        var civicIcon = L.divIcon({{
            className: 'civic-marker-icon',
            html: '<div style="background:#2563eb; color:white; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-size:18px; border:3px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.5); cursor:pointer;">🏢</div>',
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        }});

        var civicMarker = L.marker([{lat}, {lon}], {{ icon: civicIcon }}).addTo(map)
            .bindPopup(
                "<div style='min-width:260px; font-size:13px; font-family:sans-serif;'>" +
                "<div style='background:#1e3a8a; color:white; padding:6px 10px; border-radius:4px; font-weight:bold; margin-bottom:8px; display:flex; align-items:center; gap:6px;'>" +
                "<span>🏢</span> CIVIC POPULATION & MONITORING CENTER</div>" +
                "<b>Location:</b> {stn} City Urban Center ({district})<br>" +
                "<b>Type:</b> Inhabited Residential & Municipal Zone<br>" +
                "<b>Ground Elevation:</b> {elevation_m:.1f} meters ASL<br>" +
                "<b>Surveillance Basin:</b> River {river}<br>" +
                "<hr style='margin:6px 0; border:0; border-top:1px solid #cbd5e1;'>" +
                "<b>Operational Risk Status:</b> <span style='font-weight:bold; color:{color_hex};'>{severity} RISK ({int(risk*100)}%)</span><br>" +
                "<b>Event State:</b> {assessment.flood_event_status}<br>" +
                "<b>Estimated Lead Time:</b> {assessment.estimated_lead_time}<br>" +
                "</div>"
            ).openPopup();

        // 2. Hydrological River Hazard Monitoring Gauge Marker (River Channel Section)
        var riverIcon = L.divIcon({{
            className: 'river-marker-icon',
            html: '<div style="background:#0284c7; color:white; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-size:18px; border:3px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.5); cursor:pointer;">🌊</div>',
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        }});

        var riverGaugeMarker = L.marker([{river_lat}, {river_lon}], {{ icon: riverIcon }}).addTo(map)
            .bindPopup(
                "<div style='min-width:270px; font-size:13px; font-family:sans-serif;'>" +
                "<div style='background:#0369a1; color:white; padding:6px 10px; border-radius:4px; font-weight:bold; margin-bottom:8px; display:flex; align-items:center; gap:6px;'>" +
                "<span>🌊</span> HYDROLOGICAL RIVER HAZARD GAUGE</div>" +
                "<b>Monitoring Station:</b> {river_gauge.get('name', f'River {river} Stage Gauge')}<br>" +
                "<b>River System:</b> River {river}<br>" +
                "<b>Hydrological Section:</b> {river_gauge.get('bank_desc', 'River Channel Embankment')}<br>" +
                "<hr style='margin:6px 0; border:0; border-top:1px solid #cbd5e1;'>" +
                "<b>Current Stage Level:</b> {water_level_m:.2f} m<br>" +
                "<b>Warning Stage:</b> {warning_level_m:.2f} m | <b>Danger Stage:</b> {danger_level_m:.2f} m<br>" +
                "<b>Embankment State:</b> <span style='font-weight:bold; color:{color_hex};'>{'NOMINAL / SAFE FLOW' if severity == 'LOW' else ('ELEVATED WATCH FLOW' if severity == 'MODERATE' else 'HIGH DELUGE / SPILLOVER ALERT')}</span><br>" +
                "</div>"
            );

        // Area Risk Perimeter Circle (Surveillance Radius around Civic Node)
        var areaCircle = L.circle([{lat}, {lon}], {{
            color: '{color_hex}',
            fillColor: '{color_hex}',
            fillOpacity: 0.28,
            radius: {radius_m}
        }}).addTo(map).bindPopup("<b>{'🟢 SAFE ZONE: ROUTINE MONITORING' if severity == 'LOW' else ('🟡 MODERATE FLOOD WATCH ZONE' if severity == 'MODERATE' else '🔴 RED ALERT INUNDATION PERIMETER')}</b><br>Radius: {radius_m} meters<br>Severity: {severity}");

        {shelter_js_code}

        // 3. Interactive Map Legend (Bottom Right)
        var legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'info legend');
            div.style.background = '#1e293b';
            div.style.padding = '12px 16px';
            div.style.borderRadius = '8px';
            div.style.color = '#f8fafc';
            div.style.fontSize = '12px';
            div.style.lineHeight = '19px';
            div.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
            div.style.border = '1px solid #334155';
            div.innerHTML =
                "<div style='font-weight:bold; margin-bottom:8px; color:#38bdf8; font-size:13px;'>SPATIAL MAP LEGEND</div>" +
                "<div>🏢 <b>Civic Population Center</b> (Inhabited City)</div>" +
                "<div>🌊 <b>Hydrological River Gauge</b> (River Embankment)</div>" +
                "{legend_shelter_lines}" +
                "<div style='margin-top:6px; border-top:1px solid #334155; padding-top:6px;'><b>Perimeter:</b> {radius_m}m Surveillance Buffer</div>";
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
"""
        clean_ts = assessment.timestamp.replace(" ", "_").replace(":", "-")
        map_filename = f"risk_map_{assessment.station_id}_{clean_ts}.html"
        map_path = MAPS_DIR / map_filename
        with open(map_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return map_path

    def generate_incident_report(
        self,
        assessment: FusedRiskAssessmentPacket,
        decision_data: Dict[str, Any]
    ) -> Dict[str, Path]:
        """
        Generates formal Incident Action Plan (IAP) reports formatted for Human-in-the-Loop
        incident commanders and disaster management authorities (NDRF / DDMA).
        """
        stn = assessment.station_name
        district = assessment.district
        river = assessment.river_name
        clean_ts = assessment.timestamp.replace(" ", "_").replace(":", "-")
        report_base = f"incident_report_{assessment.station_id}_{clean_ts}"

        # Markdown Report with Human Sign-off Checkboxes
        md_content = f"""# DISASTER INCIDENT ACTION PLAN (IAP) & SITUATION REPORT
**Authority:** Autonomous Multi-Agent AI Early Warning System  
**Station:** {stn} ({assessment.station_id})  
**River Basin:** {river} Corridor | **District:** {district}, Assam  
**Timestamp:** {assessment.timestamp}  
**Report ID:** IAP-{assessment.assessment_id}  

---

## 1. EXECUTIVE SITUATION SUMMARY
* **Operational Status:** **{decision_data['alert_level_display']}**
* **Flood Occurrence Confirmed:** **{'YES (CONFIRMED FLOOD EVENT)' if assessment.flood_occurrence_confirmed else 'NO (BELOW CRITICAL THRESHOLD)'}**
* **Flood Event State:** `{assessment.flood_event_status}`
* **Multi-Modal Risk Score:** **{assessment.composite_risk_score:.3f} / 1.000** (Certainty: **{int(assessment.composite_confidence * 100)}%**)
* **Estimated Lead Time:** **{assessment.estimated_lead_time}**
* **Primary Threat Driver:** `{assessment.primary_hazard_driver}`

### Authoritative Assessment Verdict:
> "{assessment.headline_verdict}"

---

## 2. SPECIALIST MULTI-AGENT TELEMETRY LINEAGE
| Agent Specialist | Domain Risk | Operational Posture | Primary Critical Flags |
| :--- | :---: | :---: | :--- |
| **Weather Agent** | `{assessment.weather_risk:.3f}` | Atmospheric Monitor | Rain surge, barometric pressure rate |
| **Flood Agent** | `{assessment.flood_risk:.3f}` | Riverine Hydraulics | Water level, danger buffer, rise rate |
| **Terrain Agent** | `{assessment.terrain_risk:.3f}` | Runoff Infiltration | Soil saturation, runoff coefficient |
| **Satellite Agent** | `{assessment.satellite_risk:.3f}` | Spaceborne Radar | Sentinel-1 SAR backscatter & NDWI |

---

## 3. IDENTIFIED VULNERABLE LOCATIONS & SECTORS
The following localized residential, industrial, and infrastructure assets are under direct hazard:
"""
        for idx, loc in enumerate(assessment.identified_vulnerable_locations):
            md_content += f"{idx+1}. **{loc}**\n"

        md_content += f"""
---

## 4. PUBLIC EARLY WARNING BROADCAST
* **Siren Command Directive:** `{decision_data['siren_command']}`
* **Cell-Broadcast SMS Payload:**
> "{decision_data['public_broadcast_sms']}"

---

## 5. TACTICAL RECOMMENDED ACTIONS
"""
        for act in decision_data["recommended_tactical_actions"]:
            md_content += f"* **[{act['priority']}] {act['category']}**: {act['action']} *(Agency: `{act['designated_agency']}`)*\n"

        md_content += f"""
---

## 6. HUMAN-IN-THE-LOOP COMMAND APPROVAL CHECKLIST
*Per institutional disaster protocol, autonomous recommendations require formal Human Incident Commander verification before lethal or resource-intensive executive execution.*

"""
        for chk in decision_data["human_approval_checklist"]:
            md_content += f"- [ ] **{chk['checkpoint']}**  \n  *Responsible Official:* `{chk['sign_off_authority']}` | *Status:* `{chk['status']}`\n\n"

        md_content += f"""
---
**Incident Commander Signature:** ___________________________  
**Date & Time of Authorization:** ___________________________  
*(Archived automatically to system audit repository for post-disaster forensic review)*
"""
        md_path = REPORTS_DIR / f"{report_base}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # JSON Machine-Readable Payload
        json_payload = {
            "report_metadata": {
                "report_id": f"IAP-{assessment.assessment_id}",
                "generated_at": datetime.now().isoformat(),
                "station_name": stn,
                "district": district,
                "river": river,
                "timestamp": assessment.timestamp
            },
            "risk_assessment": assessment.model_dump(),
            "decision_and_early_warning": decision_data
        }
        json_path = REPORTS_DIR / f"{report_base}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)

        return {"md": md_path, "json": json_path}

    def process_decision_cycle(
        self,
        assessment: FusedRiskAssessmentPacket,
        station_profile: Dict[str, Any]
    ) -> EarlyWarningDecisionPacket:
        """Executes the full Decision & Early Warning synthesis."""
        # 1. LLM Decision Reasoning
        decision_data = self.llm_engine.reason_decisions_and_warnings(
            risk_assessment=assessment.model_dump(),
            station_profile=station_profile
        )

        # 1b. Dynamic Shelter Safety Re-assessment & Rerouting Directive
        routing_engine = EvacuationRoutingEngine()
        reroute_info = routing_engine.reassess_safety_and_route(
            origin_lat=station_profile.get("latitude", 26.1445),
            origin_lon=station_profile.get("longitude", 91.7362),
            origin_elevation=station_profile.get("elevation_m", 50.0),
            severity_tier=assessment.overall_severity_tier,
            composite_risk=assessment.composite_risk_score,
            flood_confirmed=assessment.flood_occurrence_confirmed,
            water_level_m=station_profile.get("water_level_m", station_profile.get("elevation_m", 50.0) + (assessment.composite_risk_score * 3.8)),
            danger_level_m=station_profile.get("danger_level_m", station_profile.get("elevation_m", 50.0) + 3.5),
            district=station_profile.get("district", assessment.district),
            location_name=station_profile.get("station_name", assessment.station_name),
            river_name=assessment.river_name
        )

        # Update public broadcast SMS and tactical actions based on strict 3-tier severity
        severity = assessment.overall_severity_tier
        if severity == "LOW":
            decision_data["public_broadcast_sms"] = (
                f"[ALL CLEAR] River {assessment.river_name} discharge and weather telemetry "
                f"are nominal at {assessment.station_name} in {assessment.district}. Routine conditions prevail. No evacuation required or allocated."
            )
        elif severity == "MODERATE":
            nearest = reroute_info.get("active_safe_shelter") or {}
            near_name = nearest.get("name", "Local Relief Center")
            near_dist = nearest.get("distance_km", 1.0)
            decision_data["public_broadcast_sms"] = (
                f"[YELLOW FLOOD ADVISORY] Elevated water levels and drainage pressure in {assessment.district}. "
                f"Nearest designated evacuation spot: {near_name} ({near_dist} km). "
                f"Safe transit corridors are open. Low-lying area residents monitor local bulletins."
            )
        else: # HIGH or CRITICAL
            if reroute_info.get("reroute_triggered", False):
                primary_name = reroute_info.get("primary_shelter", {}).get("name", "Primary Camp")
                alt_shelter = reroute_info.get("secondary_shelter", {})
                alt_name = alt_shelter.get("name", "Alternative Safe Haven")
                alt_dist = alt_shelter.get("distance_km", 3.5)
                alt_tier = alt_shelter.get("tier", "Elevated Safe Haven")
                decision_data["public_broadcast_sms"] = (
                    f"[URGENT ROUTE DIVERSION - RED ALERT] Primary Evacuation Camp ({primary_name}) is INUNDATED by expanding floodwaters! "
                    f"DO NOT PROCEED TOWARDS LOWLANDS. All evacuees must IMMEDIATELY DIVERT to Alternative High-Ground Safe Haven: "
                    f"{alt_name} ({alt_tier}, Distance: {alt_dist} km). Move to high ground immediately!"
                )
                decision_data["recommended_tactical_actions"].insert(0, {
                    "priority": "P0_IMMEDIATE (0-15 Mins)",
                    "category": "DYNAMIC_EVACUATION_REROUTING",
                    "action": (
                        f"Seal off inundated Primary Camp access road. "
                        f"Direct all citizen evacuation convoys along elevated bypass routes to {alt_name}."
                    ),
                    "designated_agency": "Traffic Police & SDRF Rapid Response"
                })
            else:
                primary_shelter = reroute_info.get("primary_shelter", {})
                primary_name = primary_shelter.get("name", "District Primary Relief Camp")
                primary_dist = primary_shelter.get("distance_km", 1.5)
                decision_data["public_broadcast_sms"] = (
                    f"[RED FLOOD ALERT] Severe flood risk along River {assessment.river_name} in {assessment.district}! "
                    f"Mandatory evacuation ordered. Proceed immediately to PRIMARY EVACUATION CAMP: "
                    f"{primary_name} (Distance: {primary_dist} km). Route is verified safe and outside flood perimeter."
                )

        # 2. Generate Spatial Risk Maps (ASCII & Interactive HTML)
        ascii_map = self.generate_ascii_risk_map(assessment, station_profile)
        html_map_path = self.generate_html_risk_map(assessment, station_profile)

        # 3. Generate Human Approval Incident Action Plans (Markdown & JSON)
        report_paths = self.generate_incident_report(assessment, decision_data)

        return EarlyWarningDecisionPacket(
            decision_id=f"DEC_{assessment.assessment_id}",
            assessment_id=assessment.assessment_id,
            station_name=assessment.station_name,
            district=assessment.district,
            river_name=assessment.river_name,
            timestamp=assessment.timestamp,
            alert_code=decision_data["alert_code"],
            alert_level_display=decision_data["alert_level_display"],
            siren_command=decision_data["siren_command"],
            public_broadcast_sms=decision_data["public_broadcast_sms"],
            recommended_tactical_actions=decision_data["recommended_tactical_actions"],
            human_approval_checklist=decision_data["human_approval_checklist"],
            incident_commander_guidance=decision_data["incident_commander_guidance"],
            ascii_risk_map=ascii_map,
            html_risk_map_path=str(html_map_path),
            incident_report_md_path=str(report_paths["md"]),
            incident_report_json_path=str(report_paths["json"])
        )
