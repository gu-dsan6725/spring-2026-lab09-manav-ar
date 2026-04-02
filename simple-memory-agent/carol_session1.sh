#!/bin/bash
# Carol Session 1: Different user_id from Alice
# Demonstrates multi-tenant memory isolation
BASE_URL="http://127.0.0.1:9090"

echo "=== Carol Session 1 ===" > carol_output.txt
echo "" >> carol_output.txt

# Turn 1
echo "User: Hi, I'm Carol. I'm a data scientist." >> carol_output.txt
response=$(curl -s -X POST "$BASE_URL/invocation" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "carol3",
    "run_id": "carol3-session-1",
    "query": "Hi, I'\''m Carol. I'\''m a data scientist."
  }' | jq -r '.response')
echo "Agent: $response" >> carol_output.txt
echo "" >> carol_output.txt

sleep 3

# Turn 2
echo "User: What programming languages do I like?" >> carol_output.txt
response=$(curl -s -X POST "$BASE_URL/invocation" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "carol3",
    "run_id": "carol3-session-1",
    "query": "What programming languages do I like?"
  }' | jq -r '.response')
echo "Agent: $response" >> carol_output.txt
echo "" >> carol_output.txt

sleep 3

# Turn 3
echo "User: Do you know what Alice prefers?" >> carol_output.txt
response=$(curl -s -X POST "$BASE_URL/invocation" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "carol3",
    "run_id": "carol3-session-1",
    "query": "Do you know what Alice prefers?"
  }' | jq -r '.response')
echo "Agent: $response" >> carol_output.txt
echo "" >> carol_output.txt

echo "Carol Session 1 complete. Output saved to carol_output.txt"