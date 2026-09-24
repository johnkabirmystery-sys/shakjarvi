"""
J.A.R.V.I.S. Mark XVII — Remote Companion & Task Package
"""

from .auth_manager import remote_auth, RemoteAuthManager
from .command_gateway import remote_command_gateway, RemoteCommandGateway
from .task_orchestrator import persistent_task_manager, PersistentTaskManager
from .reliability_monitor import reliability_monitor, ReliabilityMonitor, SystemReliabilityState
from .telephony_interface import telephony_gateway, TelephonyGateway
