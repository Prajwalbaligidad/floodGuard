"""
Autonomous Weather AI Agent (BDI Architecture & Inter-Agent Signaling)
Autonomous Multi-Agent AI System for Disaster Prediction

Agent Mind:
- Goal: Early detection of convective storms, barometric depressions, and cloudbursts.
- Beliefs: Atmospheric sensor state + historical precipitation patterns.
- Desires: Minimize warning latency and notify downstream hydraulic agents.
- Intentions: Broadcast storm surges and trigger meteorological emergency protocols.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_agent import BaseAutonomousAIAgent, InterAgentMessageBus, AgentMessage


class WeatherAgent(BaseAutonomousAIAgent):
    """Autonomous AI Agent specializing in meteorological flood hazard detection."""

    def __init__(self, agent_id: str = "AUTONOMOUS_WEATHER_AI_AGENT"):
        super().__init__(
            agent_id=agent_id,
            agent_type="WEATHER",
            primary_goal="EARLY_DETECTION_OF_CONVECTIVE_STORMS_AND_CLOUDBURSTS"
        )

    def deliberate_bdi_cycle(
        self,
        obs: Dict[str, Any],
        ml_pred: Optional[Dict[str, Any]],
        bus: InterAgentMessageBus
    ) -> Dict[str, Any]:
        hourly_rain = float(obs.get("hourly_rainfall_mm", 0.0))
        cum_6h = float(obs.get("cumulative_6h_rainfall_mm", 0.0))
        cum_24h = float(obs.get("cumulative_24h_rainfall_mm", 0.0))
        wind_gusts = float(obs.get("wind_gusts_kmh", 0.0))
        wind_speed = float(obs.get("wind_speed_kmh", 0.0))
        pressure = float(obs.get("atmospheric_pressure_hpa", 1010.0))
        pressure_drop_3h = float(obs.get("pressure_drop_3h_hpa", 0.0))
        humidity = float(obs.get("relative_humidity_pct", 50.0))
        intensity_cat = obs.get("rainfall_intensity_category", "No Rain")
        ts = str(obs.get("timestamp", ""))

        # 1. Update Beliefs
        critical_flags: List[str] = []
        if hourly_rain >= 64.4:
            critical_flags.append("EXTREMELY_HEAVY_RAINFALL")
        elif hourly_rain >= 35.5:
            critical_flags.append("VERY_HEAVY_RAINFALL")
        elif hourly_rain >= 15.5:
            critical_flags.append("HEAVY_RAINFALL")

        if cum_24h >= 150.0:
            critical_flags.append("EXTREME_24H_ACCUMULATION")
        elif cum_24h >= 80.0:
            critical_flags.append("HIGH_24H_ACCUMULATION")

        if cum_6h >= 60.0:
            critical_flags.append("SURGE_6H_PRECIPITATION")

        if pressure_drop_3h >= 5.0:
            critical_flags.append("RAPID_BAROMETRIC_DROP")

        if wind_gusts >= 55.0:
            critical_flags.append("HIGH_WIND_SQUALL")

        self.beliefs["critical_flags"] = critical_flags
        self.beliefs["barometric_depression"] = pressure_drop_3h >= 4.0

        # 2. Evaluate Desires
        self.desires = [
            "MAINTAIN_ATMOSPHERIC_SITUATIONAL_AWARENESS",
            "PREVENT_SURPRISE_FLASH_FLOOD_SURGE"
        ]

        # 3. Deliberate Risk & Intentions
        if hourly_rain >= 50.0 or cum_24h >= 150.0:
            risk_score = 0.92 + min(0.07, (hourly_rain / 100.0) * 0.05)
            risk_level = "CRITICAL"
        elif hourly_rain >= 20.0 or cum_24h >= 60.0:
            risk_score = 0.60 + min(0.25, (cum_24h / 150.0) * 0.25)
            risk_level = "HIGH"
        elif hourly_rain >= 5.0 or cum_24h >= 15.0:
            risk_score = 0.25 + min(0.25, (cum_24h / 60.0) * 0.25)
            risk_level = "MODERATE"
        else:
            # Dynamic continuous baseline directly driven by Open-Meteo live parameters
            r_factor = (cum_24h / 120.0) * 0.40 + (hourly_rain / 30.0) * 0.25
            hum_factor = (humidity / 100.0) * 0.18
            gust_factor = (wind_gusts / 50.0) * 0.10
            press_factor = min(0.08, max(0.0, (1014.0 - pressure) / 25.0) * 0.08)
            
            continuous_score = min(0.95, r_factor + hum_factor + gust_factor + press_factor + 0.02)
            risk_score = round(max(0.02, continuous_score), 3)
            risk_level = "MODERATE" if risk_score >= 0.18 else "LOW"

        dispatched_count = 0
        self.intentions = []

        if risk_level == "CRITICAL":
            operational_state = "EMERGENCY_MOBILIZATION"
            action_trigger = "TRIGGER_RED_DELUGE_ALERT"
            self.intentions = [
                "INTENTION_ISSUE_METEOROLOGICAL_RED_ALERT",
                "INTENTION_WARN_DOWNSTREAM_FLOOD_AGENT_OF_INCOMING_SURGE"
            ]

            # Autonomous Inter-Agent Signaling: Alert peer agents across the message bus
            bus.broadcast(AgentMessage(
                message_id=f"MSG_W_{ts}",
                sender_agent="WEATHER",
                recipient_agent="FLOOD",
                performative="WARN",
                timestamp=ts,
                subject="UPSTREAM_CLOUDBURST_PRECIPITATION_SURGE",
                content={
                    "hourly_rainfall_mm": hourly_rain,
                    "cum_24h_mm": cum_24h,
                    "expected_hydrograph_surge_hours": 4
                }
            ))
            dispatched_count += 1
        elif risk_level == "HIGH":
            operational_state = "ACTIVE_WATCH"
            action_trigger = "ISSUE_ORANGE_PRECIPITATION_ADVISORY"
            self.intentions = ["INTENTION_INTENSIFY_RADAR_AND_STORM_TRACKING"]
        elif risk_level == "MODERATE":
            operational_state = "ELEVATED_AWARENESS"
            action_trigger = "MAINTAIN_YELLOW_WEATHER_WATCH"
            self.intentions = ["INTENTION_MONITOR_BAROMETRIC_PRESSURE_TREND"]
        else:
            operational_state = "ROUTINE_MONITORING"
            action_trigger = "STANDARD_METEOROLOGICAL_MONITORING"
            self.intentions = ["INTENTION_LOG_BASELINE_ATMOSPHERIC_METRICS"]

        key_indicators = {
            "hourly_rainfall_mm": hourly_rain,
            "cumulative_6h_rainfall_mm": cum_6h,
            "cumulative_24h_rainfall_mm": cum_24h,
            "rainfall_intensity_category": intensity_cat,
            "wind_speed_kmh": wind_speed,
            "wind_gusts_kmh": wind_gusts,
            "atmospheric_pressure_hpa": pressure,
            "pressure_drop_3h_hpa": pressure_drop_3h,
            "relative_humidity_pct": humidity
        }

        return {
            "operational_state": operational_state,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": 0.94,
            "critical_flags": critical_flags,
            "action_trigger": action_trigger,
            "dispatched_messages_count": dispatched_count,
            "key_indicators": key_indicators
        }
