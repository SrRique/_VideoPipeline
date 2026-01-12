"""
Venn Studios - Pipeline Completo
Gerador de Sprites + Áudios + XML para Premiere
"""

from flask import Flask, render_template_string, request, jsonify
import os
import re
import json
import threading
import time
import base64
from datetime import datetime
from tkinter import Tk, filedialog
from mutagen.mp3 import MP3

app = Flask(__name__)

# Arquivo de configuração
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_venn.json")

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "elevenlabs_api_key": "",
    "pasta_fotos": "",
    "pasta_sprites": "",
    "pasta_audios": "",
    "pasta_xml": "",
    "modelo_audio": "eleven_multilingual_v2",
    "idioma": "en",
    "resolucao_width": 1920,
    "resolucao_height": 1080,
    "sprite_x": 1600,
    "sprite_y": 800,
    "sprite_scale": 100,
    "prompt_base": """Create a pixel art portrait in Stardew Valley style based on this photo. The character should appear from the chest up, including visible arms and hands to help with expressiveness.

Visual style:
- Pixel art with limited and vibrant color palette
- Slightly caricatured proportions (slightly larger head)
- Clean and well-defined lines
- Transparent background or simple solid color
- Resolution approximately 128x128 or 256x256 pixels

The character's emotion is: {emocao}

{descricao}""",
    "emocoes": {
        "neutro": "Relaxed and attentive expression, as if having a normal conversation. Eyes naturally open, mouth closed or with slight smile. Arms in natural position, one hand may be slightly visible resting.",
        "feliz": "Wide and genuine smile, eyes slightly closed with joy (arc shape). Raised eyebrows. One hand may be giving a thumbs up or both hands raised in celebration.",
        "pensativo": "Eyes slightly looking up or to the side, eyebrows slightly furrowed in concentration. One hand touching chin or side of face, as if reflecting on something.",
        "frustrado": "Furrowed eyebrows, tense mouth or slightly down. One hand on forehead or both hands holding head in sign of stress. Eyes may be half-closed from tiredness/irritation.",
        "surpreso": "Wide open eyes (larger than normal), eyebrows raised high, mouth open in O shape. Both hands raised at face height with open palms, or one hand covering mouth.",
        "orgulhoso": "Confident smile (not as wide as happy, more contained), eyes slightly closed in satisfaction, chin slightly raised. Arms crossed or one hand on chest in gesture of pride.",
        "cansado": "Half-closed eyes or heavy eyelids, subtle dark circles, relaxed/droopy eyebrows. Neutral mouth or slightly open in yawn. One hand may be supporting face or rubbing eyes.",
        "rindo": "Eyes closed in happy arc shape, mouth wide open showing laughter. Shoulders raised and one or both hands near face or belly, indicating genuine laughter."
    }
}

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Merge com defaults para novos campos
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except:
            pass
    return DEFAULT_CONFIG.copy()

