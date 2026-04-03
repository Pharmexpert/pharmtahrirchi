# Pharma Expert Backend Server

FastAPI backend for the Pharma Translation Platform.

## Features
- AI-powered pharmaceutical document translation (Gemini 2.0)
- BERT-based contextual word suggestions
- 8.7M Uzbek word dictionary (spell checking)
- Sayqallash correction engine (4000+ rules)
- FAISS vector search for semantic matching

## Deployment
Deploy to Railway with:
1. Connect this repo to Railway
2. Set environment variables
3. Railway will auto-detect Python and deploy

## Environment Variables
- `GOOGLE_API_KEY` - Google Generative AI key
- `PORT` - Server port (auto-set by Railway)
