#!/bin/bash
# Alice Session 2: New session (different run_id), same user_id
# Demonstrates cross-session memory recall
BASE_URL="http://127.0.0.1:9090"

echo "" >> alice_output.txt
echo "=== Alice Session 2 (New Session) ===" >> alice_output.txt
echo "" >> alice_output.txt

# Turn 1
echo "User: What do you remember about me?" >> alice_output.txt
response=$(curl -s -X POST "$BASE_URL/invocation" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice3",
    "run_id": "alice3-session-2",
    "query": "What do you remember about me?"
  }' | jq -r '.response')
echo "Agent: $response" >> alice_output.txt
echo "" >> alice_output.txt

sleep 3

# Turn 2
echo "User: What project am I working on?" >> alice_output.txt
response=$(curl -s -X POST "$BASE_URL/invocation" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice3",
    "run_id": "alice3-session-2",
    "query": "What project am I working on?"
  }' | jq -r '.response')
echo "Agent: $response" >> alice_output.txt
echo "" >> alice_output.txt

echo "Alice Session 2 complete. Output appended to alice_output.txt"