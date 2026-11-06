"""
Autonomous Terrain AI Agent (BDI Architecture & Inter-Agent Signaling)
Autonomous Multi-Agent AI System for Disaster Prediction

Agent Mind:
- Goal: Identify geomorphic runoff accumulation corridors and mitigate soil saturation overflow.
- Beliefs: Landscape slope, soil permeability, land cover imperviousness, TWI, dynamic rainfall load.
- Desires: Prevent low-slope water ponding and channel overland flash runoff safely.
- Intentions: Command municipal corridor clearance and notify flood defense agents.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_agent import BaseAutonomousAIAgent, InterAgentMessageBus, AgentMessage


class TerrainAgent(BaseAutonomousAIAgent):
    """Autonomous AI Agent specializing in geomorphological flood susceptibility and runoff dynamics."""

    def __init__(self, agent_id: str = "AUTONOMOUS_TERRAIN_AI_AGENT"):
        super().__init__(
            agent_id=agent_id,
            agent_type="TERRAIN",
            primary_goal="IDENTIFY_GEOMORPHIC_RUNOFF_ACCUMULATION_CORRIDORS"
        )

    def deliberate_bdi_cycle(
        self,
        obs: Dict[str, Any],
        ml_pred: Optional[Dict[str, Any]],
        bus: InterAgentMessageBus
    ) -> Dict[str, Any]:
        slope = float(obs.get("slope_deg", 2.0))
        elevation = float(obs.get("elevation_m", 50.0))
        soil = obs.get("soil_type", "Loam")
        infilt_cap = float(obs.get("infiltration_capacity_mmh", 10.0))
        land_cover = obs.get("land_cover_class", "Mixed")
        runoff_c = float(obs.get("runoff_coefficient", 0.50))
        twi = float(obs.get("topographic_wetness_index", 10.0))
        surge_index = float(obs.get("effective_runoff_surge_index", 0.0))
        cum_24h_rain = float(obs.get("cumulative_24h_rainfall_mm", 0.0))
        ts = str(obs.get("timestamp", ""))

        # 1. Update Beliefs
        critical_flags: List[str] = []
        if slope < 1.0:
            critical_flags.append("LOW_SLOPE_WATER_PONDING")
        elif slope >= 10.0:
            critical_flags.append("STEEP_FOOTHILL_RUNOFF_VELOCITY")

        if runoff_c >= 0.70:
            critical_flags.append("HIGH_RUNOFF_IMPERVIOUS_SURFACE")

        if infilt_cap <= 6.0:
            critical_flags.append("LOW_INFILTRATION_HEAVY_SOIL")

        if surge_index >= 2.0 or (cum_24h_rain >= 80.0 and infilt_cap <= 8.0):
            critical_flags.append("SOIL_SATURATION_EXCESS_RUNOFF")

        if twi >= 12.5 and cum_24h_rain >= 15.0:
            critical_flags.append("HIGH_TOPOGRAPHIC_WETNESS_DEPRESSION")

        self.beliefs["critical_flags"] = critical_flags
        self.beliefs["saturation_excess"] = surge_index >= 2.0

        # 2. Evaluate Desires
        self.desires = [
            "PREVENT_URBAN_PONDING_PARALYSIS",
            "SECURE_NATURAL_CONVERGENCE_CORRIDORS"
        ]

        # 3. Deliberate Risk & Intentions
        if surge_index >= 2.0 or (cum_24h_rain >= 80.0 and infilt_cap <= 6.0):
            risk_score = 0.88
            risk_level = "CRITICAL"
        elif surge_index >= 1.0 or (cum_24h_rain >= 40.0 and slope < 2.0):
            risk_score = 0.55
            risk_level = "HIGH"
        else:
            # Low elevation (< 30m) delta/coastal terrain has poor gravity outflow
            elev_factor = max(0.0, min(0.12, (120.0 - min(120.0, elevation)) / 120.0 * 0.12))
            slope_factor = max(0.0, min(0.08, (5.0 - min(5.0, slope)) / 5.0 * 0.08))
            twi_factor = min(0.05, (twi / 15.0) * 0.05)
            
            continuous_score = max(0.02, elev_factor + slope_factor + twi_factor + 0.01)
            risk_score = max(continuous_score, ml_pred["ml_risk_score"]) if ml_pred and ml_pred["ml_predicted_level"] != "LOW" else continuous_score
            risk_level = "MODERATE" if risk_score >= 0.18 else "LOW"
            if risk_level == "LOW":
                critical_flags = []
                self.beliefs["critical_flags"] = []

        dispatched_count = 0
        self.intentions = []

        if risk_level in ["CRITICAL", "HIGH"]:
            operational_state = "EMERGENCY_MOBILIZATION" if risk_level == "CRITICAL" else "ACTIVE_WATCH"
            action_trigger = "ENFORCE_STORMWATER_CORRIDOR_CLEARANCE"
            self.intentions = [
                "INTENTION_ISSUE_CLEARANCE_ORDER_FOR_LOW_LYING_HOLLOWS",
                "INTENTION_NOTIFY_FLOOD_AGENT_OF_HIGH_OVERLAND_RUNOFF"
            ]

            # Broadcast Runoff Advisory to Flood Agent
            bus.broadcast(AgentMessage(
                message_id=f"MSG_T_{ts}",
                sender_agent="TERRAIN",
                recipient_agent="FLOOD",
                performative="INFORM",
                timestamp=ts,
                subject="OVERLAND_RUNOFF_SATURATION_SURGE",
                content={
                    "slope_deg": slope,
                    "runoff_coefficient": runoff_c,
                    "effective_surge_index": surge_index
                }
            ))
            dispatched_count += 1
        elif risk_level == "MODERATE":
            operational_state = "ELEVATED_AWARENESS"
            action_trigger = "MONITOR_LOW_LYING_DEPRESSION_PONDING"
            self.intentions = ["INTENTION_INSPECT_TOPOGRAPHIC_WETNESS_ZONES"]
        else:
            operational_state = "ROUTINE_MONITORING"
            action_trigger = "STABLE_TERRAIN_DRAINAGE"
            self.intentions = ["INTENTION_VERIFY_NATURAL_INFILTRATION"]

        key_indicators = {
            "slope_deg": slope,
            "elevation_m": elevation,
            "soil_type": soil,
            "infiltration_capacity_mmh": infilt_cap,
            "land_cover_class": land_cover,
            "runoff_coefficient": runoff_c,
            "topographic_wetness_index": twi,
            "effective_runoff_surge_index": surge_index
        }

        return {
            "operational_state": operational_state,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": 0.92,
            "critical_flags": critical_flags,
            "action_trigger": action_trigger,
            "dispatched_messages_count": dispatched_count,
            "key_indicators": key_indicators
        }
