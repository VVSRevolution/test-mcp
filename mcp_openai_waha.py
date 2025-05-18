# arquivo: mcp_openai_waha.py
import requests
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

# CONFIGURAÇÃO
WAHA_URL = "http://localhost:3000/api/sendText"
SESSION = "default"
openai_api_key = "key"  # Substitua pela sua chave real da OpenAI

# Instancia cliente OpenAI
client = OpenAI(api_key=openai_api_key)

# === MCP SERVER ===
app = FastAPI()

# === Resource: contatos ===
contatos = {
    "João": "556232432020",
}

@app.get("/resources/contatos")
def get_contatos():
    return [{"nome": nome, "numero": numero} for nome, numero in contatos.items()]

# === Tool: send_message ===
class SendMessageRequest(BaseModel):
    number: str
    text: str

@app.post("/tools/send_message")
def send_message(req: SendMessageRequest):
    payload = {
        "chatId": f"{req.number}@c.us",
        "text": req.text,
        "session": SESSION
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.post(WAHA_URL, json=payload, headers=headers)
    return response.json()

# === MCP Describe ===
@app.get("/mcp/describe")
def mcp_describe():
    return {
        "tools": [
            {
                "name": "send_message",
                "description": "Envia mensagem via WhatsApp usando WaHa.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "string", "description": "Número internacional, ex: +5511999990001"},
                        "text": {"type": "string", "description": "Mensagem a ser enviada"}
                    },
                    "required": ["number", "text"]
                },
                "url": "/tools/send_message"
            }
        ],
        "resources": [
            {
                "name": "contatos",
                "description": "Contatos pré-definidos com nomes e números.",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nome": {"type": "string"},
                            "numero": {"type": "string"}
                        }
                    }
                },
                "url": "/resources/contatos"
            }
        ]
    }

# === Integração com ChatGPT ===
class PromptRequest(BaseModel):
    prompt: str
    
@app.post("/chatgpt/interpretar")
def interpretar_prompt(req: PromptRequest):
    try:
        contatos_string = ", ".join([f"{nome}: {num}" for nome, num in contatos.items()])
        system_prompt = f"Você é um assistente que envia mensagens via WhatsApp. Os contatos disponíveis são: {contatos_string}."

        functions = [
            {
                "name": "send_message",
                "description": "Envia uma mensagem via WhatsApp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "string", "description": "Número do destinatário"},
                        "text": {"type": "string", "description": "Conteúdo da mensagem"}
                    },
                    "required": ["number", "text"]
                }
            }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            functions=functions,
            function_call="auto"
        )

        choice = response.choices[0]
        if choice.finish_reason == "function_call":
            args = eval(choice.message.function_call.arguments)
            number = args["number"]
            text = args["text"]
            return send_message(SendMessageRequest(number=number, text=text))

        return {"erro": "ChatGPT não entendeu o comando."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))