def salvar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# Estado global
progresso = {"atual": 0, "total": 0, "status": "", "erro": None, "concluido": False}
resultados = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Venn Studios - Pipeline</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        .header {
            background: rgba(0,0,0,0.3);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid #ffd700;
        }
        .header h1 { color: #ffd700; margin-bottom: 5px; }
        .header p { color: #aaa; }
        .tabs {
            display: flex;
            background: rgba(0,0,0,0.2);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }
        .tab:hover { background: rgba(255,215,0,0.1); }
        .tab.active {
            background: rgba(255,215,0,0.2);
            border-bottom-color: #ffd700;
        }
        .tab-content { display: none; padding: 20px; max-width: 1000px; margin: 0 auto; }
        .tab-content.active { display: block; }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .card h2 { color: #ffd700; margin-bottom: 15px; font-size: 1.2em; }
        label { display: block; margin-bottom: 8px; color: #ccc; }
        input[type="text"], input[type="password"], input[type="number"], select, textarea {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            margin-bottom: 15px;
            font-family: inherit;
        }
        textarea { min-height: 150px; resize: vertical; font-family: 'Consolas', monospace; }
        select option { background: #1a1a2e; }
        .row { display: flex; gap: 15px; }
        .row > * { flex: 1; }
        .row-3 > * { flex: 1; }
        .input-com-botao { display: flex; gap: 10px; margin-bottom: 15px; }
        .input-com-botao input { flex: 1; margin-bottom: 0; }
        .btn {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: bold;
        }
        .btn-primary {
            background: linear-gradient(135deg, #ffd700 0%, #ff8c00 100%);
            color: #1a1a2e;
            width: 100%;
            padding: 15px;
            font-size: 1.1em;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(255,215,0,0.4); }
        .btn-primary:disabled { background: #666; cursor: not-allowed; transform: none; }
        .btn-secondary {
            background: rgba(255,215,0,0.3);
            color: #fff;
        }
        .btn-secondary:hover { background: rgba(255,215,0,0.5); }
        .btn-outline {
            background: transparent;
            border: 1px solid rgba(255,255,255,0.3);
            color: #fff;
        }
        .btn-outline:hover { background: rgba(255,255,255,0.1); }
        .checkbox-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            cursor: pointer;
        }
        .checkbox-item:hover { background: rgba(255,215,0,0.2); }
        .checkbox-item input { width: 18px; height: 18px; }
        .progresso { display: none; margin-top: 20px; }
        .progresso.ativo { display: block; }
        .barra-progresso {
            height: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .barra-progresso-inner {
            height: 100%;
            background: linear-gradient(90deg, #ffd700, #ff8c00);
            transition: width 0.3s;
        }
        .status-text { text-align: center; color: #aaa; }
        .erro {
            background: rgba(255,0,0,0.2);
            border: 1px solid #ff4444;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
        }
        .erro.ativo { display: block; }
        .sucesso {
            background: rgba(0,255,0,0.2);
            border: 1px solid #44ff44;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
        }
        .sucesso.ativo { display: block; }
        .info-box {
            background: rgba(0,150,255,0.2);
            border: 1px solid #4488ff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 0.9em;
        }
        .vozes-lista {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            max-height: 120px;
            overflow-y: auto;
        }
        .foto-status {
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 0.9em;
        }
        .foto-encontrada { background: rgba(0,255,0,0.2); border: 1px solid #44ff44; }
        .foto-nao-encontrada { background: rgba(255,0,0,0.2); border: 1px solid #ff4444; }
        .foto-aguardando { background: rgba(255,255,255,0.1); border: 1px solid #666; }
        .emocao-editor {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }
        .emocao-editor h4 { color: #ffd700; margin-bottom: 10px; text-transform: capitalize; }
        .emocao-editor textarea { min-height: 80px; margin-bottom: 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎮 Super economizador de tempo venn studios by henrique anselmo</h1>
        <p>Gerador de Sprites, Áudios e XML para Premiere</p>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('sprites')">🎨 Sprites</div>
        <div class="tab" onclick="showTab('audios')">🎙️ Áudios</div>
        <div class="tab" onclick="showTab('xml')">🎬 XML Premiere</div>
        <div class="tab" onclick="showTab('config')">⚙️ Configurações</div>
    </div>
    
    <!-- TAB SPRITES -->
    <div id="tab-sprites" class="tab-content active">
        <div class="card">
            <h2>🔑 API Key do Gemini</h2>
            <input type="password" id="geminiApiKey" placeholder="Sua API key do Google AI Studio">
        </div>
        
        <div class="card">
            <h2>📁 Pastas</h2>
            <label>Pasta das fotos (onde estão as fotos dos membros):</label>
            <div class="input-com-botao">
                <input type="text" id="pastaFotos" placeholder="Ex: C:/Users/Henrique/Desktop/fotos_equipe">
                <button class="btn btn-secondary" onclick="procurarPasta('pastaFotos')">📂 Procurar</button>
            </div>
            <label>Pasta de saída (onde salvar os sprites):</label>
            <div class="input-com-botao">
                <input type="text" id="pastaSpritesOutput" placeholder="Ex: C:/Users/Henrique/Desktop/sprites">
                <button class="btn btn-secondary" onclick="procurarPasta('pastaSpritesOutput')">📂 Procurar</button>
            </div>
        </div>
        
        <div class="card">
            <h2>👤 Membro da Equipe</h2>
            <label>Nome do membro (deve corresponder ao nome do arquivo da foto):</label>
            <input type="text" id="nomeMembro" placeholder="Ex: henrique" oninput="verificarFoto()">
            <div id="fotoStatus" class="foto-status foto-aguardando">
                Digite o nome do membro para verificar se a foto existe
            </div>
        </div>
        
        <div class="card">
            <h2>😊 Emoções</h2>
            <button class="btn btn-outline" onclick="toggleTodasEmocoes()" style="margin-bottom: 15px;">Selecionar/Desmarcar Todas</button>
            <div class="checkbox-grid" id="emocoesGrid"></div>
        </div>
        
        <button class="btn btn-primary" id="btnGerarSprites" onclick="gerarSprites()">🚀 Gerar Sprites</button>
        
        <div class="progresso" id="progressoSprites">
            <div class="barra-progresso"><div class="barra-progresso-inner" id="barraSprites" style="width: 0%"></div></div>
            <p class="status-text" id="statusSprites">Iniciando...</p>
        </div>
        <div class="erro" id="erroSprites"></div>
        <div class="sucesso" id="sucessoSprites"></div>
    </div>
    
    <!-- TAB AUDIOS -->
    <div id="tab-audios" class="tab-content">
        <div class="card">
            <h2>🔑 API Key do ElevenLabs</h2>
            <div class="row">
                <div>
                    <input type="password" id="elevenlabsApiKey" placeholder="Sua API key do ElevenLabs">
                </div>
                <div>
                    <button class="btn btn-secondary" onclick="carregarVozes()" style="width: 100%; height: 46px;">🔄 Carregar Vozes</button>
                </div>
            </div>
            <div class="vozes-lista" id="vozesLista">
                <p style="color: #888;">Clique em "Carregar Vozes" para ver as vozes disponíveis</p>
            </div>
        </div>
        
        <div class="card">
            <h2>🎛️ Configurações de Áudio</h2>
            <div class="row">
                <div>
                    <label>Modelo de voz:</label>
                    <select id="modeloAudio">
                        <option value="eleven_multilingual_v2">Multilingual v2 (Natural)</option>
                        <option value="eleven_v3">Eleven v3 (Mais avançado)</option>
                        <option value="eleven_turbo_v2_5">Turbo v2.5 (Rápido)</option>
                        <option value="eleven_flash_v2_5">Flash v2.5 (Ultra rápido)</option>
                    </select>
                </div>
                <div>
                    <label>Idioma:</label>
                    <select id="idiomaAudio">
                        <option value="en">English</option>
                        <option value="pt">Português</option>
                        <option value="es">Español</option>
                        <option value="fr">Français</option>
                        <option value="de">Deutsch</option>
                        <option value="it">Italiano</option>
                        <option value="ja">日本語</option>
                    </select>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📁 Pasta de Saída</h2>
            <div class="row">
                <div class="input-com-botao" style="flex: 2;">
                    <input type="text" id="pastaAudiosOutput" placeholder="Ex: C:/Users/Henrique/Desktop/audios" style="margin-bottom: 0;">
                    <button class="btn btn-secondary" onclick="procurarPasta('pastaAudiosOutput')">📂 Procurar</button>
                </div>
                <div>
                    <input type="text" id="nomePastaAudio" placeholder="Nome da pasta (ex: episodio_01)">
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📝 Roteiro</h2>
            <div class="info-box">
                <strong>Formato:</strong> [personagem - emoção] "Texto da fala"<br>
                O nome do personagem deve ser igual ao nome da voz no ElevenLabs
            </div>
            <button class="btn btn-outline" onclick="carregarExemploRoteiro()" style="margin-right: 10px; margin-bottom: 15px;">📄 Carregar Exemplo</button>
            <button class="btn btn-outline" onclick="document.getElementById('roteiroAudio').value=''" style="margin-bottom: 15px;">🗑️ Limpar</button>
            <textarea id="roteiroAudio" placeholder="Cole ou escreva seu roteiro aqui..."></textarea>
        </div>
        
        <button class="btn btn-primary" id="btnGerarAudios" onclick="gerarAudios()">🚀 Gerar Áudios</button>
        
        <div class="progresso" id="progressoAudios">
            <div class="barra-progresso"><div class="barra-progresso-inner" id="barraAudios" style="width: 0%"></div></div>
            <p class="status-text" id="statusAudios">Iniciando...</p>
        </div>
        <div class="erro" id="erroAudios"></div>
        <div class="sucesso" id="sucessoAudios"></div>
    </div>
    
    <!-- TAB XML -->
    <div id="tab-xml" class="tab-content">
        <div class="card">
            <h2>📁 Pastas de Entrada</h2>
            <label>Pasta dos áudios (que contém timestamps.json):</label>
            <div class="input-com-botao">
                <input type="text" id="pastaAudiosInput" placeholder="Ex: C:/audios/episodio_01">
                <button class="btn btn-secondary" onclick="procurarPasta('pastaAudiosInput')">📂 Procurar</button>
            </div>
            <label>Pasta dos sprites:</label>
            <div class="input-com-botao">
                <input type="text" id="pastaSpritesInput" placeholder="Ex: C:/sprites/henrique">
                <button class="btn btn-secondary" onclick="procurarPasta('pastaSpritesInput')">📂 Procurar</button>
            </div>
            <label>Pasta de saída do XML:</label>
            <div class="input-com-botao">
                <input type="text" id="pastaXmlOutput" placeholder="Ex: C:/premiere/projetos">
                <button class="btn btn-secondary" onclick="procurarPasta('pastaXmlOutput')">📂 Procurar</button>
            </div>
        </div>
        
        <div class="card">
            <h2>🎬 Configurações da Sequência</h2>
            <div class="row">
                <div>
                    <label>Nome da sequência:</label>
                    <input type="text" id="nomeSequencia" placeholder="Ex: Venn_Ep01_Narracao">
                </div>
                <div>
                    <label>Largura (px):</label>
                    <input type="number" id="resolucaoWidth" value="1920">
                </div>
                <div>
                    <label>Altura (px):</label>
                    <input type="number" id="resolucaoHeight" value="1080">
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🖼️ Posição do Sprite</h2>
            <div class="row">
                <div>
                    <label>Posição X:</label>
                    <input type="number" id="spriteX" value="1600">
                </div>
                <div>
                    <label>Posição Y:</label>
                    <input type="number" id="spriteY" value="800">
                </div>
                <div>
                    <label>Escala (%):</label>
                    <input type="number" id="spriteScale" value="100">
                </div>
            </div>
            <p style="color: #888; font-size: 0.85em; margin-top: 10px;">
                💡 Para 1920x1080: Centro = 960,540 | Canto inferior direito ≈ 1600,800
            </p>
        </div>
        
        <button class="btn btn-primary" id="btnGerarXml" onclick="gerarXml()">🚀 Gerar XML</button>
        
        <div class="progresso" id="progressoXml">
            <div class="barra-progresso"><div class="barra-progresso-inner" id="barraXml" style="width: 0%"></div></div>
            <p class="status-text" id="statusXml">Gerando...</p>
        </div>
        <div class="erro" id="erroXml"></div>
        <div class="sucesso" id="sucessoXml"></div>
    </div>
    
    <!-- TAB CONFIG -->
    <div id="tab-config" class="tab-content">
        <div class="card">
            <h2>📝 Prompt Base para Sprites</h2>
            <p style="color: #888; margin-bottom: 15px;">Use {emocao} e {descricao} como placeholders</p>
            <textarea id="promptBase" style="min-height: 200px;"></textarea>
        </div>
        
        <div class="card">
            <h2>😊 Descrições das Emoções</h2>
            <p style="color: #888; margin-bottom: 15px;">Edite as descrições de cada emoção para o prompt</p>
            <div id="emocoesEditorContainer"></div>
        </div>
        
        <button class="btn btn-primary" onclick="salvarConfiguracoes()">💾 Salvar Configurações</button>
        <div class="sucesso" id="sucessoConfig" style="margin-top: 15px;"></div>
    </div>
    
    <script>
        let config = {};
        let vozes = [];
        let fotoEncontrada = false;
        let fotoPath = "";
        
        // ===== INICIALIZAÇÃO =====
        window.onload = async function() {
            await carregarConfig();
            renderizarEmocoes();
            renderizarEditorEmocoes();
        };
        
        async function carregarConfig() {
            try {
                const response = await fetch('/config');
                config = await response.json();
                
                // Preenche campos
                document.getElementById('geminiApiKey').value = config.gemini_api_key || '';
                document.getElementById('elevenlabsApiKey').value = config.elevenlabs_api_key || '';
                document.getElementById('pastaFotos').value = config.pasta_fotos || '';
                document.getElementById('pastaSpritesOutput').value = config.pasta_sprites || '';
                document.getElementById('pastaAudiosOutput').value = config.pasta_audios || '';
                document.getElementById('pastaXmlOutput').value = config.pasta_xml || '';
                document.getElementById('modeloAudio').value = config.modelo_audio || 'eleven_multilingual_v2';
                document.getElementById('idiomaAudio').value = config.idioma || 'en';
                document.getElementById('resolucaoWidth').value = config.resolucao_width || 1920;
                document.getElementById('resolucaoHeight').value = config.resolucao_height || 1080;
                document.getElementById('spriteX').value = config.sprite_x || 1600;
                document.getElementById('spriteY').value = config.sprite_y || 800;
                document.getElementById('spriteScale').value = config.sprite_scale || 100;
                document.getElementById('promptBase').value = config.prompt_base || '';
            } catch (err) {
                console.error('Erro ao carregar config:', err);
            }
        }
        
        // ===== TABS =====
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab:nth-child(${['sprites','audios','xml','config'].indexOf(tabName)+1})`).classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
        }
        
        // ===== UTILIDADES =====
        async function procurarPasta(inputId) {
            try {
                const response = await fetch('/selecionar-pasta');
                const data = await response.json();
                if (data.pasta) {
                    document.getElementById(inputId).value = data.pasta;
                    if (inputId === 'pastaFotos') verificarFoto();
                    salvarConfigAuto();
                }
            } catch (err) {
                console.error('Erro ao selecionar pasta:', err);
            }
        }
        
        async function salvarConfigAuto() {
            const configData = {
                gemini_api_key: document.getElementById('geminiApiKey').value,
                elevenlabs_api_key: document.getElementById('elevenlabsApiKey').value,
                pasta_fotos: document.getElementById('pastaFotos').value,
                pasta_sprites: document.getElementById('pastaSpritesOutput').value,
                pasta_audios: document.getElementById('pastaAudiosOutput').value,
                pasta_xml: document.getElementById('pastaXmlOutput').value,
                modelo_audio: document.getElementById('modeloAudio').value,
                idioma: document.getElementById('idiomaAudio').value,
                resolucao_width: parseInt(document.getElementById('resolucaoWidth').value),
                resolucao_height: parseInt(document.getElementById('resolucaoHeight').value),
                sprite_x: parseInt(document.getElementById('spriteX').value),
                sprite_y: parseInt(document.getElementById('spriteY').value),
                sprite_scale: parseInt(document.getElementById('spriteScale').value),
                prompt_base: document.getElementById('promptBase').value,
                emocoes: config.emocoes
            };
            
            await fetch('/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });
        }
        
        // ===== SPRITES =====
        function renderizarEmocoes() {
            const grid = document.getElementById('emocoesGrid');
            const emocoes = Object.keys(config.emocoes || {});
            grid.innerHTML = emocoes.map(e => `
                <label class="checkbox-item">
                    <input type="checkbox" name="emocao" value="${e}" checked>
                    ${e.charAt(0).toUpperCase() + e.slice(1)}
                </label>
            `).join('');
        }
        
        function toggleTodasEmocoes() {
            const checkboxes = document.querySelectorAll('input[name="emocao"]');
            const todasMarcadas = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => cb.checked = !todasMarcadas);
        }
        
        async function verificarFoto() {
            const nome = document.getElementById('nomeMembro').value.trim().toLowerCase();
            const pastaFotos = document.getElementById('pastaFotos').value.trim();
            const statusDiv = document.getElementById('fotoStatus');
            
            if (!nome || !pastaFotos) {
                statusDiv.className = 'foto-status foto-aguardando';
                statusDiv.textContent = 'Digite o nome do membro e selecione a pasta das fotos';
                fotoEncontrada = false;
                return;
            }
            
            try {
                const response = await fetch(`/verificar-foto?nome=${encodeURIComponent(nome)}&pasta=${encodeURIComponent(pastaFotos)}`);
                const data = await response.json();
                
                if (data.encontrada) {
                    statusDiv.className = 'foto-status foto-encontrada';
                    statusDiv.textContent = `✅ Foto encontrada: ${data.arquivo}`;
                    fotoEncontrada = true;
                    fotoPath = data.caminho;
                } else {
                    statusDiv.className = 'foto-status foto-nao-encontrada';
                    statusDiv.textContent = `❌ Foto não encontrada. Procurando por: ${nome}.jpg, ${nome}.png, ${nome}.jpeg`;
                    fotoEncontrada = false;
                }
            } catch (err) {
                statusDiv.className = 'foto-status foto-nao-encontrada';
                statusDiv.textContent = '❌ Erro ao verificar foto';
                fotoEncontrada = false;
            }
        }
        
        async function gerarSprites() {
            const apiKey = document.getElementById('geminiApiKey').value;
            const nome = document.getElementById('nomeMembro').value.trim().toLowerCase();
            const pastaOutput = document.getElementById('pastaSpritesOutput').value;
            const emocoes = Array.from(document.querySelectorAll('input[name="emocao"]:checked')).map(cb => cb.value);
            
            if (!apiKey) { alert('Digite a API key do Gemini'); return; }
            if (!nome) { alert('Digite o nome do membro'); return; }
            if (!pastaOutput) { alert('Selecione a pasta de saída'); return; }
            if (!fotoEncontrada) { alert('Foto não encontrada'); return; }
            if (emocoes.length === 0) { alert('Selecione pelo menos uma emoção'); return; }
            
            document.getElementById('btnGerarSprites').disabled = true;
            document.getElementById('progressoSprites').classList.add('ativo');
            document.getElementById('erroSprites').classList.remove('ativo');
            document.getElementById('sucessoSprites').classList.remove('ativo');
            
            await salvarConfigAuto();
            
            try {
                await fetch('/gerar-sprites', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: apiKey,
                        nome: nome,
                        pasta_output: pastaOutput,
                        foto_path: fotoPath,
                        emocoes: emocoes,
                        prompt_base: config.prompt_base,
                        emocoes_descricao: config.emocoes
                    })
                });
                verificarProgresso('Sprites');
            } catch (err) {
                mostrarErro('Sprites', err.message);
            }
        }
        
        // ===== ÁUDIOS =====
        async function carregarVozes() {
            const apiKey = document.getElementById('elevenlabsApiKey').value;
            if (!apiKey) { alert('Digite a API key primeiro'); return; }
            
            const lista = document.getElementById('vozesLista');
            lista.innerHTML = '<p style="color: #888;">Carregando vozes...</p>';
            
            try {
                const response = await fetch('/carregar-vozes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: apiKey })
                });
                const data = await response.json();
                
                if (data.erro) {
                    lista.innerHTML = `<p style="color: #ff4444;">${data.erro}</p>`;
                    return;
                }
                
                vozes = data.vozes;
                lista.innerHTML = vozes.map(v => `<div style="padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.1);"><span style="color: #ffd700;">${v.nome}</span></div>`).join('');
                salvarConfigAuto();
            } catch (err) {
                lista.innerHTML = `<p style="color: #ff4444;">Erro: ${err.message}</p>`;
            }
        }
        
        function carregarExemploRoteiro() {
            document.getElementById('roteiroAudio').value = `[henrique - neutro] "Hey everyone, welcome to the Venn Studios channel."

[henrique - feliz] "Today we're going to tell you how it all started and how we're developing Rogue Reigns."

[henrique - pensativo] "You know, when we started this project, we had no idea where it would go."

[henrique - frustrado] "There was a time when we spent three weeks trying to fix a single bug. Three weeks!"

[henrique - surpreso] "And out of nowhere, we discovered the problem was a comma in the wrong place. A comma!"

[henrique - rindo] "We laughed a lot afterwards, but at the time it wasn't funny at all."

[henrique - orgulhoso] "But look where we've come. The game is taking shape and it's looking incredible."

[henrique - cansado] "Of course there are hard days, sleepless nights, lots of coffee involved."

[henrique - feliz] "But it's worth every second. And you're going to follow this whole journey with us!"

[henrique - neutro] "So subscribe to the channel, hit the bell, and come along on this journey."`;
        }
        
        async function gerarAudios() {
            const apiKey = document.getElementById('elevenlabsApiKey').value;
            const pastaOutput = document.getElementById('pastaAudiosOutput').value;
            const nomePasta = document.getElementById('nomePastaAudio').value.trim();
            const modelo = document.getElementById('modeloAudio').value;
            const idioma = document.getElementById('idiomaAudio').value;
            const roteiro = document.getElementById('roteiroAudio').value;
            
            if (!apiKey) { alert('Digite a API key'); return; }
            if (!pastaOutput) { alert('Selecione a pasta de saída'); return; }
            if (!nomePasta) { alert('Digite o nome da pasta'); return; }
            if (!roteiro.trim()) { alert('Digite o roteiro'); return; }
            
            document.getElementById('btnGerarAudios').disabled = true;
            document.getElementById('progressoAudios').classList.add('ativo');
            document.getElementById('erroAudios').classList.remove('ativo');
            document.getElementById('sucessoAudios').classList.remove('ativo');
            
            await salvarConfigAuto();
            
            try {
                await fetch('/gerar-audios', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: apiKey,
                        pasta_output: pastaOutput,
                        nome_pasta: nomePasta,
                        modelo: modelo,
                        idioma: idioma,
                        roteiro: roteiro
                    })
                });
                verificarProgresso('Audios');
            } catch (err) {
                mostrarErro('Audios', err.message);
            }
        }
        
        // ===== XML =====
        async function gerarXml() {
            const pastaAudios = document.getElementById('pastaAudiosInput').value;
            const pastaSprites = document.getElementById('pastaSpritesInput').value;
            const pastaOutput = document.getElementById('pastaXmlOutput').value;
            const nome = document.getElementById('nomeSequencia').value.trim() || 'Venn_Sequencia';
            const width = parseInt(document.getElementById('resolucaoWidth').value);
            const height = parseInt(document.getElementById('resolucaoHeight').value);
            const spriteX = parseInt(document.getElementById('spriteX').value);
            const spriteY = parseInt(document.getElementById('spriteY').value);
            const spriteScale = parseInt(document.getElementById('spriteScale').value);
            
            if (!pastaAudios) { alert('Selecione a pasta dos áudios'); return; }
            if (!pastaSprites) { alert('Selecione a pasta dos sprites'); return; }
            if (!pastaOutput) { alert('Selecione a pasta de saída'); return; }
            
            document.getElementById('btnGerarXml').disabled = true;
            document.getElementById('progressoXml').classList.add('ativo');
            document.getElementById('erroXml').classList.remove('ativo');
            document.getElementById('sucessoXml').classList.remove('ativo');
            
            await salvarConfigAuto();
            
            try {
                const response = await fetch('/gerar-xml', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        pasta_audios: pastaAudios,
                        pasta_sprites: pastaSprites,
                        pasta_output: pastaOutput,
                        nome_sequencia: nome,
                        width: width,
                        height: height,
                        sprite_x: spriteX,
                        sprite_y: spriteY,
                        sprite_scale: spriteScale
                    })
                });
                const data = await response.json();
                
                document.getElementById('btnGerarXml').disabled = false;
                document.getElementById('progressoXml').classList.remove('ativo');
                
                if (data.erro) {
                    mostrarErro('Xml', data.erro);
                } else {
                    mostrarSucesso('Xml', `XML gerado com sucesso!\\n\\nArquivo: ${data.arquivo}\\nClips: ${data.clips}`);
                }
            } catch (err) {
                mostrarErro('Xml', err.message);
            }
        }
        
        // ===== CONFIG =====
        function renderizarEditorEmocoes() {
            const container = document.getElementById('emocoesEditorContainer');
            const emocoes = config.emocoes || {};
            
            container.innerHTML = Object.entries(emocoes).map(([nome, descricao]) => `
                <div class="emocao-editor">
                    <h4>${nome}</h4>
                    <textarea id="emocao_${nome}" onchange="atualizarEmocao('${nome}')">${descricao}</textarea>
                </div>
            `).join('');
        }
        
        function atualizarEmocao(nome) {
            config.emocoes[nome] = document.getElementById('emocao_' + nome).value;
        }
        
        async function salvarConfiguracoes() {
            // Atualiza todas as emoções
            Object.keys(config.emocoes).forEach(nome => {
                const el = document.getElementById('emocao_' + nome);
                if (el) config.emocoes[nome] = el.value;
            });
            
            config.prompt_base = document.getElementById('promptBase').value;
            
            // Atualiza config completo antes de salvar
            config.gemini_api_key = document.getElementById('geminiApiKey').value;
            config.elevenlabs_api_key = document.getElementById('elevenlabsApiKey').value;
            config.pasta_fotos = document.getElementById('pastaFotos').value;
            config.pasta_sprites = document.getElementById('pastaSpritesOutput').value;
            config.pasta_audios = document.getElementById('pastaAudiosOutput').value;
            config.pasta_xml = document.getElementById('pastaXmlOutput').value;
            config.modelo_audio = document.getElementById('modeloAudio').value;
            config.idioma = document.getElementById('idiomaAudio').value;
            config.resolucao_width = parseInt(document.getElementById('resolucaoWidth').value) || 1920;
            config.resolucao_height = parseInt(document.getElementById('resolucaoHeight').value) || 1080;
            config.sprite_x = parseInt(document.getElementById('spriteX').value) || 1600;
            config.sprite_y = parseInt(document.getElementById('spriteY').value) || 800;
            config.sprite_scale = parseInt(document.getElementById('spriteScale').value) || 100;
            
            await fetch('/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            const msg = document.getElementById('sucessoConfig');
            msg.textContent = '✅ Configurações salvas com sucesso!';
            msg.classList.add('ativo');
            setTimeout(() => msg.classList.remove('ativo'), 3000);
        }
        
        // ===== PROGRESSO =====
        async function verificarProgresso(tipo) {
            try {
                const response = await fetch('/progresso');
                const data = await response.json();
                
                const porcentagem = data.total > 0 ? (data.atual / data.total) * 100 : 0;
                document.getElementById('barra' + tipo).style.width = porcentagem + '%';
                document.getElementById('status' + tipo).textContent = data.status;
                
                if (data.erro) {
                    mostrarErro(tipo, data.erro);
                    document.getElementById('btnGerar' + tipo).disabled = false;
                    return;
                }
                
                if (data.concluido) {
                    document.getElementById('btnGerar' + tipo).disabled = false;
                    mostrarSucesso(tipo, data.status);
                } else {
                    setTimeout(() => verificarProgresso(tipo), 1000);
                }
            } catch (err) {
                setTimeout(() => verificarProgresso(tipo), 1000);
            }
        }
        
        function mostrarErro(tipo, msg) {
            const el = document.getElementById('erro' + tipo);
            el.textContent = '❌ ' + msg;
            el.classList.add('ativo');
            document.getElementById('progresso' + tipo).classList.remove('ativo');
            document.getElementById('btnGerar' + tipo).disabled = false;
        }
        
        function mostrarSucesso(tipo, msg) {
            const el = document.getElementById('sucesso' + tipo);
            el.textContent = '✅ ' + msg;
            el.classList.add('ativo');
            document.getElementById('progresso' + tipo).classList.remove('ativo');
        }
        
        // Auto-save em campos importantes
        ['geminiApiKey', 'elevenlabsApiKey', 'modeloAudio', 'idiomaAudio'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', salvarConfigAuto);
        });
    </script>
</body>
</html>
"""

# ===== ROTAS =====

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'GET':
        return jsonify(carregar_config())
    else:
        salvar_config(request.json)
        return jsonify({"success": True})

@app.route('/selecionar-pasta')
def selecionar_pasta():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    pasta = filedialog.askdirectory(title="Selecione uma pasta")
    root.destroy()
    return jsonify({"pasta": pasta if pasta else None})

@app.route('/verificar-foto')
def verificar_foto():
    nome = request.args.get('nome', '').lower()
    pasta = request.args.get('pasta', '')
    
    if not nome or not pasta or not os.path.exists(pasta):
        return jsonify({"encontrada": False})
    
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        arquivo = f"{nome}{ext}"
        caminho = os.path.join(pasta, arquivo)
        if os.path.exists(caminho):
            return jsonify({"encontrada": True, "arquivo": arquivo, "caminho": caminho})
    
    return jsonify({"encontrada": False})

@app.route('/carregar-vozes', methods=['POST'])
def carregar_vozes():
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=request.json['api_key'])
        response = client.voices.get_all()
        vozes = [{"nome": v.name.lower(), "id": v.voice_id} for v in response.voices]
        return jsonify({"vozes": vozes})
    except Exception as e:
        return jsonify({"erro": str(e)})

@app.route('/gerar-sprites', methods=['POST'])
def gerar_sprites():
    global progresso
    data = request.json
    progresso = {"atual": 0, "total": len(data['emocoes']), "status": "Iniciando...", "erro": None, "concluido": False}
    
    thread = threading.Thread(target=processar_sprites, args=(data,))
    thread.start()
    return jsonify({"success": True})

def processar_sprites(data):
    global progresso
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=data['api_key'])
        
        pasta_membro = os.path.join(data['pasta_output'], data['nome'])
        os.makedirs(pasta_membro, exist_ok=True)
        
        with open(data['foto_path'], "rb") as f:
            foto_bytes = f.read()
        
        ext = os.path.splitext(data['foto_path'])[1].lower()
        mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
        foto_mime = mime_types.get(ext, 'image/jpeg')
        
        # Cria chat para manter consistência entre emoções
        chat = client.chats.create(
            model="gemini-2.5-flash-image",
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
        )
        
        primeira_emocao = True
        
        for i, emocao in enumerate(data['emocoes']):
            progresso["atual"] = i
            progresso["status"] = f"Gerando {emocao}... ({i+1}/{len(data['emocoes'])})"
            
            if primeira_emocao:
                # Primeira emoção: envia foto + prompt completo
                prompt = data['prompt_base'].format(
                    emocao=emocao.upper(),
                    descricao=data['emocoes_descricao'].get(emocao, '')
                )
                
                response = chat.send_message([
                    types.Part.from_bytes(data=foto_bytes, mime_type=foto_mime),
                    types.Part.from_text(text=prompt)
                ])
                primeira_emocao = False
            else:
                # Emoções seguintes: pede variação mantendo o estilo
                prompt_variacao = f"Now generate the same character but with a different emotion: {emocao.upper()}\n\n{data['emocoes_descricao'].get(emocao, '')}\n\nKeep the exact same art style, colors, and character design. Only change the expression and pose."
                
                response = chat.send_message(prompt_variacao)
            
            # Salva a imagem gerada
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    filename = f"{data['nome']}_{emocao}.png"
                    filepath = os.path.join(pasta_membro, filename)
                    with open(filepath, "wb") as f:
                        f.write(part.inline_data.data)
                    break
            
            time.sleep(1)
        
        progresso["atual"] = len(data['emocoes'])
        progresso["status"] = f"Concluído! Sprites salvos em: {pasta_membro}"
        progresso["concluido"] = True
        
    except Exception as e:
        progresso["erro"] = str(e)
        progresso["concluido"] = True

@app.route('/gerar-audios', methods=['POST'])
def gerar_audios():
    global progresso
    data = request.json
    
    pattern = r'\[(\w+)\s*-\s*(\w+)\]\s*"([^"]+)"'
    falas = re.findall(pattern, data['roteiro'])
    
    if not falas:
        return jsonify({"erro": "Nenhuma fala encontrada no roteiro"})
    
    progresso = {"atual": 0, "total": len(falas), "status": "Iniciando...", "erro": None, "concluido": False}
    
    thread = threading.Thread(target=processar_audios, args=(data, falas))
    thread.start()
    return jsonify({"success": True})

def processar_audios(data, falas):
    global progresso
    try:
        from elevenlabs import ElevenLabs
        
        client = ElevenLabs(api_key=data['api_key'])
        response = client.voices.get_all()
        vozes_dict = {v.name.lower(): v.voice_id for v in response.voices}
        
        pasta_sessao = os.path.join(data['pasta_output'], data['nome_pasta'])
        contador = 2
        pasta_original = pasta_sessao
        while os.path.exists(pasta_sessao):
            pasta_sessao = f"{pasta_original}_{contador}"
            contador += 1
        os.makedirs(pasta_sessao)
        
        timestamps_data = []
        tempo_acumulado = 0.0
        
        for i, (personagem, emocao, texto) in enumerate(falas):
            progresso["atual"] = i
            progresso["status"] = f"Gerando áudio {i+1}/{len(falas)}: {personagem}..."
            
            personagem_lower = personagem.lower()
            
            if personagem_lower not in vozes_dict:
                progresso["erro"] = f"Voz '{personagem}' não encontrada"
                progresso["concluido"] = True
                return
            
            audio = client.text_to_speech.convert(
                voice_id=vozes_dict[personagem_lower],
                text=texto,
                model_id=data['modelo'],
                language_code=data['idioma']
            )
            
            filename = f"{str(i+1).zfill(2)}_{personagem_lower}_{emocao}.mp3"
            filepath = os.path.join(pasta_sessao, filename)
            
            audio_bytes = b''.join(audio)
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            
            # Pega duração real do MP3
            try:
                audio_info = MP3(filepath)
                duracao = audio_info.info.length
            except:
                duracao = 3.0
            
            timestamps_data.append({
                "arquivo": filename,
                "personagem": personagem_lower,
                "emocao": emocao,
                "texto": texto,
                "inicio": round(tempo_acumulado, 3),
                "fim": round(tempo_acumulado + duracao, 3),
                "duracao": round(duracao, 3)
            })
            
            tempo_acumulado += duracao
            time.sleep(0.5)
        
        with open(os.path.join(pasta_sessao, "timestamps.json"), "w", encoding="utf-8") as f:
            json.dump(timestamps_data, f, ensure_ascii=False, indent=2)
        
        progresso["atual"] = len(falas)
        progresso["status"] = f"Concluído! Áudios salvos em: {pasta_sessao}"
        progresso["concluido"] = True
        
    except Exception as e:
        progresso["erro"] = str(e)
        progresso["concluido"] = True

@app.route('/gerar-xml', methods=['POST'])
def gerar_xml():
    try:
        data = request.json
        
        timestamps_path = os.path.join(data['pasta_audios'], "timestamps.json")
        if not os.path.exists(timestamps_path):
            return jsonify({"erro": "timestamps.json não encontrado"})
        
        with open(timestamps_path, 'r', encoding='utf-8') as f:
            timestamps = json.load(f)
        
        fps = 30
        width = data['width']
        height = data['height']
        sprite_x = data['sprite_x']
        sprite_y = data['sprite_y']
        sprite_scale = data['sprite_scale']
        
        # Prepara clips
        clips = []
        tempo_atual = 0
        
        for i, item in enumerate(timestamps):
            audio_path = os.path.join(data['pasta_audios'], item['arquivo']).replace('\\', '/')
            duracao = item['duracao']
            
            # Encontra sprite
            sprite_path = None
            sprite_nome = None
            for ext in ['.png', '.jpg', '.jpeg']:
                sp = os.path.join(data['pasta_sprites'], f"{item['personagem']}_{item['emocao']}{ext}")
                if os.path.exists(sp):
                    sprite_path = sp.replace('\\', '/')
                    sprite_nome = f"{item['personagem']}_{item['emocao']}{ext}"
                    break
            
            clips.append({
                'index': i + 1,
                'audio_path': audio_path,
                'audio_nome': item['arquivo'],
                'sprite_path': sprite_path,
                'sprite_nome': sprite_nome,
                'inicio_frames': int(tempo_atual * fps),
                'duracao_frames': max(1, int(duracao * fps)),
                'fim_frames': int((tempo_atual + duracao) * fps)
            })
            tempo_atual += duracao
        
        duracao_total = int(tempo_atual * fps)
        
        # Gera XML
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence>
    <name>{data['nome_sequencia']}</name>
    <duration>{duracao_total}</duration>
    <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <width>{width}</width>
            <height>{height}</height>
            <pixelaspectratio>square</pixelaspectratio>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
          </samplecharacteristics>
        </format>
        <track>
'''
        
        # Sprites com posição e escala
        for c in clips:
            if c['sprite_path']:
                # Calcula posição normalizada (0-1 no FCP XML, centro = 0.5)
                scale_factor = sprite_scale / 100.0

                center_x = 0.5 + ((sprite_x - (width / 2)) / (width * scale_factor))
                center_y = 0.5 + ((sprite_y - (height / 2)) / (height * scale_factor))

                pos_x = center_x
                pos_y = center_y
                scale_val = sprite_scale
                
                xml += f'''          <clipitem id="sprite_{c['index']}">
            <name>{c['sprite_nome']}</name>
            <duration>{c['duracao_frames']}</duration>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <start>{c['inicio_frames']}</start>
            <end>{c['fim_frames']}</end>
            <in>0</in>
            <out>{c['duracao_frames']}</out>
            <file id="file_sprite_{c['index']}">
              <name>{c['sprite_nome']}</name>
              <pathurl>file://localhost/{c['sprite_path']}</pathurl>
              <media><video><duration>{c['duracao_frames']}</duration></video></media>
            </file>
            <filter>
              <effect>
                <name>Basic Motion</name>
                <effectid>basic</effectid>
                <effectcategory>motion</effectcategory>
                <effecttype>motion</effecttype>
                <parameter>
                  <parameterid>center</parameterid>
                  <name>Center</name>
                  <value><horiz>{pos_x}</horiz><vert>{pos_y}</vert></value>
                </parameter>
                <parameter>
                  <parameterid>scale</parameterid>
                  <name>Scale</name>
                  <value>{scale_val}</value>
                </parameter>
              </effect>
            </filter>
          </clipitem>
'''
        
        xml += '''        </track>
      </video>
      <audio>
        <format>
          <samplecharacteristics>
            <samplerate>48000</samplerate>
            <depth>16</depth>
          </samplecharacteristics>
        </format>
        <track>
'''
        
        # Áudios
        for c in clips:
            xml += f'''          <clipitem id="audio_{c['index']}">
            <name>{c['audio_nome']}</name>
            <duration>{c['duracao_frames']}</duration>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <start>{c['inicio_frames']}</start>
            <end>{c['fim_frames']}</end>
            <in>0</in>
            <out>{c['duracao_frames']}</out>
            <file id="file_audio_{c['index']}">
              <name>{c['audio_nome']}</name>
              <pathurl>file://localhost/{c['audio_path']}</pathurl>
              <media><audio><channelcount>2</channelcount></audio></media>
            </file>
          </clipitem>
'''
        
        xml += '''        </track>
      </audio>
    </media>
      </sequence>
    </children>
  </bin>
</xmeml>'''
        
        # Salva arquivo
        xml_path = os.path.join(data['pasta_output'], f"{data['nome_sequencia']}.xml")
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml)
        
        return jsonify({"sucesso": True, "arquivo": xml_path, "clips": len(clips)})
        
    except Exception as e:
        return jsonify({"erro": str(e)})

@app.route('/progresso')
def get_progresso():
    return jsonify(progresso)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎮 Venn Studios - Pipeline Completo")
    print("="*50)
    print("\n📌 Acesse: http://localhost:5000")
    print("📌 Para parar: Ctrl+C\n")
    app.run(debug=True, port=5000)