"""
generator.py
============
Contains the GeneratorController and all supporting types/constants for the
generator simulation.  Extracted from generator_sim.py for easier independent
maintenance.
"""

import logging
import threading
import time
import math
from typing import Optional, List, Dict
from enum import IntEnum

from pymodbus.datastore import ModbusDeviceContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Logging / verbosity
# ---------------------------------------------------------------------------
# Set VERBOSE=True for DEBUG level output.
# HEARTBEAT_LOG_LEVEL adds a custom level between INFO(20) and WARNING(30).
VERBOSE = False
HEARTBEAT_LOG_LEVEL = 25  # sits between INFO and WARNING
logging.addLevelName(HEARTBEAT_LOG_LEVEL, "HEARTBEAT")
LOG_LEVEL = logging.DEBUG if VERBOSE else logging.INFO
logger.setLevel(LOG_LEVEL)
logging.getLogger().setLevel(LOG_LEVEL)

# ---------------------------------------------------------------------------
# Physical tolerances
# ---------------------------------------------------------------------------
VOLTAGE_EPSILON = 10
FREQUENCY_EPSILON = 0.1
POWER_EPSILON = 10

# Duration (ms) of the dead-bus connection window opened by a SSL710 rising edge
DEAD_BUS_WINDOW_MS = 3000


# ---------------------------------------------------------------------------
# Generator state enum + state-machine string mapping
# ---------------------------------------------------------------------------
class GeneratorState(IntEnum):
    STANDSTILL = 0
    STARTING = 1
    RUNNING = 2
    SHUTDOWN = 3
    FAULT = 4
    FAST_TRANSFER = 5


STATE_MAP = {
    "standstill": GeneratorState.STANDSTILL,
    "starting": GeneratorState.STARTING,
    "running": GeneratorState.RUNNING,
    "shutdown": GeneratorState.SHUTDOWN,
    "fault": GeneratorState.FAULT,
    "fastTransfer": GeneratorState.FAST_TRANSFER,
}


# ---------------------------------------------------------------------------
# Lightweight finite state machine
# ---------------------------------------------------------------------------
class StateMachine:
    def __init__(self, initial_state: str):
        self.state = initial_state
        self.transitions: Dict[str, Dict[str, str]] = {}
        self.ignored_triggers: Dict[str, List[str]] = {}

    def add_transition(self, from_state: str, trigger: str, to_state: str):
        self.transitions.setdefault(from_state, {})[trigger] = to_state

    def add_ignore(self, state: str, trigger: str):
        self.ignored_triggers.setdefault(state, []).append(trigger)

    def fire(self, trigger: str) -> bool:
        if trigger in self.ignored_triggers.get(self.state, []):
            return False
        nxt = self.transitions.get(self.state, {}).get(trigger)
        if nxt:
            self.state = nxt
            return True
        return False


