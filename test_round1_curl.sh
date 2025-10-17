#!/bin/bash

# Correct curl command for Round 1 test
# No comments in JSON - valid JSON only

curl -X 'POST' \
  'https://22f3001854-tds-project1-dk.hf.space/handle_task' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "student@example.com",
  "secret": "YaarThachaSattaiThathaThachaSattai",
  "task": "sum-of-sales-round1-001",
  "round": 1,
  "nonce": "nonce-12345-round1-test",
  "brief": "sum-of-sales",
  "checks": [
    "Repository exists and is public",
    "GitHub Pages is enabled",
    "Page loads successfully",
    "Page displays sum of sales correctly in #total-sales element",
    "Page shows sales data in a table",
    "README.md exists and describes the project",
    "LICENSE file exists (MIT recommended)"
  ],
  "evaluation_url": "https://httpbin.org/post",
  "attachments": [
    {
      "name": "sales_data.csv",
      "url": "data:text/csv;base64,UHJvZHVjdCxTYWxlcwpMYXB0b3AsMTIwMApQaG9uZSw4NTAKU2NyZWVuLDQ1MApNb3VzZSwxMDAKS2V5Ym9hcmQsMTUw"
    }
  ]
}' | jq '.'
