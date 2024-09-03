#!/bin/bash
# export PYTHONPATH=$(pwd)/crs_arena:$PYTHONPATH

# Define port variables
# UNICRS_PORT=5001
# BARCOR_PORT=5002
# KBRD_PORT=5000
# CHATGPT_PORT=5003

# # Start the chat servers and capture their PIDs
# nohup python -m script.serve_model --crs_model unicrs --kg_dataset redial --model microsoft/DialoGPT-small --rec_model data/models/unicrs_rec_redial/ --conv_model data/models/unicrs_conv_redial/ --context_max_length 128 --entity_max_length 43 --tokenizer_path microsoft/DialoGPT-small --text_tokenizer_path roberta-base --resp_max_length 128 --text_encoder roberta-base --debug --port $UNICRS_PORT > out_unicrs.log 2>&1 &
# UNICRS_PID=$!

# nohup python -m script.serve_model --crs_model barcor --kg_dataset redial --hidden_size 128 --entity_hidden_size 128 --num_bases 8 --context_max_length 200 --entity_max_length 32 --rec_model data/models/barcor_rec_redial/ --conv_model data/models/barcor_conv_redial/ --tokenizer_path facebook/bart-base --encoder_layers 2 --decoder_layers 2 --attn_head 2 --text_hidden_size 300 --resp_max_length 128 --debug --port $BARCOR_PORT > out_barcor.log 2>&1 &
# BARCOR_PID=$!

# nohup python -m script.serve_model --crs_model kbrd --kg_dataset redial --hidden_size 128 --entity_hidden_size 128 --num_bases 8 --context_max_length 200 --entity_max_length 32 --rec_model data/models/kbrd_rec_redial/ --conv_model data/models/kbrd_conv_redial/ --tokenizer_path facebook/bart-base --encoder_layers 2 --decoder_layers 2 --attn_head 2 --text_hidden_size 300 --resp_max_length 128 --port $KBRD_PORT > out_kbrd.log 2>&1 &
# KBRD_PID=$!

# nohup python -m script.serve_model --api_key {OPENAI_API_KEY} --kg_dataset redial --crs_model chatgpt --port $CHATGPT_PORT > out_chatgpt.log 2>&1 &
# CHATGPT_PID=$!

# # Function to kill all background processes
# cleanup() {
#     echo "Terminating chat servers..."
#     kill $UNICRS_PID $BARCOR_PID $KBRD_PID $CHATGPT_PID
# }

# # Trap termination signals and call cleanup
# trap cleanup SIGINT SIGTERM

# Run the main application
python -m streamlit run crs_arena/arena.py

# Wait for background processes to finish
# wait $UNICRS_PID $BARCOR_PID $KBRD_PID $CHATGPT_PID