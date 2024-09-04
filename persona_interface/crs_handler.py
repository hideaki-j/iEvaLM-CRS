import sys
import os
from typing import Tuple, List

# Get the absolute path of the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root to the Python path
sys.path.insert(0, project_root)

# Change the current working directory to the project root
os.chdir(project_root)

crs_model_map = {
    "kbrd_redial": os.path.join("data/arena/crs_config/KBRD/kbrd_redial.yaml"),
}

from crs_arena.crs_fighter import CRSFighter
from typing import List

class CRSResponseGenerator:
    def __init__(self, model_name: str):
        """Initialize the CRSResponseGenerator with the specified model.
        
        Args:
            model_name: Name of the CRS model to use.
        """
        self.fighter = CRSFighter(1, model_name, crs_model_map[model_name])

    def generate_response(self, dialogue_history: List[str], current_utterance: str) -> Tuple[str, List[str]]:
        """Generate a response using the initialized CRS model.
        
        Args:
            dialogue_history: List of dialogue history.
            current_utterance: Current utterance.
        
        Returns:
            str: Generated response.
        """
        # Format the dialogue history
        history = [{"message": msg} for msg in dialogue_history]

        # Call the reply() method and return the generated response
        response, top_recommendations_names = self.fighter.reply(current_utterance, history)
        return response, top_recommendations_names

# Example usage
if __name__ == "__main__":
    generator = CRSResponseGenerator("kbrd_redial")
    
    dialogue_history = [
        "Hi",
        "I recommend A, B, and C"
    ]
    current_utterance = "I don't like them, could you recommend more family friendly ones?"

    response = generator.generate_response(dialogue_history, current_utterance)
    print("Generated response:", response)
