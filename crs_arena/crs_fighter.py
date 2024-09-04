"""CRS Fighter.

This class represents a CRS fighter. A CRS fighter has a fighter id (i.e., 1
or 2), a name (i.e., model name), and a CRS. The CRS is loaded using the
model name and configuration file.
"""

import json
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from crs_arena.utils import get_crs_model
from src.model.utils import get_entity

if TYPE_CHECKING:
    from crs_arena.battle_manager import Message


class CRSFighter:
    def __init__(self, fighter_id: int, name: str, config_path: str) -> None:
        """Initializes CRS fighter.

        Args:
            fighter_id: Fighter id (1 or 2).
            name: Model name.
            config: Model configuration file.

        Raises:
            ValueError: If id is not 1 or 2.
        """
        if fighter_id not in [1, 2]:
            raise ValueError("Fighter id must be 1 or 2.")

        self.fighter_id = fighter_id

        self.name = name
        self.config_path = config_path
        self.model = get_crs_model(self.name, self.config_path)

        # Load entity data
        self._load_entity_data()

        # Generation arguments
        self.response_generation_args = self._get_response_generation_args()

    def _load_entity_data(self):
        """Loads entity data."""
        with open(
            f"data/{self.model.crs_model.kg_dataset}/entity2id.json",
            "r",
            encoding="utf-8",
        ) as f:
            self.entity2id = json.load(f)

        self.id2entity = {int(v): k for k, v in self.entity2id.items()}
        self.entity_list = list(self.entity2id.keys())

    def _get_response_generation_args(self) -> Dict[str, Any]:
        """Returns response generation arguments."""
        if "unicrs" in self.name:
            return {
                "movie_token": (
                    "<movie>"
                    if self.model.crs_model.kg_dataset.startswith("redial")
                    else "<mask>"
                ),
            }
        return {}

    def _process_user_input(
        self, input_message: str, history: List["Message"]
    ) -> Dict[str, Any]:
        """Processes user input.

        The conversation dictionary contains the following keys: context,
        entity, rec, and resp. Context is a list of the previous utterances,
        entity is a list of entities mentioned in the conversation, rec is the
        recommended items, resp is the response generated by the model, and
        template is the context with masked entities.
        Note that rec, resp, and template are empty as the model is used for
        inference only, they are kept for compatibility with the models.

        Args:
            input_message: User input message.
            history: Conversation history.

        Returns:
            Processed user input.
        """
        context = [m["message"] for m in history] + [input_message]
        entities = []
        for utterance in context:
            utterance_entities = get_entity(utterance, self.entity_list)
            entities.extend(utterance_entities)

        return {
            "context": context,
            "entity": entities,
            "rec": [],
            "resp": "",
            "template": [],
        }

    def reply(self, input_message: str, history: List["Message"]) -> Tuple[str, List[str]]:
        """Generates a reply to the user input.

        Args:
            input_message: User input message.
            history: Conversation history.

        Returns:
            Generated response.
        """
        # Process conversation to create conversation dictionary
        conversation_dict = self._process_user_input(input_message, history)

        # Get response
        response, top_recommendations_names = self.model.get_response(
            conversation_dict,
            self.id2entity,
            **self.response_generation_args,
        )
        return response, top_recommendations_names
