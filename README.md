# Music Downloader

Projeto focado em agilizar a vida de quem trabalha com música, principalmente DJs que montam playlists no Spotify e depois precisam fazer o corre de baixar tudo em MP3 para tocar.

Com uma interface simples, o app automatiza o processo de busca no YouTube, download, conversão para MP3, organização por playlist e controle de qualidade do resultado.

## Visão Geral

O objetivo é transformar este fluxo:

1. montar playlist no Spotify
2. pesquisar faixa por faixa
3. baixar manualmente
4. organizar arquivos

em um processo automatizado, com poucos cliques e muito menos tempo perdido.

## Principais Recursos

- Download de playlists do Spotify para MP3 (via busca inteligente no YouTube)
- Download de playlists e links avulsos do YouTube
- Opção de priorizar versões Extended para sets de DJ
- Limitador de duração por faixa (10, 13, 15, 20 min ou sem limite)
- Downloads paralelos para acelerar o processamento
- Organização automática por nome da playlist
- Detecção de faixas já existentes para evitar download duplicado
- Embedding de capa e metadados no MP3 (quando disponível)
- Relatório de músicas não baixadas com motivo
- Verificação de espaço em disco para reduzir falhas no meio da execução

## Para Quem Este Projeto Foi Feito

- DJs de pista, rádio ou eventos
- Produtores e curadores musicais
- Pessoas que montam playlists com frequência e precisam de ganho de tempo

## Tecnologias Utilizadas

- Python
- CustomTkinter (interface gráfica)
- yt-dlp (busca e download)
- FFmpeg (conversão para MP3 e metadados)
- Requests + BeautifulSoup (leitura dos dados públicos de playlists)

## Requisitos

- Windows 10 ou 11
- Python 3.10+
- FFmpeg instalado no sistema

Instalação de FFmpeg no Windows (PowerShell):

```powershell
winget install FFmpeg
```

## Instalação do Projeto

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install requests beautifulsoup4 customtkinter yt-dlp
```

## Como Executar

```powershell
python app_download.py
```

## Como Usar

1. Abra o aplicativo.
2. Escolha a pasta de destino dos arquivos.
3. Cole os links (um por linha):
	- playlist do Spotify
	- playlist do YouTube
	- música avulsa do YouTube
4. Marque a opção Extended se quiser priorizar versões estendidas.
5. Defina o limite de duração por faixa.
6. Ajuste a quantidade de downloads paralelos.
7. Clique em Iniciar Downloads.

## Diferenciais de Performance

- Paralelismo para processar múltiplos links ao mesmo tempo
- Filtro por duração para evitar faixas longas fora do objetivo
- Estratégia de busca em cascata para aumentar chance de match correto
- Skip inteligente de arquivos já existentes

## Estrutura de Saída

- Cada playlist vai para uma pasta com o nome da própria playlist
- Faixas avulsas vão para a pasta Musicas_Avulsas
- Falhas ficam registradas no arquivo musicas_nao_baixadas.txt

## Troubleshooting

Erro: FFmpeg não encontrado
- Instale ou reinstale FFmpeg com winget install FFmpeg
- Feche e abra o terminal novamente

Erro ao ativar ambiente virtual no PowerShell

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Pouco espaço em disco
- O app interrompe o processo para evitar corromper a operação
- Libere espaço e execute novamente

## Roadmap

- Exportar histórico de downloads
- Presets por estilo (House, Tech House, Trance, etc.)
- Filtros adicionais de versão (radio edit, remix, live)
- Pacote executável para distribuição simplificada

## Aviso Importante

Use este projeto de forma responsável, respeitando direitos autorais e os termos de uso das plataformas.

## Autor

Desenvolvido para acelerar workflow musical real de DJ, com foco em praticidade, velocidade e organização.

