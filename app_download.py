import os
import re
import json
import shutil
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import customtkinter as ctk
from yt_dlp import YoutubeDL

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def sanitizar_nome(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()

def limpar_termo_para_busca(titulo, artista):
    # Remove sufixos comuns que poluem a busca do YouTube
    padroes_para_remover = [
        r'\(feat\..*?\)', r'\[feat\..*?\]',
        r'\(with.*?\)', r'\[with.*?\]',
        r'- Radio Edit', r'\(Radio Edit\)',
        r'- Original Mix', r'\(Original Mix\)',
        r'- Extended Mix', r'\(Extended Mix\)',
        r'- Extended', r'\(Extended\)',
        r'\(Official.*?\)', r'\[Official.*?\]',
        r'-\s*$'
    ]
    
    texto_limpo = titulo
    for padrao in padroes_para_remover:
        texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE).strip()
        
    # Pega apenas o primeiro artista principal caso venha uma lista enorme
    artistas_split = re.split(r'[,&/]', artista)
    artista_principal = artistas_split[0].strip() if artistas_split else artista.strip()
    
    busca_otimizada = f"{texto_limpo} {artista_principal}".strip()
    return re.sub(r'\s+', ' ', busca_otimizada)

def tem_espaco_em_disco(caminho, limite_minimo_mb=500):
    try:
        total, usado, livre = shutil.disk_usage(caminho)
        livre_mb = livre / (1024 * 1024)
        return livre_mb >= limite_minimo_mb
    except Exception:
        return True

def musica_ja_existe(pasta, titulo_musica):
    if not os.path.exists(pasta):
        return False
    titulo_limpo = re.sub(r'[^a-zA-Z0-9]', '', titulo_musica.lower())
    arquivos = [f.lower() for f in os.listdir(pasta) if f.endswith('.mp3')]
    for arq in arquivos:
        arq_limpo = re.sub(r'[^a-zA-Z0-9]', '', arq)
        if titulo_limpo in arq_limpo:
            return True
    return False