# ---------------------------------------------------------------------------
# Generator controller
# ---------------------------------------------------------------------------
class GeneratorController:
    def __init__(self, gen_id: str, register_base: int, ip_address: str = ""):
        if not gen_id:
            raise ValueError("Invalid generator ID")
        self.id = gen_id
        self.register_base = register_base
        self.ip_address = ip_address
        self.last_processed_state = None

        self.DeExcitedVoltage = 3500.0
        self.ExcitedVoltage = 10500.0
        self.rVoltage = 0.0

        self.NominalFrequency = 50.0
        self.NominalPower = 3350.0
        # Reactive power rating (typically ~0.4-0.6 of active power rating)
        self.NominalReactivePower = 2100.0  # Typical for 0.8-0.85 power factor

        self.RampRateVoltage = 10000.0
        self.RampRateFrequency = 200.0
        self.RampRatePowerUp = 10000.0
        self.RampRatePowerDown = 10000.0

        self.dt = 100
        self.StartDelay = 100
        self.StopDelay = 100
        self.startTimer = 0
        self.stopTimer = 1
        self.deadBusWindowTimer = 0
        self.ssl710PreviousValue = False

        # NOTE: self.state is a property — do not set it as a plain attribute here
        self.faultDetected = False

        self.SimulateFailToStart = False
        self.FailRampUp = False
        self.FailRampDown = False
        self.FailStartTime = False
        # configuration overrides – when True, tick will not update from R095 bits
        self._override_SimulateFailToStart = False
        self._override_FailRampUp = False
        self._override_FailRampDown = False
        self._override_FailStartTime = False

        self.SimulatedVoltage = 0.0
        self.SimulatedFrequency = 0.0
        self.SimulatedCurrent = 0.0
        self.SimulatedActivePower = 0.0
        self.SimulatedReactivePower = 0.0

        self.rSetpointPower = 0.0
        self.rSetpointReactivePower = 0.0
        self.previousSetpointPower = 0.0
        self.previousSetpointReactivePower = 0.0

        self.FCB1 = True
        self.FCB2 = False
        self.previousR192 = 0  # Track R192 to detect actual changes
        self.last_heartbeat_time = time.time()
        self.heartbeat_failed = False
        self.HEARTBEAT_TIMEOUT = 60.0  # 60 seconds — auto-shutdown if no heartbeat

        self.SSL = {
            'SSL425_ServiceSWOff': False,
            'SSL426_ServiceSWManual': False,
            'SSL427_ServiceSWAuto': True,
            'SSL429_GenCBClosed': False,
            'SSL430_GenCBOpen': True,
            'SSL431_OperOn': False,
            'SSL432_OperOff': True,
            'SSL435_MainsCBClosed': False,
            'SSL437_TurboChUnitGeneralTrip': False,
            'SSL438_TurboChUnitGeneralWarn': False,
            'SSL439_IgnSysGeneralTrip': False,
            'SSL440_IgnSysGeneralWarn': False,
            'SSL441_SyncGenActivated': False,
            'SSL443_EngineInStartingPhase': False,
            'SSL444_ReadyforAutoDem': True,
            'SSL445_DemandforAux': False,
            'SSL448_ModuleisDemanded': False,
            'SSL449_OperEngineisRunning': False,
            'SSL452_GeneralTrip': False,
            'SSL453_GeneralWarn': False,
            'SSL545_UtilityOperModuleBlocked': False,
            'SSL546_GenBreakerOpenFail': False,
            'SSL547_GenDeexcited': False,
            'SSL548_PowerReductionActivated': False,
            'SSL549_LoadRejectedGCBOpen': False,
            'SSL550_GenSyncLoadReleas': False,
            'SSL563_ReadyforFastStart': True,
            'SSL564_ModuleLockedOut': False,
            'SSL592_EngineAtStandStill': True,
            'SSL593_ScaveningInOper': False,
            'SSL3612_EmergStopPBEngRoom': False,
            'SSL3613_EmergStopPBEngVentRoom': False,
            'SSL3614_EmergStopPBLVMVCtrlRoom': False,
            'SSL3615_EmergStopPBExtCustom': False,
            'SSL3616_AuxSupplySource1': False,
            'SSL3617_AuxSupplySource2': False,
            'SSL3624_TrAppPowExceeded': False,
            'SSL3625_EngSmoothLoadRejectStart': False,
            'SSL3626_LoadRejWaitforReleaseSync': False,
            'SSL3627_GenAntiCondensHeatInOper': False,
            'SSL3630_ReleaseLoadAfterGenExcit': False,
            'SSL701_DemandModule_CMD': False,
            'SSL702_UtilityOperModuleBlocked_CMD': False,
            'SSL703_MainsCBClosed_CMD': False,
            'SSL704_EnGenBreakerActToDeadBus_CMD': False,
            'SSL705_LoadRejectGenCBOpen_CMD': False,
            'SSL706_AuxPowSuppSource1_CMD': False,
            'SSL707_AuxPowSuppSource2_CMD': False,
            'SSL708_ClockPulse_CMD': False,
            'SSL709_GenExcitationOff_CMD': False,
            'SSL710_OthGCBClosedandExcitOn_CMD': False
        }

        self.sm = StateMachine("standstill")
        self.sm.add_transition("standstill", "demand", "starting")
        self.sm.add_transition("standstill", "faultDetected", "fault")
        self.sm.add_ignore("starting", "voltageReady")
        self.sm.add_ignore("starting", "freqReady")
        self.sm.add_transition("starting", "startComplete", "running")
        self.sm.add_transition("starting", "shutdown", "shutdown")
        self.sm.add_transition("starting", "faultDetected", "fault")
        self.sm.add_transition("running", "shutdown", "shutdown")
        self.sm.add_transition("running", "transfer", "fastTransfer")
        self.sm.add_transition("running", "faultDetected", "fault")
        self.sm.add_transition("shutdown", "powerZero", "standstill")
        self.sm.add_transition("shutdown", "faultDetected", "fault")
        self.sm.add_transition("fault", "faultCleared", "standstill")
        self.sm.add_transition("fault", "shutdown", "shutdown")
        self.sm.add_transition("fastTransfer", "demand", "running")
        self.sm.add_transition("fastTransfer", "shutdown", "shutdown")
        self.sm.add_transition("fastTransfer", "faultDetected", "fault")

        self.lock = threading.Lock()
        self._last_status_log = None
        self._last_event_log = None

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------
    def log(self, message: str):
        """Log generator events - uses INFO level for state transitions and important events"""
        log_msg = f"[{self.id}] [{self.sm.state}] {message}"
        if log_msg != self._last_event_log:
            logger.info(log_msg)
            self._last_event_log = log_msg

    # ------------------------------------------------------------------
    # Physics helpers
    # ------------------------------------------------------------------
    def ramp(self, value: float, target: float, rate: float, fail_flag: bool, param_type: str) -> float:
        if fail_flag:
            return value
        delta = target - value
        max_step = rate * self.dt / 1000.0
        step = max(min(delta, max_step), -max_step)
        new_value = value + step

        if param_type == 'power':
            return min(max(new_value, 0), self.NominalPower)
        if param_type == 'reactive_power':
            return min(max(new_value, -self.NominalReactivePower), self.NominalReactivePower)
        if param_type == 'voltage':
            return min(max(new_value, 0), self.ExcitedVoltage)
        if param_type == 'frequency':
            return min(max(new_value, 0), self.NominalFrequency * 1.1)
        return new_value

    # ------------------------------------------------------------------
    # Modbus register parsers
    # ------------------------------------------------------------------
    def parse_R192(self, value: int):
        flags = [
            ('SSL701_DemandModule_CMD', 0),
            ('SSL702_UtilityOperModuleBlocked_CMD', 1),
            ('SSL703_MainsCBClosed_CMD', 2),
            ('SSL704_EnGenBreakerActToDeadBus_CMD', 3),
            ('SSL705_LoadRejectGenCBOpen_CMD', 4),
            ('SSL706_AuxPowSuppSource1_CMD', 5),
            ('SSL707_AuxPowSuppSource2_CMD', 6),
            ('SSL708_ClockPulse_CMD', 7),  # Heartbeat
            ('SSL709_GenExcitationOff_CMD', 8),
            ('SSL710_OthGCBClosedandExcitOn_CMD', 9)
        ]
        for name, bit in flags:
            self.SSL[name] = ((value >> bit) & 1) == 1

    # ------------------------------------------------------------------
    # Output reset
    # ------------------------------------------------------------------
    def reset_outputs(self):
        self.SimulatedVoltage = 0.0
        self.SimulatedFrequency = 0.0
        self.SimulatedCurrent = 0.0
        self.SimulatedActivePower = 0.0
        self.SimulatedReactivePower = 0.0
        self.rVoltage = 0.0
        self.SSL['SSL429_GenCBClosed'] = False
        self.SSL['SSL430_GenCBOpen'] = True
        self.SSL['SSL431_OperOn'] = False
        self.SSL['SSL432_OperOff'] = True
        self.SSL['SSL444_ReadyforAutoDem'] = True
        self.SSL['SSL448_ModuleisDemanded'] = False
        self.SSL['SSL547_GenDeexcited'] = False
        self.SSL['SSL592_EngineAtStandStill'] = True
        self.SSL['SSL550_GenSyncLoadReleas'] = False
        self.SSL['SSL563_ReadyforFastStart'] = True

    # ------------------------------------------------------------------
    # State entry actions
    # ------------------------------------------------------------------
    def on_enter_standstill(self):
        self.log("ENTERING STATE: Standstill")
        self.reset_outputs()

    def on_enter_starting(self):
        self.log("ENTERING STATE: Starting")
        self.startTimer = 0
        self.SSL['SSL431_OperOn'] = True
        self.SSL['SSL432_OperOff'] = False
        self.SSL['SSL448_ModuleisDemanded'] = True
        self.SSL['SSL592_EngineAtStandStill'] = False
        self.SSL['SSL443_EngineInStartingPhase'] = True
        self.SSL['SSL563_ReadyforFastStart'] = False

    def on_enter_running(self):
        self.log("ENTERING STATE: Running")
        self.SSL['SSL550_GenSyncLoadReleas'] = True
        # Do not force SSL547 here — allow external commands to control de-excitation
        self.SSL['SSL448_ModuleisDemanded'] = True
        self.SSL['SSL444_ReadyforAutoDem'] = False
        self.SSL['SSL449_OperEngineisRunning'] = True
        self.SSL['SSL592_EngineAtStandStill'] = False
        self.SSL['SSL443_EngineInStartingPhase'] = False

    def on_enter_shutdown(self):
        self.log("ENTERING STATE: Shutdown")
        self.stopTimer = 0
        self.SSL['SSL448_ModuleisDemanded'] = False

    def on_enter_fault(self):
        self.log("ENTERING STATE: Fault")
        self.reset_outputs()
        # Explicitly clear engine running flag in fault state
        self.SSL['SSL449_OperEngineisRunning'] = False

    def on_enter_fast_transfer(self):
        self.log("ENTERING STATE: FastTransfer")
        self.SSL['SSL429_GenCBClosed'] = False
        self.SSL['SSL430_GenCBOpen'] = True
        self.SimulatedFrequency = self.NominalFrequency
        self.SimulatedVoltage = self.ExcitedVoltage
        self.SimulatedActivePower = 0
        self.SimulatedReactivePower = 0

    # ------------------------------------------------------------------
    # State property – always derived from the string state machine
    # ------------------------------------------------------------------
    @property
    def state(self) -> GeneratorState:
        """Always in sync with the string-based state machine (sm.state).

        Using a property eliminates the dual-state tracking problem: any reader
        (including SwitchgearController) sees the live value without needing a
        separate manual assignment.
        """
        return STATE_MAP.get(self.sm.state, GeneratorState.STANDSTILL)

    # ------------------------------------------------------------------
    # State machine update
    # ------------------------------------------------------------------
    def update_state(self):
        """Deferred entry-action dispatcher.

        sm.fire() updates sm.state immediately on the calling tick.  The
        corresponding on_enter_* callback is invoked here on the *next* tick
        (when last_processed_state diverges from sm.state).  This keeps entry
        actions decoupled from the transition triggers and prevents re-running
        them if update_state() is called multiple times in the same tick.
        """
        if not self.SSL['SSL427_ServiceSWAuto']:
            return
        current_state = self.sm.state
        if current_state != self.last_processed_state:
            self.log(f"STATE TRANSITION: {self.last_processed_state} -> {current_state}")
            func_name = f"on_enter_{current_state}"
            if hasattr(self, func_name):
                getattr(self, func_name)()
            self.last_processed_state = current_state
            # self.state is a property — no manual sync needed
        if self.faultDetected and self.sm.state != "fault":
            self.sm.fire("faultDetected")
            return
        voltage_in_range = abs(self.SimulatedVoltage - self.rVoltage) < VOLTAGE_EPSILON
        frequency_in_range = abs(self.SimulatedFrequency - self.NominalFrequency) < FREQUENCY_EPSILON
        is_power_zero = abs(self.SimulatedActivePower) < POWER_EPSILON
        if self.sm.state == "starting":
            self.startTimer += self.dt
        elif self.sm.state == "shutdown":
            self.stopTimer += self.dt
        if self.sm.state == "standstill":
            if self.SSL['SSL701_DemandModule_CMD']:
                self.sm.fire("demand")
        elif self.sm.state == "starting":
            if not self.SSL['SSL701_DemandModule_CMD']:
                self.sm.fire("shutdown")
            else:
                if voltage_in_range:
                    self.sm.fire("voltageReady")
                if frequency_in_range:
                    self.sm.fire("freqReady")
                if (self.startTimer >= self.StartDelay or self.FailStartTime) and voltage_in_range and frequency_in_range:
                    if self.SimulateFailToStart:
                        self.log("Start blocked by SimulateFailToStart flag")
                    else:
                        bus_is_live = self.SSL['SSL710_OthGCBClosedandExcitOn_CMD']
                        if self.SSL['SSL709_GenExcitationOff_CMD']:
                            self.SSL['SSL448_ModuleisDemanded'] = True
                            self.SSL['SSL547_GenDeexcited'] = True
                            self.SSL['SSL550_GenSyncLoadReleas'] = True
                        if self.SSL['SSL704_EnGenBreakerActToDeadBus_CMD'] and not bus_is_live and self.SSL['SSL430_GenCBOpen']:
                            self.SSL['SSL429_GenCBClosed'] = True
                            self.SSL['SSL430_GenCBOpen'] = False
                            self.SSL['SSL431_OperOn'] = True
                            self.SSL['SSL432_OperOff'] = False
                            self.log("CB CLOSED to dead busbar (SSL704)")
                            self.sm.fire("startComplete")
                        if bus_is_live and not self.SSL['SSL709_GenExcitationOff_CMD'] and self.SSL['SSL430_GenCBOpen']:
                            self.SSL['SSL441_SyncGenActivated'] = True
                            self.SSL['SSL547_GenDeexcited'] = False
                            self.SSL['SSL3630_ReleaseLoadAfterGenExcit'] = True
                            phase_angle_ok = True
                            if phase_angle_ok:
                                self.SSL['SSL429_GenCBClosed'] = True
                                self.SSL['SSL430_GenCBOpen'] = False
                                self.SSL['SSL431_OperOn'] = True
                                self.SSL['SSL432_OperOff'] = False
                                self.log("CB CLOSED via auto-sync to live busbar")
                                self.sm.fire("startComplete")
        elif self.sm.state == "running":
            if self.SSL['SSL705_LoadRejectGenCBOpen_CMD']:
                self.sm.fire("transfer")
            elif not self.SSL['SSL701_DemandModule_CMD']:
                self.sm.fire("shutdown")
        elif self.sm.state == "shutdown":
            power_below_10_percent = self.SimulatedActivePower < (self.NominalPower * 0.1)
            if power_below_10_percent and self.SSL['SSL429_GenCBClosed']:
                self.SSL['SSL429_GenCBClosed'] = False
                self.SSL['SSL430_GenCBOpen'] = True
                self.SSL['SSL448_ModuleisDemanded'] = False
                self.SSL['SSL431_OperOn'] = False
                self.SSL['SSL432_OperOff'] = True
                self.log(f"CB OPENED - power below 10% ({self.SimulatedActivePower:.1f} kW)")
            if is_power_zero and self.stopTimer >= self.StopDelay:
                self.log("Shutdown complete - transitioning to standstill")
                self.sm.fire("powerZero")
        elif self.sm.state == "fastTransfer":
            if self.SSL['SSL429_GenCBClosed']:
                self.SSL['SSL429_GenCBClosed'] = False
                self.SSL['SSL430_GenCBOpen'] = True
            if not self.SSL['SSL705_LoadRejectGenCBOpen_CMD']:
                self.SSL['SSL429_GenCBClosed'] = True
                self.SSL['SSL430_GenCBOpen'] = False
                self.sm.fire("demand")

    def validate_ssl_flags(self):
        service_modes = sum([self.SSL['SSL427_ServiceSWAuto'], self.SSL['SSL426_ServiceSWManual'], self.SSL['SSL425_ServiceSWOff']])
        if service_modes > 1:
            if self.SSL['SSL427_ServiceSWAuto']:
                self.SSL['SSL426_ServiceSWManual'] = False
                self.SSL['SSL425_ServiceSWOff'] = False
            elif self.SSL['SSL426_ServiceSWManual']:
                self.SSL['SSL427_ServiceSWAuto'] = False
                self.SSL['SSL425_ServiceSWOff'] = False
        elif service_modes == 0:
            self.SSL['SSL427_ServiceSWAuto'] = True
        if self.SSL['SSL430_GenCBOpen']:
            self.SSL['SSL429_GenCBClosed'] = False
        elif self.SSL['SSL429_GenCBClosed']:
            self.SSL['SSL430_GenCBOpen'] = False
        else:
            self.SSL['SSL430_GenCBOpen'] = True
        if self.SSL['SSL431_OperOn']:
            self.SSL['SSL432_OperOff'] = False
        elif self.SSL['SSL432_OperOff']:
            self.SSL['SSL431_OperOn'] = False
        if self.SSL['SSL592_EngineAtStandStill']:
            self.SSL['SSL449_OperEngineisRunning'] = False
            self.SSL['SSL443_EngineInStartingPhase'] = False
        if self.SSL['SSL705_LoadRejectGenCBOpen_CMD']:
            self.SSL['SSL549_LoadRejectedGCBOpen'] = True
        else:
            self.SSL['SSL549_LoadRejectedGCBOpen'] = False

    def update_simulation_dynamics(self):
        if self.sm.state in ['standstill', 'fault', 'shutdown']:
            self.rVoltage = 0.0
        elif self.sm.state in ['starting', 'running', 'fastTransfer']:
            # Excitation controlled ONLY by SSL709
            self.SSL['SSL547_GenDeexcited'] = self.SSL['SSL709_GenExcitationOff_CMD']
            if self.SSL['SSL547_GenDeexcited']:
                self.rVoltage = self.DeExcitedVoltage
            else:
                self.rVoltage = self.ExcitedVoltage

        # Voltage ramp towards rVoltage
        self.SimulatedVoltage = self.ramp(
            self.SimulatedVoltage, self.rVoltage, self.RampRateVoltage, self.FailRampUp, 'voltage'
        )
        target_frequency = 0.0
        if self.sm.state in ['starting', 'running', 'fastTransfer']:
            target_frequency = self.NominalFrequency
        elif self.sm.state == 'shutdown':
            target_frequency = 0.0

        self.SimulatedFrequency = self.ramp(self.SimulatedFrequency, target_frequency, self.RampRateFrequency, self.FailRampUp, 'frequency')
        if self.sm.state in ['standstill', 'fault']:
            self.SimulatedFrequency = 0.0

        target_power = 0.0
        if self.sm.state == 'running' and self.SSL['SSL429_GenCBClosed']:
            target_power = self.rSetpointPower
        elif self.sm.state == 'fastTransfer':
            target_power = 0.0

        current_power_ramp_rate = self.RampRatePowerDown if (self.SimulatedActivePower > target_power and target_power == 0.0) else self.RampRatePowerUp
        fail_ramp_flag = self.FailRampDown if (self.SimulatedActivePower > target_power and target_power == 0.0) else self.FailRampUp
        if self.sm.state == 'shutdown':
            current_power_ramp_rate = self.RampRatePowerDown
            fail_ramp_flag = self.FailRampDown

        self.SimulatedActivePower = self.ramp(self.SimulatedActivePower, target_power, current_power_ramp_rate, fail_ramp_flag, 'power')
        if (self.SSL['SSL430_GenCBOpen'] and self.sm.state != 'starting') or self.sm.state in ['standstill', 'fault']:
            self.SimulatedActivePower = 0.0

        target_reactive_power = 0.0
        if self.sm.state == 'running' and self.SSL['SSL429_GenCBClosed']:
            target_reactive_power = self.rSetpointReactivePower
        elif self.sm.state == 'fastTransfer':
            target_reactive_power = 0.0

        current_reactive_power_ramp_rate = self.RampRatePowerDown if (self.SimulatedReactivePower > target_reactive_power and target_reactive_power == 0.0) else self.RampRatePowerUp
        fail_reactive_ramp_flag = self.FailRampDown if (self.SimulatedReactivePower > target_reactive_power and target_reactive_power == 0.0) else self.FailRampUp
        if self.sm.state == 'shutdown':
            current_reactive_power_ramp_rate = self.RampRatePowerDown
            fail_reactive_ramp_flag = self.FailRampDown

        self.SimulatedReactivePower = self.ramp(self.SimulatedReactivePower, target_reactive_power, current_reactive_power_ramp_rate, fail_reactive_ramp_flag, 'reactive_power')
        if (self.SSL['SSL430_GenCBOpen'] and self.sm.state != 'starting') or self.sm.state in ['standstill', 'fault']:
            self.SimulatedReactivePower = 0.0

        P_kW = self.SimulatedActivePower
        Q_kVAr = self.SimulatedReactivePower
        S_kVA = math.sqrt(P_kW * P_kW + Q_kVAr * Q_kVAr)
        if self.SimulatedVoltage > VOLTAGE_EPSILON:
            self.SimulatedCurrent = (S_kVA * 1000) / (self.SimulatedVoltage * 1.732)
        else:
            self.SimulatedCurrent = 0.0
        self.SimulatedCurrent = float(f"{self.SimulatedCurrent:.2f}")

    # ------------------------------------------------------------------
    # Main simulation tick (called every dt ms)
    # ------------------------------------------------------------------
    def tick(self, datastore: ModbusDeviceContext):
        status_line = (
            f"{self.id} | State: {self.sm.state} | "
            f"V={self.SimulatedVoltage:.1f} | "
            f"F={self.SimulatedFrequency:.1f} | "
            f"P={self.SimulatedActivePower:.1f} | "
            f"CB={self.SSL['SSL429_GenCBClosed']}"
        )
        if status_line != self._last_status_log:
            logger.info(status_line)
            self._last_status_log = status_line
        with self.lock:
            # Read inputs and update state BEFORE calculating simulation dynamics
            # This prevents 1-cycle lag where physics use previous state
            R095 = datastore.getValues(3, self.register_base + 95, count=1)
            if isinstance(R095, list):
                R095_Value = R095[0]
                if not getattr(self, '_override_SimulateFailToStart', False):
                    self.SimulateFailToStart = ((R095_Value >> 0) & 1) == 1
                if not getattr(self, '_override_FailRampUp', False):
                    self.FailRampUp = ((R095_Value >> 1) & 1) == 1
                if not getattr(self, '_override_FailRampDown', False):
                    self.FailRampDown = ((R095_Value >> 2) & 1) == 1
                if not getattr(self, '_override_FailStartTime', False):
                    self.FailStartTime = ((R095_Value >> 3) & 1) == 1
                reset_fault_cmd = ((R095_Value >> 4) & 1) == 1
                if reset_fault_cmd and self.faultDetected:
                    self.faultDetected = False
                    self.sm.fire("faultCleared")

            R192 = datastore.getValues(3, self.register_base + 192, count=1)
            if isinstance(R192, list):
                current_R192 = R192[0]

                # Check for heartbeat (Bit 7 / SSL708_ClockPulse_CMD)
                xor_diff = current_R192 ^ self.previousR192
                heartbeat_changed = (xor_diff & 128) != 0

                if heartbeat_changed:
                    self.last_heartbeat_time = time.time()
                    if self.heartbeat_failed:
                        self.log("Heartbeat restored (R192 Bit 7)")
                        self.heartbeat_failed = False

                if current_R192 != self.previousR192:
                    is_heartbeat_only = xor_diff == 128
                    if not is_heartbeat_only:
                        logger.info(f"[{self.id}] R192 changed: {self.previousR192} -> {current_R192}")

                    self.parse_R192(current_R192)
                    self.previousR192 = current_R192

            # Heartbeat supervision: if R192 Bit 7 (SSL708_ClockPulse_CMD) stops toggling
            # for longer than HEARTBEAT_TIMEOUT seconds, trigger automatic shutdown.
            #
            # We only *act* on the timeout when heartbeat_failed is False so that the
            # shutdown fires exactly once.  heartbeat_failed is cleared by the
            # restoration branch above, so the guard will re-arm after
            # the PLC reconnects and resumes heartbeating.
            if (not self.heartbeat_failed and
                    (time.time() - self.last_heartbeat_time) > self.HEARTBEAT_TIMEOUT):
                self.log(f"HEARTBEAT TIMEOUT: R192 Bit 7 has not toggled for > {self.HEARTBEAT_TIMEOUT}s — initiating automatic shutdown")
                self.heartbeat_failed = True
                # Clear the demand command so update_state() will trigger the shutdown path
                self.SSL['SSL701_DemandModule_CMD'] = False
                # Directly fire shutdown for states that won't check SSL701 on their own
                if self.sm.state in ("starting", "running", "fastTransfer"):
                    self.sm.fire("shutdown")

            # Update state machine and flags first
            self.validate_ssl_flags()
            self.update_state()

            # Now calculate simulation dynamics based on current state
            self.update_simulation_dynamics()

            datastore.setValues(3, self.register_base + 129, [int(self.SimulatedActivePower)])
            datastore.setValues(3, self.register_base + 130, [int(self.SimulatedReactivePower)])
            datastore.setValues(3, self.register_base + 76, [int(self.SimulatedFrequency * 100)])
            datastore.setValues(3, self.register_base + 77, [int(self.SimulatedCurrent)])
            datastore.setValues(3, self.register_base + 78, [int(self.SimulatedVoltage)])

            R014 = 0
            if self.SSL['SSL425_ServiceSWOff']: R014 |= (1 << 0)
            if self.SSL['SSL426_ServiceSWManual']: R014 |= (1 << 1)
            if self.SSL['SSL427_ServiceSWAuto']: R014 |= (1 << 2)
            if self.SSL['SSL429_GenCBClosed']: R014 |= (1 << 4)
            if self.SSL['SSL430_GenCBOpen']: R014 |= (1 << 5)
            if self.SSL['SSL431_OperOn']: R014 |= (1 << 6)
            if self.SSL['SSL432_OperOff']: R014 |= (1 << 7)
            if self.SSL['SSL449_OperEngineisRunning']: R014 |= (1 << 8)
            if self.SSL['SSL441_SyncGenActivated']: R014 |= (1 << 9)
            if self.SSL['SSL435_MainsCBClosed']: R014 |= (1 << 10)
            if self.SSL['SSL452_GeneralTrip']: R014 |= (1 << 11)
            if self.SSL['SSL437_TurboChUnitGeneralTrip']: R014 |= (1 << 12)
            if self.SSL['SSL438_TurboChUnitGeneralWarn']: R014 |= (1 << 13)
            if self.SSL['SSL439_IgnSysGeneralTrip']: R014 |= (1 << 14)
            if self.SSL['SSL440_IgnSysGeneralWarn']: R014 |= (1 << 15)
            datastore.setValues(3, self.register_base + 14, [R014])

            R015 = 0
            if self.SSL['SSL441_SyncGenActivated']: R015 |= (1 << 0)
            if self.SSL['SSL443_EngineInStartingPhase']: R015 |= (1 << 2)
            if self.SSL['SSL444_ReadyforAutoDem']: R015 |= (1 << 3)
            if self.SSL['SSL445_DemandforAux']: R015 |= (1 << 4)
            if self.SSL['SSL448_ModuleisDemanded']: R015 |= (1 << 7)
            if self.SSL['SSL449_OperEngineisRunning']: R015 |= (1 << 8)
            if self.SSL['SSL452_GeneralTrip']: R015 |= (1 << 11)
            if self.SSL['SSL453_GeneralWarn']: R015 |= (1 << 12)
            datastore.setValues(3, self.register_base + 15, [R015])

            R023 = 0
            if self.SSL['SSL563_ReadyforFastStart']: R023 |= (1 << 12)
            if self.SSL['SSL564_ModuleLockedOut']: R023 |= (1 << 15)
            datastore.setValues(3, self.register_base + 23, [R023])

            R029 = 0
            if self.SSL['SSL3612_EmergStopPBEngRoom']: R029 |= (1 << 3)
            if self.SSL['SSL3613_EmergStopPBEngVentRoom']: R029 |= (1 << 4)
            if self.SSL['SSL3614_EmergStopPBLVMVCtrlRoom']: R029 |= (1 << 5)
            if self.SSL['SSL3615_EmergStopPBExtCustom']: R029 |= (1 << 6)
            if self.SSL['SSL3616_AuxSupplySource1']: R029 |= (1 << 7)
            if self.SSL['SSL3617_AuxSupplySource2']: R029 |= (1 << 8)
            if self.SSL['SSL3624_TrAppPowExceeded']: R029 |= (1 << 15)
            datastore.setValues(3, self.register_base + 29, [R029])

            R030 = 0
            if self.SSL['SSL3625_EngSmoothLoadRejectStart']: R030 |= (1 << 0)
            if self.SSL['SSL3626_LoadRejWaitforReleaseSync']: R030 |= (1 << 1)
            if self.SSL['SSL3627_GenAntiCondensHeatInOper']: R030 |= (1 << 2)
            if self.SSL['SSL3630_ReleaseLoadAfterGenExcit']: R030 |= (1 << 5)
            datastore.setValues(3, self.register_base + 30, [R030])

            R031 = 0
            if self.SSL['SSL592_EngineAtStandStill']: R031 |= (1 << 1)
            if self.SSL['SSL593_ScaveningInOper']: R031 |= (1 << 2)
            datastore.setValues(3, self.register_base + 31, [R031])

            R109 = 0
            if self.SSL['SSL545_UtilityOperModuleBlocked']: R109 |= (1 << 0)
            if self.SSL['SSL546_GenBreakerOpenFail']: R109 |= (1 << 1)
            if self.SSL['SSL547_GenDeexcited']: R109 |= (1 << 2)
            if self.SSL['SSL548_PowerReductionActivated']: R109 |= (1 << 3)
            if self.SSL['SSL549_LoadRejectedGCBOpen']: R109 |= (1 << 4)
            if self.SSL['SSL550_GenSyncLoadReleas']: R109 |= (1 << 5)
            datastore.setValues(3, self.register_base + 109, [R109])

            if self.sm.state == 'running' and self.SSL['SSL703_MainsCBClosed_CMD'] and self.SSL['SSL430_GenCBOpen']:
                voltage_ready = abs(self.SimulatedVoltage - self.ExcitedVoltage) < VOLTAGE_EPSILON
                frequency_ready = abs(self.SimulatedFrequency - self.NominalFrequency) < FREQUENCY_EPSILON
                if voltage_ready and frequency_ready:
                    self.SSL['SSL429_GenCBClosed'] = True
                    self.SSL['SSL430_GenCBOpen'] = False
                    self.log("CB CLOSED via SSL703_MainsCBClosed_CMD")

            if not self.ssl710PreviousValue and self.SSL['SSL710_OthGCBClosedandExcitOn_CMD']:
                self.deadBusWindowTimer = DEAD_BUS_WINDOW_MS
                self.log("SSL710 rising edge - 3s dead bus window opened")
            self.ssl710PreviousValue = self.SSL['SSL710_OthGCBClosedandExcitOn_CMD']

            if self.deadBusWindowTimer > 0:
                self.deadBusWindowTimer = max(0, self.deadBusWindowTimer - self.dt)
                if (self.sm.state == 'running' and self.SSL['SSL430_GenCBOpen'] and
                    self.SSL['SSL547_GenDeexcited'] and self.SSL['SSL704_EnGenBreakerActToDeadBus_CMD']):
                    self.SSL['SSL429_GenCBClosed'] = True
                    self.SSL['SSL430_GenCBOpen'] = False
                    self.log("CB CLOSED during 3s dead bus window (de-excited)")
