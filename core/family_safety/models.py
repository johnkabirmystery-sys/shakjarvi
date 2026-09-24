"""
J.A.R.V.I.S. Mark XVII — Family Safety Data Models
===================================================
Pydantic/Dataclass schemas for devices, consent, signals, alerts, check-ins, and tasks.
"""

import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DeviceType(str, Enum):
    PHONE = "phone"
    TABLET = "tablet"
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    SMARTWATCH = "smartwatch"
    HOME_DEVICE = "home_device"
    SAFETY_SENSOR = "safety_sensor"
    IOT = "iot"
    OTHER = "other"

class PlatformType(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WEB = "web"
    EMBEDDED = "embedded"

class EnrollmentStatus(str, Enum):
    PENDING_PAIRING = "pending_pairing"
    ENROLLED = "enrolled"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    REMOVED = "removed"

class ConsentStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING_REVIEW = "pending_review"

class LocationPermissionLevel(str, Enum):
    NONE = "none"
    ONE_TIME = "one_time"
    WHILE_USING = "while_using"
    ALWAYS = "always"

class AlertSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SignalType(str, Enum):
    VOLUNTARY_SOS = "voluntary_sos"
    MANUAL_CHECKIN = "manual_checkin"
    MISSED_CHECKIN = "missed_checkin"
    DEVICE_OFFLINE = "device_offline"
    LOCATION_UPDATE_LOST = "location_update_lost"
    GEOFENCE_ENTER = "geofence_enter"
    GEOFENCE_EXIT = "geofence_exit"
    LOW_BATTERY = "low_battery"
    EMERGENCY_NOTIFICATION = "emergency_notification"
    PUBLIC_WEATHER_ALERT = "public_weather_alert"
    PUBLIC_EARTHQUAKE_ALERT = "public_earthquake_alert"
    PUBLIC_WILDFIRE_ALERT = "public_wildfire_alert"
    USER_REPORTED_DANGER = "user_reported_danger"

class TaskStatus(str, Enum):
    QUEUED = "queued"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BLOCKED = "blocked"

class UserRole(str, Enum):
    SYSTEM_ADMIN = "system_admin"
    FAMILY_ADMIN = "family_admin"
    PARTICIPANT = "participant"
    EMERGENCY_CONTACT = "emergency_contact"
    READ_ONLY_VIEWER = "read_only_viewer"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FamilyDevice(BaseModel):
    deviceId: str = Field(default_factory=lambda: f"dev_{uuid.uuid4().hex[:12]}")
    displayName: str
    ownerProfileId: str
    deviceType: DeviceType = DeviceType.PHONE
    platform: PlatformType = PlatformType.ANDROID
    enrollmentStatus: EnrollmentStatus = EnrollmentStatus.PENDING_PAIRING
    consentStatus: ConsentStatus = ConsentStatus.PENDING_REVIEW
    locationPermission: LocationPermissionLevel = LocationPermissionLevel.NONE
    lastSeenAt: float = Field(default_factory=time.time)
    lastKnownConnection: Dict[str, Any] = Field(default_factory=dict)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    securityStatus: Dict[str, Any] = Field(default_factory=dict)
    dataRetentionPolicy: str = "7_days"
    createdAt: float = Field(default_factory=time.time)
    updatedAt: float = Field(default_factory=time.time)

class FamilyConsentRecord(BaseModel):
    participantId: str
    ownerProfileId: str
    consentVersion: str = "1.0"
    locationSharingEnabled: bool = False
    liveLocationEnabled: bool = False
    locationHistoryEnabled: bool = False
    safetyAlertsEnabled: bool = True
    geofenceAlertsEnabled: bool = True
    emergencyContactPermission: bool = False
    notificationPermission: bool = True
    backgroundLocationEnabled: bool = False
    externalSharingEnabled: bool = False
    grantedAt: float = Field(default_factory=time.time)
    expiresAt: Optional[float] = None
    revokedAt: Optional[float] = None
    lastReviewedAt: float = Field(default_factory=time.time)

class DiscoveredDevice(BaseModel):
    discoveryId: str = Field(default_factory=lambda: f"disc_{uuid.uuid4().hex[:8]}")
    ipAddress: Optional[str] = None
    macMasked: Optional[str] = None
    hostname: Optional[str] = None
    manufacturer: Optional[str] = None
    serviceMetadata: Dict[str, Any] = Field(default_factory=dict)
    discoveredAt: float = Field(default_factory=time.time)
    networkSegment: str = "192.168.1.0/24"
    enrollmentMatch: Optional[str] = None
    confidenceLevel: float = 0.5
    isIdentified: bool = False
    isOwnerVerified: bool = False

class SafetySignal(BaseModel):
    signalId: str = Field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:10]}")
    participantId: str
    signalType: SignalType
    timestamp: float = Field(default_factory=time.time)
    rawData: Dict[str, Any] = Field(default_factory=dict)
    source: str = "device_telemetry"
    confidence: float = 1.0
    location: Optional[Dict[str, float]] = None

class SafetyAlert(BaseModel):
    alertId: str = Field(default_factory=lambda: f"alt_{uuid.uuid4().hex[:10]}")
    participantId: str
    alertType: str
    severity: AlertSeverity = AlertSeverity.LOW
    triggeredAt: float = Field(default_factory=time.time)
    evidence: str
    source: str
    confidence: float = 1.0
    locationPrecision: str = "city"
    expiration: float = Field(default_factory=lambda: time.time() + 3600 * 4)
    recommendedAction: str
    notificationState: str = "pending"
    escalationState: str = "none"
    falsePositiveRisk: str = "low"
    isDismissed: bool = False
    dismissedAt: Optional[float] = None

class CheckInRecord(BaseModel):
    checkInId: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:10]}")
    participantId: str
    scheduledAt: float = Field(default_factory=time.time)
    status: str = "pending"  # pending, confirmed, missed, cancelled
    responseType: Optional[str] = None  # safe, need_help
    respondedAt: Optional[float] = None
    gracePeriodMinutes: int = 15
    reminderSentAt: Optional[float] = None
    notes: Optional[str] = None

class RemoteTaskRecord(BaseModel):
    taskId: str = Field(default_factory=lambda: f"rtask_{uuid.uuid4().hex[:10]}")
    ownerId: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.QUEUED
    priority: int = 1
    createdAt: float = Field(default_factory=time.time)
    startedAt: Optional[float] = None
    updatedAt: float = Field(default_factory=time.time)
    nextRunAt: Optional[float] = None
    schedule: Optional[str] = None
    progress: float = 0.0
    requiredPermissions: List[str] = Field(default_factory=list)
    toolsUsed: List[str] = Field(default_factory=list)
    lastResult: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cancellationState: Dict[str, Any] = Field(default_factory=dict)
    auditTrail: List[Dict[str, Any]] = Field(default_factory=list)
