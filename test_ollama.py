import ollama

resp = ollama.chat(
    model="qwen2.5:7b-instruct",
    messages=[{"role": "user", "content": "Reply with exactly: local model working"}],
)
print(resp["message"]["content"])