def formatar_tempo(segundos):
    if segundos is None:
        return "N/A"
    minutos = int(segundos // 60)
    segs = int(segundos % 60)
    return f"{minutos}:{segs:02d}"

def obter_faixas_spotify_embed(url_playlist):
    match = re.search(r'playlist/([a-zA-Z0-9]+)', url_playlist)
    if not match:
        raise Exception("Formato de URL do Spotify inválido!")
    
    playlist_id = match.group(1)
    embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    response = requests.get(embed_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erro ao acessar Spotify Embed ({response.status_code})")
        
    soup = BeautifulSoup(response.text, 'html.parser')
    next_data = soup.find('script', id='__NEXT_DATA__')
    
    tracks_info = []
    nome_playlist = "Spotify_Playlist"
    
    if next_data and next_data.string:
        data = json.loads(next_data.string)
        entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
        nome_playlist = entity.get('title') or entity.get('name') or "Spotify_Playlist"
        for item in entity.get('trackList', []):
            titulo = item.get('title', '').strip()
            artista = item.get('subtitle', '').strip()
            if titulo:
                tracks_info.append({
                    'titulo': titulo,
                    'artista': artista,
                    'busca_otimizada': limpar_termo_para_busca(titulo, artista),
                    'busca_completa': f"{titulo} - {artista}" if artista else titulo
                })
    return sanitizar_nome(nome_playlist), tracks_info


class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Universal Music Downloader (Spotify & YouTube)")
        self.geometry("860x780")
        self.minsize(750, 650)
        
        self.diretorio_base = os.path.join(os.path.expanduser("~"), "Downloads", "Musicas")
        if not os.path.exists(self.diretorio_base):
            os.makedirs(self.diretorio_base)
            
        self.nao_baixadas = []
        self.lock_lista = threading.Lock()
        self.abortar_por_disco = threading.Event()
            
        self.criar_interface()

    def log(self, mensagem):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", mensagem + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def registrar_nao_baixada(self, playlist, faixa, motivo):
        with self.lock_lista:
            self.nao_baixadas.append(f"{playlist} > {faixa} (Motivo: {motivo})")

    def atualizar_progresso_ui(self, valor_decimal, texto_status):
        self.after(0, lambda: self._set_progresso(valor_decimal, texto_status))

    def _set_progresso(self, valor_decimal, texto_status):
        self.progress_bar.set(valor_decimal)
        self.lbl_status_progresso.configure(text=texto_status)

    def hook_download(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            baixado = d.get('downloaded_bytes', 0)
            if total > 0:
                pct = (baixado / total)
                self.atualizar_progresso_ui(pct, f"Baixando stream: {int(pct * 100)}%")
        elif d['status'] == 'finished':
            self.atualizar_progresso_ui(1.0, "Processando tags ID3 e Capa...")

    def criar_interface(self):
        self.label_titulo = ctk.CTkLabel(
            self, text="🎵 Music Downloader MP3", font=ctk.CTkFont(size=22, weight="bold")
        )
        self.label_titulo.pack(pady=(15, 5))

        self.frame_dir = ctk.CTkFrame(self)
        self.frame_dir.pack(fill="x", padx=20, pady=5)
        
        self.lbl_pasta = ctk.CTkLabel(self.frame_dir, text=f"Pasta: {self.diretorio_base}", anchor="w")
        self.lbl_pasta.pack(side="left", padx=10, fill="x", expand=True)
        
        self.btn_alterar_dir = ctk.CTkButton(self.frame_dir, text="Alterar Pasta", width=110, command=self.selecionar_pasta)
        self.btn_alterar_dir.pack(side="right", padx=10, pady=6)

        self.lbl_links = ctk.CTkLabel(self, text="Cole seus links abaixo (1 por linha):", anchor="w")
        self.lbl_links.pack(fill="x", padx=20, pady=(10, 2))

        self.txt_links = ctk.CTkTextbox(self, height=110)
        self.txt_links.pack(fill="x", padx=20, pady=5)

        self.frame_opcoes = ctk.CTkFrame(self)
        self.frame_opcoes.pack(fill="x", padx=20, pady=5)

        self.chk_extended = ctk.CTkCheckBox(self.frame_opcoes, text="Priorizar 'extended' no Spotify")
        self.chk_extended.select()
        self.chk_extended.pack(side="left", padx=10, pady=8)

        self.lbl_duracao = ctk.CTkLabel(self.frame_opcoes, text="Duração Máx:")
        self.lbl_duracao.pack(side="left", padx=(10, 2))

        self.combo_duracao = ctk.CTkComboBox(self.frame_opcoes, values=["10 min", "13 min", "15 min", "20 min", "Sem Limite"], width=105)
        self.combo_duracao.set("15 min")
        self.combo_duracao.pack(side="left", padx=5)

        self.lbl_concorrencia = ctk.CTkLabel(self.frame_opcoes, text="Paralelos:")
        self.lbl_concorrencia.pack(side="left", padx=(15, 2))

        self.combo_threads = ctk.CTkComboBox(self.frame_opcoes, values=["1", "2", "3", "4"], width=65)
        self.combo_threads.set("2")
        self.combo_threads.pack(side="left", padx=5)

        self.frame_progresso = ctk.CTkFrame(self)
        self.frame_progresso.pack(fill="x", padx=20, pady=(10, 5))

        self.lbl_status_progresso = ctk.CTkLabel(self.frame_progresso, text="Aguardando início...", anchor="w", font=ctk.CTkFont(size=12))
        self.lbl_status_progresso.pack(fill="x", padx=10, pady=(5, 2))

        self.progress_bar = ctk.CTkProgressBar(self.frame_progresso, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=10, pady=(0, 8))

        self.btn_iniciar = ctk.CTkButton(
            self, text="▶ Iniciar Downloads", font=ctk.CTkFont(size=15, weight="bold"),
            height=38, command=self.iniciar_processamento
        )
        self.btn_iniciar.pack(fill="x", padx=20, pady=8)

        self.lbl_log = ctk.CTkLabel(self, text="Console de Execução:", anchor="w")
        self.lbl_log.pack(fill="x", padx=20, pady=(5, 0))

        self.log_textbox = ctk.CTkTextbox(self, height=170, state="disabled")
        self.log_textbox.pack(fill="both", expand=True, padx=20, pady=(5, 15))

    def selecionar_pasta(self):
        escolhida = ctk.filedialog.askdirectory(initialdir=self.diretorio_base)
        if escolhida:
            self.diretorio_base = escolhida
            self.lbl_pasta.configure(text=f"Pasta: {self.diretorio_base}")

    def obter_limite_segundos(self):
        selecao = self.combo_duracao.get()
        if "10" in selecao:
            return 600
        elif "13" in selecao:
            return 780
        elif "15" in selecao:
            return 900
        elif "20" in selecao:
            return 1200
        return None

    def iniciar_processamento(self):
        links_texto = self.txt_links.get("1.0", "end").strip()
        if not links_texto:
            self.log("⚠️ Nenhum link informado.")
            return

        if not shutil.which("ffmpeg"):
            self.log("❌ FFmpeg não encontrado no sistema! Execute 'winget install FFmpeg' no terminal.")
            return

        if not tem_espaco_em_disco(self.diretorio_base, limite_minimo_mb=500):
            self.log("❌ Espaço em disco insuficiente! É necessário pelo menos 500 MB livres.")
            return

        links = [linha.strip() for linha in links_texto.splitlines() if linha.strip()]
        self.btn_iniciar.configure(state="disabled", text="Baixando...")
        self.atualizar_progresso_ui(0.0, "Iniciando fila...")
        
        self.nao_baixadas.clear()
        self.abortar_por_disco.clear()
        
        num_threads = int(self.combo_threads.get())
        usar_extended = bool(self.chk_extended.get())
        limite_segundos = self.obter_limite_segundos()

        threading.Thread(
            target=self.gerenciar_fila, 
            args=(links, num_threads, usar_extended, limite_segundos), 
            daemon=True
        ).start()

    def gerenciar_fila(self, links, num_threads, usar_extended, limite_segundos):
        txt_limite = f"{limite_segundos//60} min" if limite_segundos else "Sem Limite"
        self.log(f"\n🚀 Iniciando fila com {len(links)} link(s) | Limite por faixa: {txt_limite} | Paralelos: {num_threads}...")
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            executor.map(lambda url: self.processar_link(url, usar_extended, limite_segundos), links)
            
        if self.abortar_por_disco.is_set():
            self.log("\n🛑 Download interrompido: Disco cheio!")
            self.atualizar_progresso_ui(0.0, "Interrompido (Disco Cheio)")
        else:
            self.log("\n✨ Processamento da lista finalizado!")
            self.atualizar_progresso_ui(1.0, "Concluído com sucesso (100%)")

        if self.nao_baixadas:
            self.log("\n" + "="*70)
            self.log("📋 LISTA DE MÚSICAS NÃO BAIXADAS (Playlist > Música):")
            for item in self.nao_baixadas:
                self.log(f"  • {item}")
            self.log("="*70)
            
            caminho_relatorio = os.path.join(self.diretorio_base, "musicas_nao_baixadas.txt")
            try:
                with open(caminho_relatorio, "w", encoding="utf-8") as f:
                    f.write("RELATÓRIO DE MÚSICAS NÃO BAIXADAS\n")
                    f.write("Formato: [Playlist] > [Música] (Motivo)\n")
                    f.write("="*70 + "\n\n")
                    for item in self.nao_baixadas:
                        f.write(f"{item}\n")
                self.log(f"📄 Arquivo salvo em: {caminho_relatorio}")
            except Exception as e:
                self.log(f"⚠️ Erro ao salvar relatório: {e}")
        else:
            self.log("🎉 Todas as músicas foram baixadas ou já existiam!")

        self.btn_iniciar.configure(state="normal", text="▶ Iniciar Downloads")

    def get_ydl_opts(self, pasta_destino, limite_segundos=None, apenas_uma_musica=False):
        opts = {
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
                {'key': 'FFmpegMetadata', 'add_metadata': True},
                {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}
            ],
            'outtmpl': os.path.join(pasta_destino, '%(title)s.%(ext)s'),
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['tv', 'web', 'android']}},
            'concurrent_fragment_downloads': 4,
            'progress_hooks': [self.hook_download],
        }
        
        if apenas_uma_musica:
            opts['noplaylist'] = True
            
        return opts

    def processar_link(self, url, usar_extended, limite_segundos):
        if self.abortar_por_disco.is_set():
            return

        try:
            if "spotify.com/playlist/" in url:
                self.processar_playlist_spotify(url, usar_extended, limite_segundos)
            elif "youtube.com/playlist" in url or ("list=" in url and "watch?v=" not in url):
                self.processar_playlist_youtube(url, limite_segundos)
            elif "youtube.com/watch" in url or "youtu.be/" in url:
                self.processar_musica_avulsa_youtube(url, limite_segundos)
            else:
                self.log(f"⚠️ Link não suportado: {url}")
                self.registrar_nao_baixada("Desconhecida", url, "Link não suportado")
        except Exception as e:
            self.log(f"❌ Erro ao processar '{url}': {e}")
            self.registrar_nao_baixada("Erro Link", url, str(e))

    def processar_playlist_spotify(self, url, usar_extended, limite_segundos):
        self.log(f"🔍 Identificando Spotify: {url}")
        try:
            nome_playlist, faixas = obter_faixas_spotify_embed(url)
        except Exception as e:
            self.log(f"❌ Erro ao carregar Spotify: {e}")
            self.registrar_nao_baixada("Spotify", url, f"Falha ao ler playlist: {e}")
            return

        pasta_destino = os.path.join(self.diretorio_base, nome_playlist)
        os.makedirs(pasta_destino, exist_ok=True)
        
        total_faixas = len(faixas)
        self.log(f"📂 [Spotify] '{nome_playlist}' ({total_faixas} músicas)")
        opts = self.get_ydl_opts(pasta_destino, apenas_uma_musica=True)
        
        with YoutubeDL(opts) as ydl:
            for idx, item in enumerate(faixas, 1):
                if self.abortar_por_disco.is_set():
                    self.registrar_nao_baixada(nome_playlist, item['busca_completa'], "Abortado por falta de espaço em disco")
                    continue

                if not tem_espaco_em_disco(self.diretorio_base, limite_minimo_mb=500):
                    self.log("\n⚠️ [DISCO CHEIO] Espaço abaixo de 500 MB! Abortando...")
                    self.abortar_por_disco.set()
                    self.registrar_nao_baixada(nome_playlist, item['busca_completa'], "Sem espaço em disco")
                    break

                titulo = item['titulo']
                busca_otimizada = item['busca_otimizada']
                busca_completa = item['busca_completa']
                
                progresso_geral_pct = int(((idx - 1) / total_faixas) * 100)
                self.atualizar_progresso_ui((idx - 1) / total_faixas, f"Playlist '{nome_playlist}': {idx}/{total_faixas} ({progresso_geral_pct}%)")

                if musica_ja_existe(pasta_destino, titulo):
                    self.log(f"  ⏭️ [{nome_playlist}] ({idx}/{total_faixas}) Já existe: {titulo}")
                    continue
                
                # Lista de queries em cascata para cobrir variações como "2020", "Audio Oficial", etc.
                queries_teste = []
                if usar_extended:
                    queries_teste.append(f"ytsearch5:{busca_otimizada} extended")
                queries_teste.append(f"ytsearch5:{busca_otimizada} audio")
                queries_teste.append(f"ytsearch3:{busca_otimizada}")
                queries_teste.append(f"ytsearch3:{busca_completa}")
                
                video_escolhido = None
                
                for query in queries_teste:
                    try:
                        info = ydl.extract_info(query, download=False)
                        entradas = info.get('entries', []) if info else []
                        
                        for entrada in entradas:
                            if not entrada:
                                continue
                            duracao = entrada.get('duration')
                            if limite_segundos is None or duracao is None or duracao <= limite_segundos:
                                video_escolhido = entrada
                                break
                        
                        if video_escolhido:
                            break
                    except Exception:
                        continue
                
                if video_escolhido:
                    url_vid = video_escolhido.get('webpage_url') or video_escolhido.get('url')
                    dur_str = formatar_tempo(video_escolhido.get('duration'))
                    self.log(f"  ⬇️ [{nome_playlist}] ({idx}/{total_faixas}) Baixando [{dur_str}]: {titulo}")
                    try:
                        ydl.download([url_vid])
                    except Exception as e:
                        self.log(f"  ❌ [{nome_playlist}] ({idx}/{total_faixas}) Falha ao baixar stream: {e}")
                        self.registrar_nao_baixada(nome_playlist, busca_completa, f"Falha no stream: {e}")
                else:
                    self.log(f"  ⚠️ [{nome_playlist}] ({idx}/{total_faixas}) Não encontrado no YouTube: {titulo}")
                    self.registrar_nao_baixada(nome_playlist, busca_completa, "Nenhum resultado válido encontrado no YouTube")

    def processar_playlist_youtube(self, url, limite_segundos):
        if not tem_espaco_em_disco(self.diretorio_base, limite_minimo_mb=500):
            self.log("\n⚠️ [DISCO CHEIO] Espaço em disco insuficiente!")
            self.abortar_por_disco.set()
            self.registrar_nao_baixada("YouTube Playlist", url, "Sem espaço em disco")
            return

        self.log(f"🔍 Identificando Playlist YouTube: {url}")
        try:
            with YoutubeDL({'extract_flat': True, 'skip_download': True, 'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                nome_playlist = sanitizar_nome(info.get('title', 'YouTube_Playlist'))
        except Exception as e:
            self.log(f"❌ Erro ao ler playlist do YouTube: {e}")
            self.registrar_nao_baixada("YouTube", url, str(e))
            return
            
        pasta_destino = os.path.join(self.diretorio_base, nome_playlist)
        os.makedirs(pasta_destino, exist_ok=True)
        
        self.log(f"📂 [YouTube Playlist] Baixando na pasta '{nome_playlist}'...")
        opts = self.get_ydl_opts(pasta_destino, limite_segundos=limite_segundos, apenas_uma_musica=False)
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            self.log(f"❌ Erro ao baixar playlist: {e}")
            self.registrar_nao_baixada(nome_playlist, url, str(e))

    def processar_musica_avulsa_youtube(self, url, limite_segundos):
        if not tem_espaco_em_disco(self.diretorio_base, limite_minimo_mb=500):
            self.log("\n⚠️ [DISCO CHEIO] Espaço em disco insuficiente!")
            self.abortar_por_disco.set()
            self.registrar_nao_baixada("YouTube Avulsa", url, "Sem espaço em disco")
            return

        pasta_destino = os.path.join(self.diretorio_base, "Musicas_Avulsas")
        os.makedirs(pasta_destino, exist_ok=True)
        
        self.log(f"⬇️ [YouTube Single/Mix] Iniciando: {url}")
        opts = self.get_ydl_opts(pasta_destino, limite_segundos=limite_segundos, apenas_uma_musica=False)
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            self.log(f"❌ Erro ao baixar música avulsa: {e}")
            self.registrar_nao_baixada("Musicas_Avulsas", url, str(e))


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()