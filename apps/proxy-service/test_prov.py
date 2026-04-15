from src.llm.providers import detect_provider, format_litellm_model
m = "openrouter/openai/gpt-4o"
p = detect_provider(m)
lt_m = format_litellm_model(m, p)
print(f"model: {m} -> provider: {p}, litellm: {lt_m}")

m2 = "openai/gpt-4o"
p2 = detect_provider(m2)
lt_m2 = format_litellm_model(m2, p2)
print(f"model: {m2} -> provider: {p2}, litellm: {lt_m2}")
