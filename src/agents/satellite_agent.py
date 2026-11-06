"""
Autonomous Satellite AI Agent (BDI Architecture & Inter-Agent Signaling)
Autonomous Multi-Agent AI System for Disaster Prediction

Agent Mind:
- Goal: Maintain ground truth spaceborne observability and provide radar flood verification.
- Beliefs: Optical NDWI, cloud occlusion fraction, Sentinel-1 SAR radar backscatter, surface water extent.
- Desires: Overcome atmospheric cloud blindness and confirm real-time surface flood spread.
- Intentions: Autonomously swap sensor modes to SAR C-band and broadcast ground-truth verification.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_agent import BaseAutonomousAIAgent, InterAgentMessageBus, AgentMessage


class SatelliteAgent(BaseAutonomousAIAgent):
    """Autonomous AI Agent specializing in spaceborne remote sensing flood verification."""

    def __init__(self, agent_id: str = "AUTONOMOUS_SATELLITE_AI_AGENT"):
        super().__init__(
            agent_id=agent_id,
            agent_type="SATELLITE",
            primary_goal="MAINTAIN_GROUND_TRUTH_OBSERVABILITY_DESPITE_ATMOSPHERIC_OCCLUSION"
        )

    def deliberate_bdi_cycle(
        self,
        obs: Dict[str, Any],
        ml_pred: Optional[Dict[str, Any]],
        bus: InterAgentMessageBus
    ) -> Dict[str, Any]:
        cloud_pct = float(obs.get("satellite_cloud_cover_pct", 20.0))
        optical_vis = bool(obs.get("optical_visibility_flag", True))
        ndwi = float(obs.get("ndwi_index", -0.1))
        water_extent = float(obs.get("surface_water_extent_km2", 10.0))
        extent_change_pct = float(obs.get("water_extent_change_pct", 0.0))
        sar_db = float(obs.get("sar_backscatter_db", -12.0))
        sat_confidence = float(obs.get("satellite_flood_confidence_pct", 50.0))
        ts = str(obs.get("timestamp", ""))

        critical_flags: List[str] = []
        
        # Autonomous Sensor Handoff Behavior
        if cloud_pct >= 65.0:
            critical_flags.append("OPTICAL_SENSOR_CLOUD_OCCLUDED")
            sensor_mode = "SAR_RADAR_PRIMARY"
            confidence = max(0.75, sat_confidence / 100.0)
            sensor_adaptation = "ADAPTIVE_SWAP_TO_SAR_C_BAND"
        else:
            sensor_mode = "OPTICAL_SAR_FUSION"
            confidence = max(0.85, sat_confidence / 100.0)
            sensor_adaptation = "DUAL_SENSOR_FUSION_NOMINAL"

        if extent_change_pct >= 75.0:
            critical_flags.append("EXTREME_SURFACE_WATER_EXPANSION")
        elif extent_change_pct >= 35.0:
            critical_flags.append("SIGNIFICANT_FLOOD_SPREAD")

        if ndwi >= 0.35:
            critical_flags.append("HIGH_NDWI_OPEN_STANDING_WATER")
        elif ndwi >= 0.15:
            critical_flags.append("ELEVATED_SURFACE_MOISTURE_SIGNATURE")

        if sar_db <= -18.0:
            critical_flags.append("SAR_SPECULAR_FLOOD_SIGNATURE")

        self.beliefs["cloud_occluded"] = cloud_pct >= 65.0
        self.beliefs["sar_verified"] = sar_db <= -18.0
        self.beliefs["sensor_mode"] = sensor_mode

        # 2. Evaluate Desires
        self.desires = [
            "MAINTAIN_OBSERVATIONAL_CONTINUITY",
            "PREVENT_FALSE_CLEAR_DUE_TO_CLOUD_BLINDNESS"
        ]

        # 3. Deliberate Risk & Intentions
        if sar_db <= -18.0 or extent_change_pct >= 50.0:
            risk_score = 0.90
            risk_level = "CRITICAL"
        elif sar_db <= -14.0 or extent_change_pct >= 20.0:
            risk_score = 0.55
            risk_level = "HIGH"
        else:
            # Normal baseline SAR backscatter sensitivity (-7 to -13 dB)
            sar_factor = max(0.0, min(0.08, abs(sar_db + 7.0) / 10.0 * 0.08))
            ndwi_factor = max(0.0, (ndwi + 0.2) / 0.5) * 0.04
            continuous_score = max(0.015, sar_factor + ndwi_factor + 0.01)
            risk_score = max(continuous_score, ml_pred["ml_risk_score"]) if ml_pred and ml_pred["ml_predicted_level"] != "LOW" else continuous_score
            risk_level = "MODERATE" if risk_score >= 0.18 else "LOW"

        # Autonomous Spaceborne Ground Truth Veto
        if sar_db <= -22.0 and extent_change_pct >= 80.0:
            risk_level = "CRITICAL"
            risk_score = max(risk_score, 0.95)

        dispatched_count = 0
        self.intentions = []

        if risk_level == "CRITICAL":
            operational_state = "EMERGENCY_MOBILIZATION"
            action_trigger = "DISPATCH_SAR_FLOODPLAIN_INUNDATION_VECTORS"
            self.intentions = [
                "INTENTION_EXPORT_VECTOR_FLOOD_POLYGONS",
                "INTENTION_BROADCAST_RADAR_CONFIRMATION_TO_ALL_AGENTS"
            ]

            # Broadcast Ground Truth Confirmation to all peer agents
            bus.broadcast(AgentMessage(
                message_id=f"MSG_S_{ts}",
                sender_agent="SATELLITE",
                recipient_agent="BROADCAST",
                performative="CONFIRM",
                timestamp=ts,
                subject="RADAR_CONFIRMED_GROUND_INUNDATION",
                content={
                    "sensor_mode": sensor_mode,
                    "water_extent_change_pct": extent_change_pct,
                    "sar_backscatter_db": sar_db,
                    "flood_confidence_pct": sat_confidence
                }
            ))
            dispatched_count += 1
        elif risk_level == "HIGH":
            operational_state = "ACTIVE_WATCH"
            action_trigger = "ALERT_EMERGENCY_UNITS_TO_INUNDATED_ACCESS_ROADS"
            self.intentions = ["INTENTION_SCHEDULE_NEXT_ORBITAL_PASS"]
        elif risk_level == "MODERATE":
            operational_state = "ELEVATED_AWARENESS"
            action_trigger = "TASK_HIGH_FREQUENCY_SATELLITE_CONSTELLATION"
            self.intentions = ["INTENTION_REQUEST_COMMERCIAL_SAR_TASKING"]
        else:
            operational_state = "ROUTINE_MONITORING"
            action_trigger = "CONFIRM_NORMAL_SEASONAL_WATER_CHANNELS"
            self.intentions = ["INTENTION_UPDATE_BASELINE_SURFACE_WATER_MASK"]

        key_indicators = {
            "sensor_mode": sensor_mode,
            "cloud_cover_pct": cloud_pct,
            "optical_visibility_flag": optical_vis,
            "ndwi_index": ndwi,
            "surface_water_extent_km2": water_extent,
            "water_extent_change_pct": extent_change_pct,
            "sar_backscatter_db": sar_db,
            "satellite_flood_confidence_pct": sat_confidence
        }

        return {
            "operational_state": operational_state,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": confidence,
            "critical_flags": critical_flags,
            "action_trigger": action_trigger,
            "dispatched_messages_count": dispatched_count,
            "key_indicators": key_indicators
        }
