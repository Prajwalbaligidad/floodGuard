"""
Autonomous Flood AI Agent (BDI Architecture & Inter-Agent Signaling)
Autonomous Multi-Agent AI System for Disaster Prediction

Agent Mind:
- Goal: Prevent surprise levee overtopping, protect river basin populations, and mitigate drainage collapse.
- Beliefs: River water stage telemetry, peer weather surge alerts, drainage choke ratio.
- Desires: Guarantee zero false negatives on river breaches, deploy dewatering resources.
- Intentions: Broadcast emergency overtopping alarms and issue basin evacuation triggers.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_agent import BaseAutonomousAIAgent, InterAgentMessageBus, AgentMessage


class FloodAgent(BaseAutonomousAIAgent):
    """Autonomous AI Agent specializing in riverine hydraulics and urban waterlogging defense."""

    def __init__(self, agent_id: str = "AUTONOMOUS_FLOOD_AI_AGENT"):
        super().__init__(
            agent_id=agent_id,
            agent_type="FLOOD",
            primary_goal="PREVENT_LEVEE_OVERTOPPING_AND_MITIGATE_DRAINAGE_COLLAPSE"
        )

    def deliberate_bdi_cycle(
        self,
        obs: Dict[str, Any],
        ml_pred: Optional[Dict[str, Any]],
        bus: InterAgentMessageBus
    ) -> Dict[str, Any]:
        water_level = float(obs.get("water_level_m", 0.0))
        warning_level = float(obs.get("warning_level_m", 0.0))
        danger_level = float(obs.get("danger_level_m", 0.0))
        discharge = float(obs.get("discharge_rate_cumecs", 0.0))
        velocity = float(obs.get("flow_velocity_ms", 0.0))
        waterlogging = float(obs.get("waterlogging_depth_cm", 0.0))
        choke_ratio = float(obs.get("drainage_choke_ratio", 0.0))
        rise_1h = float(obs.get("water_level_rise_1h_m", 0.0))
        rise_3h = float(obs.get("water_level_rise_3h_m", 0.0))
        river_name = obs.get("river_name", "Local River")
        ts = str(obs.get("timestamp", ""))

        # 1. Update Beliefs (Incorporating Sensory Input + Peer Agent Warnings)
        critical_flags: List[str] = []
        if water_level >= danger_level:
            critical_flags.append("RIVER_BREACHED_DANGER_LEVEL")
        elif water_level >= warning_level:
            critical_flags.append("RIVER_ABOVE_WARNING_LEVEL")
        elif (warning_level - water_level) <= 0.6:
            critical_flags.append("RIVER_APPROACHING_WARNING_LEVEL")

        if rise_3h >= 0.40 or rise_1h >= 0.18:
            critical_flags.append("RAPID_RIVER_STAGE_RISE")

        if waterlogging >= 45.0:
            critical_flags.append("SEVERE_URBAN_WATERLOGGING")
        elif waterlogging >= 20.0:
            critical_flags.append("MODERATE_WATERLOGGING")

        if choke_ratio >= 0.80:
            critical_flags.append("DRAINAGE_NETWORK_COLLAPSE")

        # Check if Weather Agent warned of an incoming upstream surge
        peer_alerts = self.beliefs.get("peer_alerts", [])
        if any("UPSTREAM_CLOUDBURST" in alert for alert in peer_alerts):
            critical_flags.append("UPSTREAM_METEOROLOGICAL_SURGE_INCOMING")

        self.beliefs["critical_flags"] = critical_flags
        self.beliefs["danger_breached"] = water_level >= danger_level

        # 2. Evaluate Desires
        self.desires = [
            "SAFEGUARD_RIVERINE_EMBANKMENT_INTEGRITY",
            "PREVENT_URBAN_PONDING_FATALITIES"
        ]

        # 3. Deliberate Risk & Intentions
        if ml_pred:
            risk_score = ml_pred["ml_risk_score"]
            risk_level = ml_pred["ml_predicted_level"]
        else:
            risk_score = 0.95 if (danger_level > 0 and water_level >= danger_level) else (0.65 if (warning_level > 0 and water_level >= warning_level) else 0.05)
            risk_level = "CRITICAL" if risk_score >= 0.75 else "LOW"

        # Continuous Hydrological River & Inundation Physics
        if danger_level > 0 and water_level >= danger_level:
            risk_level = "CRITICAL"
            risk_score = 0.95 + min(0.04, max(0.0, (water_level - danger_level) * 0.05))
        elif warning_level > 0 and water_level >= warning_level:
            risk_level = "HIGH"
            risk_score = 0.55 + min(0.25, ((water_level - warning_level) / max(0.1, danger_level - warning_level)) * 0.25)
        else:
            # Physical reality: When river is safely within banks (below warning mark),
            # baseline continuous risk is strictly governed by physical discharge and stage buffer
            discharge_factor = min(0.25, (discharge / 4000.0) * 0.25)
            buffer_to_warn = max(0.1, warning_level - water_level) if warning_level > 0 else 2.0
            stage_factor = min(0.10, max(0.0, (1.8 - buffer_to_warn) / 1.8) * 0.10)
            waterlog_factor = min(0.06, (waterlogging / 30.0) * 0.06)
            rise_factor = min(0.08, max(0.0, rise_3h) * 0.20)
            
            risk_score = max(0.02, discharge_factor + stage_factor + waterlog_factor + rise_factor + 0.015)
            risk_level = "MODERATE" if risk_score >= 0.18 else "LOW"
            if risk_level == "LOW":
                critical_flags = []
                self.beliefs["critical_flags"] = []

        dispatched_count = 0
        self.intentions = []

        if risk_level == "CRITICAL":
            operational_state = "EMERGENCY_MOBILIZATION"
            action_trigger = f"TRIGGER_EMERGENCY_EVACUATION_{river_name.upper()}_BASIN"
            self.intentions = [
                f"INTENTION_SOUND_RIVERBANK_BREACH_SIRENS_{river_name.upper()}",
                "INTENTION_MOBILIZE_HIGH_CAPACITY_DEWATERING_PUMPS",
                "INTENTION_ALERT_COORDINATOR_FOR_NDRF_DEPLOYMENT"
            ]

            # Broadcast Emergency Alert across the inter-agent bus
            bus.broadcast(AgentMessage(
                message_id=f"MSG_F_{ts}",
                sender_agent="FLOOD",
                recipient_agent="BROADCAST",
                performative="EMERGENCY",
                timestamp=ts,
                subject=f"RIVER_{river_name.upper()}_DANGER_LEVEL_BREACHED",
                content={
                    "water_level_m": water_level,
                    "danger_level_m": danger_level,
                    "danger_buffer_m": round(water_level - danger_level, 3),
                    "drainage_choke_ratio": choke_ratio
                }
            ))
            dispatched_count += 1
        elif risk_level == "HIGH":
            operational_state = "ACTIVE_WATCH"
            action_trigger = "DEPLOY_FLOODPLAIN_BARRIERS_AND_PUMPS"
            self.intentions = ["INTENTION_CLOSE_RIVER_SLUICE_GATES"]
        elif risk_level == "MODERATE":
            operational_state = "ELEVATED_AWARENESS"
            action_trigger = "INTENSIFY_GAUGE_AND_SLUICE_MONITORING"
            self.intentions = ["INTENTION_INCREASE_SAMPLING_FREQUENCY"]
        else:
            operational_state = "ROUTINE_MONITORING"
            action_trigger = "STANDARD_HYDROLOGICAL_MONITORING"
            self.intentions = ["INTENTION_LOG_BASELINE_HYDROGRAPH"]

        key_indicators = {
            "river_name": river_name,
            "water_level_m": water_level,
            "warning_level_m": warning_level,
            "danger_level_m": danger_level,
            "danger_buffer_m": round(water_level - danger_level, 3),
            "water_level_rise_3h_m": rise_3h,
            "discharge_rate_cumecs": discharge,
            "flow_velocity_ms": velocity,
            "waterlogging_depth_cm": waterlogging,
            "drainage_choke_ratio": choke_ratio
        }

        return {
            "operational_state": operational_state,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": 0.95,
            "critical_flags": critical_flags,
            "action_trigger": action_trigger,
            "dispatched_messages_count": dispatched_count,
            "key_indicators": key_indicators
        }
