"""Battle Manager module.

Contains helper functions to select fighters for a battle and generate
unique user ids.
"""

import uuid
from collections import defaultdict
from typing import Tuple

from crs_arena.crs_fighter import CRSFighter

# CRS models with their configuration files.
CRS_MODELS = {
    # "kbrd_redial": "data/arena/crs_config/KBRD/kbrd_redial.yaml",
    # "kbrd_opendialkg": "data/arena/crs_config/KBRD/kbrd_opendialkg.yaml",
    "unicrs_redial": "data/arena/crs_config/UniCRS/unicrs_redial.yaml",
    # "unicrs_opendialkg": "data/arena/crs_config/UniCRS/unicrs_opendialkg.yaml",
    # "barcor_redial": "data/arena/crs_config/BARCOR/barcor_redial.yaml",
    # "barcor_opendialkg": "data/arena/crs_config/BARCOR/barcor_opendialkg.yaml",
    "chatgpt_redial": "data/arena/crs_config/ChatGPT/chatgpt_redial.yaml",
    # "chatgpt_opendialkg": (
    #     "data/arena/crs_config/ChatGPT/chatgpt_opendialkg.yaml"
    # ),
}

CONVERSATION_COUNTS = defaultdict(int).fromkeys(CRS_MODELS.keys(), 0)


def get_crs_fighters() -> Tuple[CRSFighter, CRSFighter]:
    """Selects two CRS models for a battle.

    The selection is based on the number of conversations collected per model.
    The ones with the least conversations are selected.

    Returns:
        CRS models to battle.
    """
    pair = sorted(CONVERSATION_COUNTS.items(), key=lambda x: x[1])[:2]
    fighter1 = CRSFighter(1, pair[0][0], CRS_MODELS[pair[0][0]])
    fighter2 = CRSFighter(2, pair[1][0], CRS_MODELS[pair[1][0]])
    return fighter1, fighter2


def get_unique_user_id() -> str:
    """Generates a unique user id.

    Returns:
        Unique user id.
    """
    return str(uuid.uuid4())
