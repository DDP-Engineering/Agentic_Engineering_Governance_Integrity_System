#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    composition.py
@brief   Assemble the concrete AEGIS version 1 application object graph.
@details This is the only runtime module that selects infrastructure adapters.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import sys
from collections.abc import Sequence

from aegis import PRODUCT_NAME, PROTOCOL_VERSION, __version__
from aegis.application.dispatcher import ApplicationServices, Dispatcher
from aegis.infrastructure.discovery import discover_repository
from aegis.infrastructure.services import Sha256Service, SystemClock, Uuid4Service
from aegis.interface.cli import configure_utf8, run_cli
from aegis.ports.repository import RepositoryDiscovery
from aegis.ports.services import Clock, HashService, UUIDService

# -----------------------------------------------------------------------------
# EXPORTED FUNCTIONS / PUBLIC API
# -----------------------------------------------------------------------------


def create_dispatcher(
    *,
    clock: Clock | None = None,
    uuid_service: UUIDService | None = None,
    hash_service: HashService | None = None,
    repository_discovery: RepositoryDiscovery | None = None,
) -> Dispatcher:
    """
    @brief Assemble the application with real or injected services.
    @param[in] clock Optional deterministic clock.
    @param[in] uuid_service Optional deterministic UUID service.
    @param[in] hash_service Optional deterministic exact-byte hash service.
    @param[in] repository_discovery Optional repository discovery adapter.
    @return A fully assembled AEGIS dispatcher.
    """
    services = ApplicationServices(
        clock=SystemClock() if clock is None else clock,
        uuid=Uuid4Service() if uuid_service is None else uuid_service,
        hashes=Sha256Service() if hash_service is None else hash_service,
        repositories=(
            discover_repository
            if repository_discovery is None
            else repository_discovery
        ),
    )
    return Dispatcher(
        product=PRODUCT_NAME,
        product_version=__version__,
        protocol_version=PROTOCOL_VERSION,
        services=services,
    )


def main(arguments: Sequence[str] | None = None) -> int:
    """@brief Assemble the runtime, configure UTF-8, and execute one CLI request."""
    configure_utf8(sys.stdout)
    return run_cli(
        sys.argv[1:] if arguments is None else arguments,
        stdout=sys.stdout,
        stderr=sys.stderr,
        dispatcher=create_dispatcher(),
    )


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
