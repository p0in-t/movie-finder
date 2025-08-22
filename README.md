# Movie Finder – Generative AI Movie Recommender

**Movie Finder** is a full-stack AI application that recommends movies based on semantic similarity, themes, and natural-language queries.  
It combines **embeddings**, **retrieval-augmented generation (RAG)**, and **LLM orchestration (LangGraph/LangChain)** to deliver conversational recommendations.

---

## Features
- **Movie similarity search** using embeddings and vector indexing (FAISS + PostgreSQL)
- **Chat-based recommendations** powered by LLMs with LangGraph orchestration
- **Multi-label classification** of IMDb reviews (themes, narrative, atmosphere) using a fine-tuned RoBERTa model
- **Full-stack app**: React + TypeScript frontend, FastAPI backend with JWT authentication
- **Cloud-deployed** on Vercel (frontend) and Google Cloud Run + Cloud SQL (backend + DB)

---

## Tech Stack
- **Frontend:** React, TypeScript  
- **Backend:** FastAPI, JWT, Python  
- **ML/NLP:** Hugging Face Transformers (RoBERTa), embeddings, FAISS, RAG  
- **Orchestration:** LangGraph, LangChain  
- **Database:** PostgreSQL  
- **Deployment:** Vercel, Google Cloud Run, Cloud SQL  

---

## Repository Structure

```
movie-finder/
├── client/                                   # React + TypeScript frontend
├── server/                                   # FastAPI backend with JWT auth
├── movie_dataset_pipeline/                   # Data collection, processing & classification pipeline
```
---

## Future Improvements

- Add support for LlamaIndex and other vector DBs (Pinecone, Chroma)

- Improve recommendation diversity with hybrid search
  
- Expand classified parameters for better similarity search
