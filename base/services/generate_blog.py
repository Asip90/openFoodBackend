import os
import math
from openai import OpenAI


# Client DeepSeek (compatible OpenAI)
client = OpenAI(
    api_key="sk-ad38c3b5c9354003863970bfab115893",
    base_url="https://api.deepseek.com"
)


def estimate_reading_time(text):
    words = len(text.split())
    return max(1, math.ceil(words / 200))


def generate_blog_content(title, theme, tone):
    """
    Génère un article structuré IA :
    - Introduction
    - Contenu
    - Conclusion
    """

    prompt = f"""
Rédige un article de blog en français, optimisé SEO.

CONTRAINTES :
- Style clair et professionnel
- Ton : {tone}
- Thème : {theme}
- Titre : {title}

FORMAT DE SORTIE STRICT :

INTRODUCTION:
(Texte ici)

CONTENU:
(Texte ici avec sous-titres)

CONCLUSION:
(Texte ici)
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Tu es un expert en rédaction de contenu SEO."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1200,
        stream=False,
    )

    ai_text = response.choices[0].message.content.strip()

    # 🔎 Parsing sécurisé
    try:
        intro = ai_text.split("INTRODUCTION:")[1].split("CONTENU:")[0].strip()
        content = ai_text.split("CONTENU:")[1].split("CONCLUSION:")[0].strip()
        conclusion = ai_text.split("CONCLUSION:")[1].strip()
    except Exception:
        intro = ""
        content = ai_text
        conclusion = ""

    reading_time = estimate_reading_time(content)

    return intro, content, conclusion, reading_time
