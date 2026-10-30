# Plan: Manual to Instruction Video

## Stage 1 — Ingestion
- Accept PDF upload or URL
- Upload PDF to Gemini via File API
- Fetch URL content with httpx

## Stage 2 — Extraction
- Send content + extraction prompt to Gemini
- Parse structured JSON response
- Validate sections/steps schema

## Stage 3 — Script Generation
- Send structured data + script prompt to Gemini
- Get scene-by-scene script with narration + visual hints
