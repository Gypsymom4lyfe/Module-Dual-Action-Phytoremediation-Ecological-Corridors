from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import FastAPI, status
from pydantic import BaseModel, Field

app = FastAPI(title="Thermal Discharge & Sensor Telemetry Service", version="1.0.0")


class SystemStatus(str, Enum):
    NOMINAL = "nominal"
    WARNING = "warning"
    CRITICAL = "critical"


class SensorPayload(BaseModel):
    sensor_id: str = Field(..., description="Unique identifier for the thermal discharge sensor")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the reading")
    temperature_celsius: float = Field(..., description="Current temperature reading in Celsius")
    flow_rate_lps: Optional[float] = Field(None, description="Discharge flow rate in liters per second")
    location_tag: Optional[str] = Field(None, description="Corridor or milepost identifier")


class ThresholdConfig(BaseModel):
    warning_threshold_c: float = Field(45.0, description="Temperature threshold to trigger a warning status")
    critical_threshold_c: float = Field(60.0, description="Temperature threshold to trigger a critical safety alert")


# Default thresholds (can be updated dynamically or loaded from environment/config)
active_thresholds = ThresholdConfig(warning_threshold_c=45.0, critical_threshold_c=60.0)


class TelemetryResponse(BaseModel):
    sensor_id: str
    temperature_celsius: float
    status: SystemStatus
    message: str
    timestamp: datetime


@app.post("/api/v1/telemetry/thermal", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
def evaluate_thermal_discharge(payload: SensorPayload):
    """
    Ingests live sensor data, evaluates temperature against built-in thresholds,
    and returns a status classification for edge logging or automated response.
    """
    temp = payload.temperature_celsius

    # Evaluate against thresholds
    if temp >= active_thresholds.critical_threshold_c:
        system_status = SystemStatus.CRITICAL
        msg = (
            f"CRITICAL: Temperature {temp}°C exceeds critical limit "
            f"of {active_thresholds.critical_threshold_c}°C!"
        )
    elif temp >= active_thresholds.warning_threshold_c:
        system_status = SystemStatus.WARNING
        msg = (
            f"WARNING: Temperature {temp}°C has reached the warning "
            f"threshold of {active_thresholds.warning_threshold_c}°C."
        )
    else:
        system_status = SystemStatus.NOMINAL
        msg = f"Normal operation. Temperature {temp}°C is within safe operating parameters."

    # Here you would typically write to your local edge database, trigger hardware relays,
    # or buffer telemetry for upstream sync.

    return TelemetryResponse(
        sensor_id=payload.sensor_id,
        temperature_celsius=temp,
        status=system_status,
        message=msg,
        timestamp=payload.timestamp,
    )


@app.put("/api/v1/config/thresholds", response_model=ThresholdConfig)
def update_thresholds(config: ThresholdConfig):
    """
    Updates the active thermal thresholds on the fly.
    """
    global active_thresholds
    active_thresholds = config
    return active_thresholds


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
