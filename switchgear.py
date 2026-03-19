"""
switchgear.py
=============
Contains the SwitchgearController for the DUBGG simulation.
Extracted from generator_sim.py for independent maintenance.

The switchgear distributes load demand proportionally across all online
generators assigned to each GPS panel.
"""

import logging
from typing import Optional, List

from pymodbus.datastore import ModbusDeviceContext

from generator import GeneratorController, GeneratorState

logger = logging.getLogger(__name__)


class SwitchgearController:
    def __init__(self, gps_id: str, register_base: int, ip_address: str = ""):
        self.id = gps_id
        self.register_base = register_base
        self.ip_address = ip_address
        self._last_event_log: Optional[str] = None

    def log(self, message: str):
        """Log switchgear events — deduplicates consecutive identical messages."""
        log_msg = f"[{self.id}] {message}"
        if log_msg != self._last_event_log:
            logger.info(log_msg)
            self._last_event_log = log_msg

    def tick(self, generators: List[GeneratorController], datastore: ModbusDeviceContext):
        P74 = datastore.getValues(3, self.register_base + 74, count=1)
        total_demand = P74[0] if isinstance(P74, list) else 0
        online = []
        for gen in generators:
            assign = False
            if gen.id in ["G1", "G2", "G3", "G4", "G5"]:
                if gen.FCB1 and self.id == "GPS1": assign = True
                if gen.FCB2 and self.id == "GPS2": assign = True
            elif gen.id in ["G6", "G7", "G8", "G9", "G10"]:
                if gen.FCB1 and self.id == "GPS2": assign = True
                if gen.FCB2 and self.id == "GPS1": assign = True
            elif gen.id in ["G11", "G12", "G13", "G14", "G15"]:
                if gen.FCB1 and self.id == "GPS3": assign = True
                if gen.FCB2 and self.id == "GPS4": assign = True
            elif gen.id in ["G16", "G17", "G18", "G19", "G20"]:
                if gen.FCB1 and self.id == "GPS4": assign = True
                if gen.FCB2 and self.id == "GPS3": assign = True
            elif gen.id == "G21":
                if gen.FCB1 and self.id == "GPS1": assign = True
                if gen.FCB2 and self.id == "GPS3": assign = True
            elif gen.id == "G22":
                if gen.FCB1 and self.id == "GPS2": assign = True
                if gen.FCB2 and self.id == "GPS4": assign = True
            if assign and gen.state == GeneratorState.RUNNING:
                online.append(gen)

        count = len(online)
        if count > 0:
            total_capacity = sum(gen.NominalPower for gen in online)
            if total_demand > total_capacity:
                self.log(f"Overload: Demand {total_demand} kW exceeds capacity {total_capacity} kW")
            for gen in online:
                proportional_share = total_demand * (gen.NominalPower / total_capacity)
                with gen.lock:
                    gen.rSetpointPower = min(proportional_share, gen.NominalPower)

        datastore.setValues(3, self.register_base + 901, [count])
