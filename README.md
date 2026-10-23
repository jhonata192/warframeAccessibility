# Warframe Accessibility for NVDA

Addon de acessibilidade integral para o **Launcher do Warframe** no leitor de tela **NVDA**, construído rigorosamente sob os princípios de **Acesso Equivalente**, **Design Universal** e diretrizes **WCAG** — sem esconder, omitir ou remover qualquer elemento da interface.

## ✨ Recursos

- **Navegação Integral por Tab / Shift+Tab:**
  - Percorre sequencialmente todos os botões e controles nativos da janela Win32:
    - Fechar launcher
    - Maximizar / Restaurar
    - Minimizar
    - Configurações do launcher
    - Idioma (`Português-Br`)
    - Canal do jogo (`Public`)
    - Texto estático com status e velocidade de download
    - Botão **JOGAR** (com verificação automática de prontidão)
    - Documento Web CEF integrado
- **Resiliência a Alt+Tab (Foco Imediato):**
  - Ao alternar para a janela do Launcher através do `Alt+Tab`, o foco e o cursor de navegação são automaticamente posicionados no botão principal ativo (botão **JOGAR** se atualizado ou primeiro botão interativo), garantindo que a primeira tecla `Tab` responda imediatamente.
- **Acesso ao Conteúdo Web (Vitrine CEF):**
  - Suporte ao modo Virtual Buffer (`Browse Mode`) para leitura linha a linha das notícias, Prime Access e Notas de Atualização usando as setas para cima e para baixo.
- **Proteção contra travamentos (Watchdog Safe):**
  - Leitura Win32 direta via `SendMessage(WM_GETTEXT)` sem engasgos de COM/DisplayModel.

## ⌨️ Teclas de Atalho

| Atalho | Ação |
| :--- | :--- |
| `Tab` | Avança o foco para o próximo controle do Launcher |
| `Shift + Tab` | Recua o foco para o controle anterior |
| `Enter` / `Espaço` | Clica no botão focado ou abre o conteúdo Web |
| `Alt + W` ou `Ctrl + Shift + W` | Foca diretamente o documento Web para leitura com setas |
| `Alt + S`, `Ctrl + Shift + S` ou `NVDA + Shift + S` | Anuncia o status, velocidade e tempo restante do download |
| `Alt + J`, `Ctrl + Shift + J` ou `NVDA + Shift + J` | Aciona o botão Jogar ou informa o tempo restante de atualização |
| `Alt + C` | Abre as configurações do Launcher |
| `F1` ou `NVDA + Shift + H` | Guia falado com o resumo dos atalhos |

## 📦 Como Instalar

1. Baixe o arquivo `.nvda-addon` da seção de [Releases](https://github.com/jhonata192/warframeAccessibility/releases).
2. Pressione `Enter` sobre o arquivo baixado ou abra o NVDA, vá ao menu **Ferramentas > Complementos > Instalar** e selecione o pacote.
3. Confirme a instalação e reinicie o NVDA.

## 🛠️ Como Compilar o Complemento Manualmente

Execute em um prompt de comando ou terminal Python:
```bash
python -c "import zipfile, os; z = zipfile.ZipFile('warframeAccessibility-1.0.0.nvda-addon', 'w', zipfile.ZIP_DEFLATED); [z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), '.')) for r, d, fs in os.walk('.') if not any(x in r for x in ['.git', '__pycache__']) for f in fs if not f.endswith(('.git', '.pyc', '.addon'))]; z.close()"
```

## 📄 Licença

Distribuído sob a licença GPL v2 (compatível com a licença do NVDA).
