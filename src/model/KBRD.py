import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import torch
from accelerate import Accelerator
from accelerate.utils import set_seed
from transformers import AutoTokenizer, BartConfig

sys.path.append("..")

from src.model.kbrd.kbrd_model import KBRDforConv, KBRDforRec
from src.model.kbrd.kg_kbrd import KGForKBRD
from src.model.utils import padded_tensor


class KBRD:
    def __init__(
        self,
        seed,
        kg_dataset,
        debug,
        hidden_size,
        entity_hidden_size,
        num_bases,
        rec_model,
        conv_model,
        context_max_length,
        tokenizer_path,
        encoder_layers,
        decoder_layers,
        text_hidden_size,
        attn_head,
        resp_max_length,
        entity_max_length,
    ):
        self.seed = seed
        if self.seed is not None:
            set_seed(self.seed)
        self.kg_dataset = kg_dataset
        # model detailed
        self.debug = debug
        self.hidden_size = hidden_size
        self.entity_hidden_size = entity_hidden_size
        self.num_bases = num_bases
        self.context_max_length = context_max_length
        self.entity_max_length = entity_max_length
        # model
        self.rec_model = rec_model
        self.conv_model = conv_model
        # conv
        self.tokenizer_path = tokenizer_path
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_path)
        self.encoder_layers = encoder_layers
        self.decoder_layers = decoder_layers
        self.text_hidden_size = text_hidden_size
        self.attn_head = attn_head
        self.resp_max_length = resp_max_length
        self.padding = "max_length"
        self.pad_to_multiple_of = 8

        self.kg_dataset_path = f"data/{self.kg_dataset}"
        with open(
            f"{self.kg_dataset_path}/entity2id.json", "r", encoding="utf-8"
        ) as f:
            self.entity2id = json.load(f)

        # Initialize the accelerator.
        self.accelerator = Accelerator(device_placement=False)
        self.device = self.accelerator.device

        self.kg = KGForKBRD(
            kg_dataset=self.kg_dataset, debug=self.debug
        ).get_kg_info()
        self.pad_id = self.kg["pad_id"]

        # rec model
        self.crs_rec_model = KBRDforRec(
            hidden_size=self.hidden_size,
            num_relations=self.kg["num_relations"],
            num_bases=self.num_bases,
            num_entities=self.kg["num_entities"],
        )
        if self.rec_model is not None:
            self.crs_rec_model.load(self.rec_model)
        self.crs_rec_model = self.crs_rec_model.to(self.device)
        self.crs_rec_model = self.accelerator.prepare(self.crs_rec_model)

        # conv model
        config = BartConfig.from_pretrained(
            self.conv_model,
            encoder_layers=self.encoder_layers,
            decoder_layers=self.decoder_layers,
            hidden_size=self.text_hidden_size,
            encoder_attention_heads=self.attn_head,
            decoder_attention_heads=self.attn_head,
            encoder_ffn_dim=self.text_hidden_size,
            decoder_ffn_dim=self.text_hidden_size,
            forced_bos_token_id=None,
            forced_eos_token_id=None,
        )

        self.crs_conv_model = KBRDforConv(
            config, user_hidden_size=self.entity_hidden_size
        ).to(self.device)
        if self.conv_model is not None:
            self.crs_conv_model = KBRDforConv.from_pretrained(
                self.conv_model, user_hidden_size=self.entity_hidden_size
            ).to(self.device)
        self.crs_conv_model = self.accelerator.prepare(self.crs_conv_model)

    def get_rec(self, conv_dict):
        data_dict = {
            "item": [
                self.entity2id[rec]
                for rec in conv_dict["rec"]
                if rec in self.entity2id
            ],
        }

        entity_ids = (
            [
                self.entity2id[ent]
                for ent in conv_dict["entity"][-self.entity_max_length :]
                if ent in self.entity2id
            ],
        )

        if "dialog_id" in conv_dict:
            data_dict["dialog_id"] = conv_dict["dialog_id"]
        if "turn_id" in conv_dict:
            data_dict["turn_id"] = conv_dict["turn_id"]
        if "template" in conv_dict:
            data_dict["template"] = conv_dict["template"]

        # kg
        edge_index, edge_type = torch.as_tensor(
            self.kg["edge_index"], device=self.device
        ), torch.as_tensor(self.kg["edge_type"], device=self.device)

        entity_ids = padded_tensor(
            entity_ids,
            pad_id=self.pad_id,
            pad_tail=True,
            max_length=self.entity_max_length,
            device=self.device,
            debug=self.debug,
        )

        data_dict["entity"] = {
            "entity_ids": entity_ids,
            "entity_mask": torch.ne(entity_ids, self.pad_id),
        }

        # infer
        self.crs_rec_model.eval()

        with torch.no_grad():
            data_dict["entity"]["edge_index"] = edge_index
            data_dict["entity"]["edge_type"] = edge_type
            outputs = self.crs_rec_model(
                **data_dict["entity"], reduction="mean"
            )

            logits = outputs["logit"][:, self.kg["item_ids"]]
            ranks = torch.topk(logits, k=50, dim=-1).indices.tolist()
            preds = [
                [self.kg["item_ids"][rank] for rank in rank_list]
                for rank_list in ranks
            ]
            labels = data_dict["item"]

        return preds, labels

    def get_conv(self, conv_dict):
        self.tokenizer.truncation_side = "left"
        context_list = conv_dict["context"]
        context = f"{self.tokenizer.sep_token}".join(context_list)
        context_ids = self.tokenizer.encode(
            context, truncation=True, max_length=self.context_max_length
        )
        context_batch = defaultdict(list)
        context_batch["input_ids"] = context_ids
        context_ids = self.tokenizer.pad(
            context_batch,
            max_length=self.context_max_length,
            padding=self.padding,
            pad_to_multiple_of=self.pad_to_multiple_of,
        )

        self.tokenizer.truncation_side = "right"
        resp = conv_dict["resp"]
        resp_batch = defaultdict(list)
        resp_ids = self.tokenizer.encode(
            resp, truncation=True, max_length=self.resp_max_length
        )
        resp_batch["input_ids"] = resp_ids
        resp_batch = self.tokenizer.pad(
            resp_batch,
            max_length=self.resp_max_length,
            padding=self.padding,
            pad_to_multiple_of=self.pad_to_multiple_of,
        )

        context_batch["labels"] = resp_batch["input_ids"]

        for k, v in context_batch.items():
            if not isinstance(v, torch.Tensor):
                context_batch[k] = torch.as_tensor(
                    v, device=self.device
                ).unsqueeze(0)

        entity_list = (
            [
                self.entity2id[ent]
                for ent in conv_dict["entity"][-self.entity_max_length :]
                if ent in self.entity2id
            ],
        )

        entity_ids = padded_tensor(
            entity_list,
            pad_id=self.pad_id,
            pad_tail=True,
            device=self.device,
            debug=self.debug,
            max_length=self.context_max_length,
        )

        entity = {
            "entity_ids": entity_ids,
            "entity_mask": torch.ne(entity_ids, self.pad_id),
        }

        data_dict = {"context": context_batch, "entity": entity}

        edge_index, edge_type = torch.as_tensor(
            self.kg["edge_index"], device=self.device
        ), torch.as_tensor(self.kg["edge_type"], device=self.device)

        node_embeds = self.crs_rec_model.get_node_embeds(edge_index, edge_type)
        user_embeds = self.crs_rec_model(
            **data_dict["entity"], node_embeds=node_embeds
        )["user_embeds"]

        gen_inputs = {
            **data_dict["context"],
            "decoder_user_embeds": user_embeds,
        }
        gen_inputs.pop("labels")

        gen_args = {
            "min_length": 0,
            "max_length": self.resp_max_length,
            "num_beams": 1,
            "no_repeat_ngram_size": 3,
            "encoder_no_repeat_ngram_size": 3,
        }
        gen_seqs = self.accelerator.unwrap_model(self.crs_conv_model).generate(
            **gen_inputs, **gen_args
        )
        gen_str = self.tokenizer.decode(gen_seqs[0], skip_special_tokens=True)
        return gen_inputs, gen_str

    def get_choice(self, encoded_instructions, gen_inputs, options, state, conv_dict=None):
        # Merge gen_inputs and instructions (NOTE: This is just a concatenation; not sure if it's the best way to do it)
        inputs = {
            'input_ids': torch.cat([encoded_instructions['input_ids'], gen_inputs['input_ids']], dim=1),
            'attention_mask': torch.cat([encoded_instructions['attention_mask'], gen_inputs['attention_mask']], dim=1),
            'decoder_user_embeds': gen_inputs['decoder_user_embeds']
        }
        outputs = self.accelerator.unwrap_model(self.crs_conv_model).generate(
            **inputs,
            min_new_tokens=2,
            max_new_tokens=2,
            num_beams=1,
            return_dict_in_generate=True,
            output_scores=True,
        )
        option_token_ids = [
            self.tokenizer.encode(op, add_special_tokens=False)[0]
            for op in options
        ]
        option_scores = outputs.scores[-1][0][option_token_ids]

        # def top_p_sampling(scores, p=0.9) -> int:
        #     # Sort the probabilities and their corresponding indices
        #     sorted_scores, sorted_indices = torch.sort(scores, descending=True)
            
        #     # Compute the cumulative sum of sorted probabilities
        #     cumulative_probs = torch.cumsum(F.softmax(sorted_scores, dim=-1), dim=-1)
            
        #     # Find the cutoff index where cumulative probability exceeds p
        #     cutoff_index = torch.where(cumulative_probs > p)[0][0].item()
            
        #     # Select the tokens corresponding to the top-p probabilities
        #     selected_indices = sorted_indices[:cutoff_index + 1]
        #     selected_probs = F.softmax(sorted_scores[:cutoff_index + 1], dim=-1)
            
        #     # Sample from the selected tokens based on their probabilities
        #     selected_token = torch.multinomial(selected_probs, num_samples=1).item()
            
        #     return selected_indices[selected_token].item()

        # selected_option_index = top_p_sampling(option_scores)

        # Probabilistic choice
        option_scores = torch.softmax(option_scores, dim=0)
        selected_option_index = torch.multinomial(option_scores, num_samples=1).item()
        selected_option = options[selected_option_index]
        return selected_option

    def get_response(
        self,
        conv_dict: Dict[str, Any],
        id2entity: Dict[int, str],
        options: Tuple[str, Dict[str, str]],
        state: List[float],
    ) -> Tuple[str, List[float]]:
        """Generates a response given a conversation context.

        Args:
            conv_dict: Conversation context.
            id2entity: Mapping from entity id to entity name.
            options: Prompt with options and dictionary of options.
            state: State of the option choices.

        Returns:
            Generated response and updated state.
        """
        generated_inputs, generated_response = self.get_conv(conv_dict)
        options_letter = list(options[1].keys())

        instructions = options[0]

        encoded_instructions = self.tokenizer(
            instructions,
            truncation=True,
            max_length=self.context_max_length,
            padding=self.padding,
            pad_to_multiple_of=self.pad_to_multiple_of,
            return_tensors="pt"
        )
        encoded_instructions = {k: v.to(self.device) for k, v in encoded_instructions.items()}

        choice = self.get_choice(encoded_instructions, generated_inputs, options_letter, state)

        if choice == options_letter[-1]:
            # Generate a recommendation
            recommended_items, _ = self.get_rec(conv_dict)
            recommended_items_str = ""
            for i, item_id in enumerate(recommended_items[0][:3]):
                recommended_items_str += f"{i+1}: {id2entity[item_id]}  \n"
            response = (
                "I would recommend the following items:  \n"
                f"{recommended_items_str}"
            )
        else:
            response = generated_response

        return response, state


if __name__ == "__main__":
    # print(sys.path)
    kbrd = KBRD(
        seed=42,
        kg_dataset="redial",
        debug=False,
        hidden_size=128,
        num_bases=8,
        rec_model=f"/mnt/tangxinyu/crs/eval_model/redial_rec/best",
        conv_model="/mnt/tangxinyu/crs/eval_model/redial_conv/final/",
        encoder_layers=2,
        decoder_layers=2,
        attn_head=2,
        resp_max_length=128,
        text_hidden_size=300,
        entity_hidden_size=128,
        context_max_length=200,
        entity_max_length=32,
        tokenizer_path="../utils/tokenizer/bart-base",
    )
    # print(kbrd)
    context_dict = {
        "dialog_id": "20001",
        "turn_id": 1,
        "context": ["Hi I am looking for a movie like Super Troopers (2001)"],
        "entity": ["Super Troopers (2001)"],
        "rec": ["Police Academy (1984)"],
        "resp": "You should watch Police Academy (1984)",
        "template": [
            "Hi I am looking for a movie like <mask>",
            "You should watch <mask>",
        ],
    }
    preds, labels = kbrd.get_rec(context_dict)
    gen_seq = kbrd.get_conv(context_dict)
