-- Необязательно для MVP. Требует расширение pgvector.
-- Если pgvector недоступен — этот файл молча пропускается (см. services.startup).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS semantic_memories (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding vector(1536),
  category VARCHAR(100),
  source VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
