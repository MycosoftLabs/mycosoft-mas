"""Process-wide Mycosoft CUI guard bootstrap.

Python imports ``sitecustomize`` automatically when the repository/application
root is on ``sys.path``. This installs the central guard before BaseAgent,
CoreBaseAgent, or BaseAgentV2 instances are created.

Set ``MYCOSOFT_CUI_GUARD_REQUIRED=0`` only in an isolated development context
that cannot receive CUI and only with SAO-approved exception documentation.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("mycosoft.cui_guard.bootstrap")

try:
    from mycosoft_mas.security.cui_guard import install_global_agent_guard

    install_global_agent_guard()
except Exception:
    logger.exception("Mycosoft CUI guard bootstrap failed")
    if os.environ.get("MYCOSOFT_CUI_GUARD_REQUIRED", "1") != "0":
        raise
