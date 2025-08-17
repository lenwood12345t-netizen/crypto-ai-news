import os
print("INGESTOR: starting…")
print("PG_DSN present?", "yes" if os.getenv("PG_DSN") else "no")
print("OPENAI_API_KEY present?", "yes" if os.getenv("OPENAI_API_KEY") else "no")
print("OPENAI_MODEL:", os.getenv("OPENAI_MODEL", "not set"))
print("INGESTOR: done.")
