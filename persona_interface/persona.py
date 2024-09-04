from openai import OpenAI
import os
import json
from typing import Dict, Any, List, Tuple
import concurrent.futures
from tqdm import tqdm

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_persona_related_information_from_wikipedia(persona_key: str, persona_value: str, wiki_text: str) -> Dict[str, Any]:
    # Step 1: Convert persona_key and persona_value to a string
    preference = f"{persona_key}: {persona_value}"

    # Step 2: Prepare the prompt for GPT-4-mini
    prompt = f"""Your task is to determine if the user's preference of "{preference}" is satisfied by the following text mentioned below.
    The process contains three steps:
    - Step 1: Explain the user's preference
    - Step 2: Find the short sentence which answers if the preference is satisfied, and cite exactly as they appear in the text. NEVER alter the text. This should exactly match the text in the original text.
    - Step 3: Determine if the user's preference is likely to be satisfied by the given text. Answer must be ONLY one of the following: "Yes", "No", "Not mentioned".

    Text:
    {wiki_text}
    """.replace("    ", "")

    # Step 3: Call GPT-4-mini
    response = client.chat.completions.create(
        # model="gpt-4o-mini",  # Assuming this is the correct model name
        model = "gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "You are a helpful assistant analyzing text for user preferences."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=500,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "persona_analysis",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "step_1": {
                            "type": "object",
                            "properties": {
                                "explanation": {"type": "string"}
                            },
                            "required": ["explanation"],
                            "additionalProperties": False
                        },
                        "step_2": {
                            "type": "object",
                            "properties": {
                                "related_sentences": {"type": "string"}
                            },
                            "required": ["related_sentences"],
                            "additionalProperties": False
                        },
                        "step_3": {
                            "type": "object",
                            "properties": {
                                "preference_satisfied": {"type": "string", "enum": ["Yes", "No", "Not mentioned"]},
                                "explanation": {"type": "string"}
                            },
                            "required": ["preference_satisfied", "explanation"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["step_1", "step_2", "step_3"],
                    "additionalProperties": False
                }
            }
        }
    )

    # Step 4: Parse and return the structured output
    return json.loads(response.choices[0].message.content)


def get_persona_data(ind: int) -> List[Tuple[str, str]]:
    with open('persona_interface/data/persona.jsonl', 'r') as file:
        personas = [json.loads(line.strip()) for line in file]
    
    assert 0 <= ind < len(personas), f"Invalid index: {ind}. Must be between 0 and {len(personas) - 1}"
    persona_json = personas[ind]
    
    # Parse the JSON into a list of key-value pairs
    persona_list = []
    for key, value in persona_json.items():
        if isinstance(value, list):
            for item in value:
                persona_list.append((key, item))
        else:
            persona_list.append((key, value))
    
    return persona_list

def batch_call(persona_list: List[Tuple[str, str]], wiki_text: str) -> List[Dict[str, Any]]:
    def process_persona(index, persona):
        persona_key, persona_value = persona
        result = get_persona_related_information_from_wikipedia(persona_key, persona_value, wiki_text)
        return index, result

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit all tasks and store futures
        futures = [executor.submit(process_persona, i, persona) for i, persona in enumerate(persona_list)]
        
        # Process results as they complete with a progress bar
        results_dict = {}
        with tqdm(total=len(futures), desc="Processing personas") as pbar:
            for future in concurrent.futures.as_completed(futures):
                index, result = future.result()
                results_dict[index] = result
                pbar.update(1)

    # Sort results based on original index and return as a list
    return [results_dict[i] for i in range(len(persona_list))]

# Example usage:
if __name__ == "__main__":
    # persona_key = "content_restrictions"
    # persona_value = "No adult themes"
    # wiki_text = "This family-friendly movie is suitable for all ages. It contains no violence or adult content."
    
    # result = get_persona_related_information_from_wikipedia(persona_key, persona_value, wiki_text)
    # print(json.dumps(result, indent=2))

    # test batch call
    persona_list = get_persona_data(ind=0)
    wiki_text = "This family-friendly movie is suitable for all ages. It contains no violence or adult content."
    results = batch_call(persona_list, wiki_text)
    print(results)