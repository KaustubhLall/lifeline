import os
import openai

def call_llm_text(prompt, model="gpt-4.1-nano", temperature=0.0):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message["content"]

def call_llm_transcribe(audio_file_path, model="gpt-4o-mini"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    with open(audio_file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe(model, audio_file)
    return transcript["text"]

def call_llm_TTS(text, model="tts-1", voice="alloy"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.Audio.create(
        model=model,
        input=text,
        voice=voice,
        response_format="mp3"
    )
    return response
