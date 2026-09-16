"""Curated, generic troubleshooting knowledge for each supported fault type.

This is a static rule-based lookup, not a trained model. FactoryOps never reports
a confidence probability — only threshold-based evidence and a bounded set of
suspected causes ranked by how commonly they explain the observed pattern in
generic industrial-motor operation. All procedures are generic demonstration
guidance, not equipment-specific repair instructions.
"""

from app.models import FaultType

KNOWLEDGE: dict[FaultType, dict] = {
    FaultType.overheating: {
        "label": "Overheating",
        "summary_template": "Temperature has stayed at or above {trigger}C for {breaches} consecutive readings (last reading: {value}C).",
        "suspected_causes": [
            "Insufficient cooling airflow or blocked ventilation",
            "Sustained overload beyond rated duty cycle",
            "Bearing or lubrication degradation increasing friction",
            "Ambient temperature rise around the machine",
        ],
        "next_checks": [
            "Confirm cooling fan/vents are unobstructed and operating",
            "Check load against the machine's rated duty cycle",
            "Inspect for unusual noise or resistance consistent with bearing wear",
            "Compare ambient temperature at the machine to normal operating range",
        ],
        "checklist": [
            "Verify the alert against the live temperature chart",
            "Reduce or pause load on the affected machine if safe to do so",
            "Inspect cooling airflow and clear any obstruction",
            "Check for abnormal vibration or noise alongside the heat",
            "Allow the machine to cool and confirm temperature trends downward",
            "Resume normal operation and monitor for recurrence",
        ],
    },
    FaultType.overload: {
        "label": "Overload",
        "summary_template": "Current draw has stayed at or above {trigger}A for {breaches} consecutive readings (last reading: {value}A).",
        "suspected_causes": [
            "Mechanical binding or increased load torque",
            "Process load exceeding the machine's rated capacity",
            "Electrical supply imbalance or degraded winding insulation",
            "Downstream jam or obstruction increasing resistance",
        ],
        "next_checks": [
            "Check for mechanical binding or obstruction in the driven load",
            "Compare current process load against the machine's rated capacity",
            "Inspect electrical supply for voltage imbalance",
            "Review recent process changes that may have increased load",
        ],
        "checklist": [
            "Verify the alert against the live current chart",
            "Reduce process load if safe to do so",
            "Inspect for mechanical binding downstream of the machine",
            "Check electrical supply quality if available",
            "Confirm current trends back toward the normal operating band",
            "Resume normal operation and monitor for recurrence",
        ],
    },
    FaultType.vibration: {
        "label": "Excessive vibration",
        "summary_template": "Vibration has stayed at or above {trigger}mm/s for {breaches} consecutive readings (last reading: {value}mm/s).",
        "suspected_causes": [
            "Mechanical imbalance or misalignment",
            "Bearing wear or damage",
            "Loose mounting hardware or foundation",
            "Coupling wear between the motor and driven load",
        ],
        "next_checks": [
            "Inspect mounting bolts and foundation for looseness",
            "Check shaft alignment and coupling condition",
            "Listen for irregular bearing noise",
            "Review vibration trend for a sudden step versus gradual drift",
        ],
        "checklist": [
            "Verify the alert against the live vibration chart",
            "Visually inspect mounting hardware for looseness",
            "Check alignment and coupling condition if accessible",
            "Reduce speed/load if safe to do so while inspecting",
            "Confirm vibration trends back toward the normal operating band",
            "Resume normal operation and monitor for recurrence",
        ],
    },
    FaultType.missing_telemetry: {
        "label": "Missing telemetry",
        "summary_template": "No telemetry has been received for at least {trigger} seconds (last reading: {value}).",
        "suspected_causes": [
            "Sensor or edge-gateway power loss",
            "Network connectivity interruption between the machine and the platform",
            "Simulator/telemetry agent process stopped or crashed",
            "Machine powered down or taken out of service",
        ],
        "next_checks": [
            "Confirm the machine and its telemetry agent are powered on",
            "Check network connectivity between the machine and the platform",
            "Check the telemetry agent/simulator process status",
            "Confirm whether the machine was intentionally taken out of service",
        ],
        "checklist": [
            "Confirm whether the outage is expected (planned maintenance/shutdown)",
            "Check power to the machine and its telemetry agent",
            "Check network connectivity on the machine's segment",
            "Restart the telemetry agent/simulator if applicable",
            "Confirm readings resume and are current",
            "Resolve once fresh readings are consistently arriving",
        ],
    },
}
