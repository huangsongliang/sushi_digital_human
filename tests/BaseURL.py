from openai import OpenAI

client = OpenAI(api_key="sk-bVGcjekiHNrL4xBt275045EbFa9a47F584A1BcC195A503Cc", base_url="https://qinzhiai.com/v1")

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    stream=False,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)

print(completion.choices[0].message)

