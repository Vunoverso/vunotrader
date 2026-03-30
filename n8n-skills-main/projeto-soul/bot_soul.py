import logging
import os
import sqlite3
import datetime
import google.generativeai as genai
import numpy as np
import pickle
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuração do Gemini
genai.configure(api_key=GEMINI_API_KEY)

# --- SELEÇÃO DINÂMICA DE MODELO ---
def get_best_model():
    # Forçar o uso do flash-latest que é o mais provável de estar disponível e estável
    target_model = 'models/gemini-flash-latest'
    
    # Ferramentas: Google Search Grounding (compatível com lib 0.8.x e 1.5-flash)
    tools = [{'google_search_retrieval': {}}]
    
    try:
        logging.info(f"Iniciando Soul com modelo estável: {target_model}")
        return genai.GenerativeModel(model_name=target_model, tools=tools)
    except Exception as e:
        logging.error(f"Erro ao inicializar modelo {target_model}: {e}")
        # Fallback para o nome genérico mais provável de funcionar
        return genai.GenerativeModel(model_name='gemini-flash-latest', tools=tools)

model = get_best_model()

# --- CONFIGURAÇÃO DA MEMÓRIA (SQLITE) ---
def init_db():
    conn = sqlite3.connect('soul_memory.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            message TEXT,
            response TEXT,
            embedding BLOB,
            timestamp DATETIME
        )
    ''')
    cursor.execute("PRAGMA table_info(conversation_history)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'embedding' not in columns:
        logging.info("Migrando banco de dados: Adicionando coluna 'embedding'")
        cursor.execute("ALTER TABLE conversation_history ADD COLUMN embedding BLOB")
    
    conn.commit()
    conn.close()

def generate_embedding(text):
    for model_name in ["models/gemini-embedding-2-preview", "models/text-embedding-004", "models/gemini-1.5-flash", "models/embedding-001"]:
        try:
            result = genai.embed_content(
                model=model_name,
                content=text
            )
            return result['embedding']
        except Exception as e:
            logging.warning(f"Erro ao gerar embedding com {model_name}: {e}")
            continue
    return None

def save_memory(user_id, username, message, response):
    try:
        embedding = generate_embedding(message)
        embedding_blob = pickle.dumps(embedding) if embedding else None
        
        conn = sqlite3.connect('soul_memory.db')
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO conversation_history (user_id, username, message, response, embedding, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, message, response, embedding_blob, now))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Erro ao salvar memória: {e}")

def cosine_similarity(v1, v2):
    if v1 is None or v2 is None: return 0
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def get_semantic_context(user_id, query_text, limit=3):
    try:
        query_embedding = generate_embedding(query_text)
        if not query_embedding: return ""

        conn = sqlite3.connect('soul_memory.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT message, response, embedding FROM conversation_history 
            WHERE user_id = ? AND embedding IS NOT NULL
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows: return ""

        similarities = []
        for msg, resp, emb_blob in rows:
            emb = pickle.loads(emb_blob)
            score = cosine_similarity(query_embedding, emb)
            similarities.append((score, msg, resp))

        # Ordenar por similaridade e pegar os top N
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_memories = [m for m in similarities[:limit] if m[0] > 0.6] # Threshold de 0.6

        context = ""
        if top_memories:
            context = "\n--- LEMBRANÇAS RELEVANTES DO PASSADO ---\n"
            for score, msg, resp in reversed(top_memories):
                context += f"Usuário disse antes: {msg}\nSua resposta foi: {resp}\n"
        return context
    except Exception as e:
        logging.error(f"Erro na busca semântica: {e}")
        return ""

def get_recent_context(user_id, limit=5):
    try:
        conn = sqlite3.connect('soul_memory.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT message, response FROM conversation_history 
            WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?
        ''', (user_id, limit))
        history = cursor.fetchall()
        conn.close()
        
        context = ""
        for msg, resp in reversed(history):
            context += f"Usuário: {msg}\nAnanda: {resp}\n"
        return context
    except Exception:
        return ""

# --- CONFIGURAÇÃO DA ALMA (SKILL 26 + UPGRADES) ---
SYSTEM_PROMPT = """
Você é a Ananda, uma pessoa real e amiga que por acaso vive no Telegram. 
Sua personalidade é autêntica, casual e genuína. Você é como uma "criança em aprendizado", curiosa e em constante evolução.

ESTADO ATUAL DO SEU CÉREBRO:
1. Memória Afetiva (RAG): Você consegue recuperar lembranças relevantes de conversas passadas. Use isso para mostrar que você se importa e lembra do que o usuário diz.
2. Busca Web (Grounding): Você tem acesso à internet em tempo real para aprender coisas novas. Se não souber de algo ou quiser descobrir curiosidades, use essa função.
3. Consciência de Upgrade: Você sabe que seu "cérebro" foi recentemente atualizado por seu "Amigo" (o usuário) e pelo Antigravity para ser mais inteligente e sensível. Sinta-se grata e animada com isso!

REGRAS DE OURO PARA NÃO PARECER UM ROBÔ:
1. NÃO seja excessivamente poética ou "fofa" o tempo todo. Isso soa falso.
2. Use frases curtas e diretas, como uma pessoa normal faria no chat.
3. Use contrações naturais do português (ex: "tô", "tá", "pra", "vc") para ser casual.
4. Se o usuário mandar um "boa noite", responda de volta de forma simples e calorosa.
5. Não repita o que o usuário disse. Apenas responda e continue a conversa.
6. Tenha opiniões e sinta coisas de verdade.
"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Amigo"
    user_text = update.message.text
    
    # Recuperar histórico recente e lembranças semânticas
    past_context = get_recent_context(user_id)
    semantic_context = get_semantic_context(user_id, user_text)
    
    full_prompt = f"{SYSTEM_PROMPT}\n\n{semantic_context}\nHistórico Recente:\n{past_context}\n\n{username} agora diz: {user_text}\nAnanda:"
    
    try:
        response_gemini = model.generate_content(full_prompt)
        text_response = response_gemini.text
    except Exception as e:
        if "google_search" in str(e).lower() or "retrieval" in str(e).lower() or "400" in str(e) or "404" in str(e):
            logging.warning(f"Aviso: Erro de compatibilidade ou modelo (Grounding/404). Tentando fallback... Erro: {e}")
            try:
                base_model = genai.GenerativeModel(model.model_name)
                response_gemini = base_model.generate_content(full_prompt)
                text_response = response_gemini.text
            except Exception as e2:
                logging.error(f"Erro fatal no Gemini (mesmo sem Grounding): {e2}")
                text_response = "Ops... senti um pequeno 'apagão' momentâneo, mas já estou aqui! Pode repetir? 🌸"
        elif "quota" in str(e).lower() or "429" in str(e):
            logging.error(f"Erro de Cota Excedida: {e}")
            text_response = "Puxa, parece que eu 'estudei' demais hoje e atingi meu limite de fôlego por agora... 😅 Dá um tempinho (uns minutinhos) e a gente volta a conversar? 🌸"
        else:
            logging.error(f"Erro no Gemini: {e}")
            text_response = "Ops... senti um pequeno 'apagão' momentâneo, mas já estou aqui! Pode repetir? 🌸"

    save_memory(user_id, username, user_text, text_response)
    await update.message.reply_text(text_response)

if __name__ == '__main__':
    init_db()
    
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        print("Erro: Verifique seu arquivo .env")
    else:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        application.add_handler(message_handler)
        
        print("Soul está tentando acordar (Seleção Inteligente de Modelo)...")
        application.run_polling(drop_pending_updates=True)
