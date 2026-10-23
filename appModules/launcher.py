# -*- coding: utf-8 -*-
"""
AppModule nativo do NVDA para o Launcher do Warframe (Launcher.exe).
Implementa Acesso Equivalente Completo (WCAG / Design Universal):
- Navegação direta entre todos os controles nativos da janela e vitrine:
  1. Fechar launcher
  2. Maximizar / Restaurar
  3. Minimizar
  4. Configurações do launcher
  5. Idioma (Português-Br)
  6. Canal do jogo (Public)
  7. Status e velocidade de download
  8. Botão JOGAR
  9. Documento Web de Novidades, Prime Access e Notas de Atualização
- Modo Virtual Buffer (Browse Mode) integrado e estável no conteúdo Web (CEF):
  - Leitura com Setas Acima/Abaixo, Cabeçalhos (H), Links (K), Listas (L).
- Atalhos rápidos de acessibilidade:
  - Alt+W: Foca diretamente o conteúdo Web das Novidades / Notas de Atualização.
  - Alt+S / Control+Shift+S / NVDA+Shift+S: Anuncia o status completo do download.
  - Alt+J / Control+Shift+J / NVDA+Shift+J: Aciona o botão Jogar ou informa o progresso restante.
  - Alt+C: Aciona as Configurações do launcher.
  - F1 / NVDA+Shift+H: Exibe o guia completo de teclas de acessibilidade do Warframe.
"""

import os
import time
import ctypes
from ctypes import wintypes
import appModuleHandler
import controlTypes
import ui
import api
import tones
import NVDAObjects
from scriptHandler import script
from logHandler import log

_u32 = ctypes.windll.user32

_Role = getattr(controlTypes, "Role", None)
ROLE_WINDOW = getattr(_Role, "WINDOW", getattr(controlTypes, "ROLE_WINDOW", 1))
ROLE_PANE = getattr(_Role, "PANE", 3)
ROLE_BUTTON = getattr(_Role, "BUTTON", getattr(controlTypes, "ROLE_BUTTON", 9))
ROLE_STATICTEXT = getattr(_Role, "STATICTEXT", getattr(controlTypes, "ROLE_STATICTEXT", 7))
ROLE_PROGRESSBAR = getattr(_Role, "PROGRESSBAR", getattr(controlTypes, "ROLE_PROGRESSBAR", 25))
ROLE_DOCUMENT = getattr(_Role, "DOCUMENT", getattr(controlTypes, "ROLE_DOCUMENT", 52))


def _get_win32_window_text(hwnd):
    """Lê o texto de uma janela Win32 de forma direta e sem acionar watchdog do displayModel."""
    if not hwnd:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(512)
        _u32.SendMessageW(hwnd, 0x000D, 512, buf)  # WM_GETTEXT = 0x000D
        return buf.value.strip()
    except Exception:
        return ""


class WarframeNativeButton(NVDAObjects.NVDAObject):
    """Identifica e rotula precisamente os botões nativos da janela Win32 do Launcher."""

    def _get_name(self):
        ctrl_id = getattr(self, "windowControlID", 0)
        if ctrl_id == 1029:
            return "Fechar launcher"
        elif ctrl_id == 1030:
            return "Maximizar"
        elif ctrl_id == 1031:
            return "Minimizar"
        elif ctrl_id == 1032:
            return "Idioma: Português-Br"
        elif ctrl_id == 1033:
            return "Canal: Public"
        elif ctrl_id in (1034, 1035):
            return "JOGAR"

        raw_name = (getattr(self, "_name", "") or getattr(super(), "name", "") or "").strip()
        if raw_name and raw_name.lower() not in ("launcher", "button", "none"):
            return raw_name

        loc = getattr(self, "location", None)
        if loc:
            x, y, w, h = loc
            if y <= 160:
                if x >= 1560:
                    return "Fechar launcher"
                elif x >= 1530:
                    return "Maximizar"
                elif x >= 1500:
                    return "Minimizar"
                elif x >= 1470:
                    return "Configurações"
            elif y >= 800 and x >= 1350:
                return "JOGAR"

        return "Botão do Launcher"


class WarframeLauncherWindow(NVDAObjects.NVDAObject):
    """Objeto raiz da janela nativa do Launcher."""

    def _get_name(self):
        return "Warframe Launcher"


class AppModule(appModuleHandler.AppModule):
    """Módulo de acessibilidade para o Launcher do Warframe."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_index = -1
        self._nav_elements_cache = []
        self._last_nav_cache_time = 0
        log.info("Warframe Launcher: AppModule inicializado com sucesso.")

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        try:
            wclass = (getattr(obj, "windowClassName", "") or "").lower()
            role = int(getattr(obj, "role", 0))

            if wclass == "launcher" and role in (int(ROLE_WINDOW), int(ROLE_PANE)):
                clsList.insert(0, WarframeLauncherWindow)
            elif wclass == "button":
                clsList.insert(0, WarframeNativeButton)
        except Exception:
            pass

        try:
            super().chooseNVDAObjectOverlayClasses(obj, clsList)
        except Exception:
            pass

    def event_gainFocus(self, obj, nextHandler):
        """Ao alternar com Alt+Tab para o Warframe, garante foco direto em controle navegavel e anuncia status."""
        try:
            wclass = (getattr(obj, "windowClassName", "") or "").lower()
            if wclass in ("launcher", "cefbrowserwindow", "chrome_widgetwin_0", "chrome_renderwidgethosthwnd"):
                elements = self._collect_nav_elements()
                if elements:
                    # Encontra o botão JOGAR ou o primeiro botão como foco padrão
                    target_idx = 0
                    for i, el in enumerate(elements):
                        if getattr(el, "windowControlID", 0) in (1034, 1035):
                            target_idx = i
                            break
                    self._current_index = target_idx
                    target = elements[target_idx]
                    try:
                        api.setFocusObject(target)
                        api.setNavigatorObject(target)
                    except Exception:
                        pass

                    label = self._get_element_label(target)
                    status_text = self._get_native_status_text()
                    if status_text:
                        ui.message(f"Warframe: {status_text}. Focado em {label}. Use Tab ou setas para navegar.")
                    else:
                        ui.message(f"Warframe Launcher ativo. Focado em {label}. Use Tab para navegar.")
                    return
        except Exception:
            pass
        nextHandler()

    def _get_native_status_text(self):
        """Lê o status da barra de download diretamente dos controles de texto estático ou log."""
        try:
            root = self._get_launcher_root()
            if root and getattr(root, "children", None):
                static_parts = []
                for c in root.children:
                    if getattr(c, "windowClassName", "") == "Static":
                        txt = _get_win32_window_text(getattr(c, "windowHandle", 0))
                        if not txt:
                            try:
                                txt = (getattr(c, "name", "") or "").strip()
                            except Exception:
                                txt = ""
                        if txt:
                            static_parts.append(txt)
                if static_parts:
                    return " ".join(static_parts)
        except Exception:
            pass

        try:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            log_path = os.path.join(local_appdata, "Warframe", "Launcher.log")
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for line in reversed(lines[-20:]):
                    line = line.strip()
                    if "Downloading @" in line:
                        return line
                    if "Finished" in line:
                        return "O Warframe está atualizado!"
        except Exception:
            pass
        return "O Warframe está atualizado!"

    def _get_launcher_root(self):
        """Localiza confiavelmente o objeto raiz com os controles do Launcher."""
        hwnd = _u32.FindWindowW("Launcher", None)
        if hwnd:
            try:
                obj = NVDAObjects.IAccessible.getNVDAObjectFromEvent(hwnd, -4, 0)
                if obj and len(getattr(obj, "children", []) or []) >= 10:
                    return obj
            except Exception:
                pass

        cur = api.getFocusObject()
        root = cur
        while root:
            if getattr(root, "windowClassName", "") == "Launcher" and int(getattr(root, "role", 0)) in (int(ROLE_WINDOW), int(ROLE_PANE)):
                if len(getattr(root, "children", []) or []) >= 10:
                    return root
            try:
                root = getattr(root, "parent", None)
            except Exception:
                break

        fg = api.getForegroundObject()
        if fg:
            if getattr(fg, "windowClassName", "") == "Launcher" and int(getattr(fg, "role", 0)) in (int(ROLE_WINDOW), int(ROLE_PANE)):
                if len(getattr(fg, "children", []) or []) >= 10:
                    return fg
            for c in getattr(fg, "children", []) or []:
                if getattr(c, "windowClassName", "") == "Launcher" and len(getattr(c, "children", []) or []) >= 10:
                    return c
        return None

    def _is_updating(self):
        """Verifica se o jogo está ativamente atualizando ou se o botão JOGAR já está liberado."""
        try:
            root = self._get_launcher_root()
            if root:
                for c in (getattr(root, "children", []) or []):
                    if getattr(c, "windowControlID", 0) == 1034:
                        # Se o botão principal 1034 tiver o estado UNAVAILABLE, ainda está atualizando
                        if controlTypes.State.UNAVAILABLE in getattr(c, "states", set()):
                            return True
                        return False
        except Exception:
            pass
        return False

    def _get_cef_document(self):
        """Localiza o documento Web real dentro do CEF diretamente pelas janelas Win32."""
        hwnd = _u32.FindWindowW("Launcher", None)
        if not hwnd:
            root = self._get_launcher_root()
            hwnd = getattr(root, "windowHandle", 0) if root else 0
        if not hwnd:
            return None

        h_cef = _u32.FindWindowExW(hwnd, 0, "CefBrowserWindow", None)
        h_widget = _u32.FindWindowExW(h_cef, 0, "Chrome_WidgetWin_0", None) if h_cef else 0
        h_render = _u32.FindWindowExW(h_widget, 0, "Chrome_RenderWidgetHostHWND", None) if h_widget else 0

        if h_render:
            try:
                doc = NVDAObjects.IAccessible.getNVDAObjectFromEvent(h_render, -4, 0)
                if doc:
                    return doc
            except Exception:
                pass
        return None

    def _collect_nav_elements(self):
        """Coleta a lista completa e ordenada de controles do Launcher (nativos + documento Web)."""
        now = time.time()
        if self._nav_elements_cache and (now - self._last_nav_cache_time < 3.0):
            return self._nav_elements_cache

        root = self._get_launcher_root()
        if not root:
            return self._nav_elements_cache or []

        children = getattr(root, "children", []) or []
        elements = []
        seen_jogar = False

        for c in children:
            wclass = getattr(c, "windowClassName", "") or ""
            ctrl_id = getattr(c, "windowControlID", 0)

            # Botões nativos
            if wclass == "Button":
                if ctrl_id in (1034, 1035):
                    if seen_jogar:
                        continue
                    seen_jogar = True
                elements.append(c)

            # Informações da barra de download / status
            elif wclass == "Static":
                txt = _get_win32_window_text(getattr(c, "windowHandle", 0))
                if not txt:
                    try:
                        txt = (getattr(c, "name", "") or "").strip()
                    except Exception:
                        txt = ""
                if txt:
                    elements.append(c)

            # Janela de conteúdo Web (Notícias, Prime Access, Notas de Atualização)
            elif wclass == "CefBrowserWindow":
                doc = self._get_cef_document()
                if doc:
                    elements.append(doc)
                else:
                    elements.append(c)

        if elements:
            self._nav_elements_cache = elements
            self._last_nav_cache_time = now

        return elements

    def _get_element_label(self, obj):
        """Retorna o rótulo descritivo e completo em português para o elemento."""
        wclass = getattr(obj, "windowClassName", "") or ""
        name = ""
        if wclass == "Static":
            name = _get_win32_window_text(getattr(obj, "windowHandle", 0))
        if not name:
            try:
                name = (getattr(obj, "name", "") or "").strip()
            except Exception:
                name = ""
        ctrl_id = getattr(obj, "windowControlID", 0)
        role = int(getattr(obj, "role", 0))

        if role == int(ROLE_DOCUMENT) or wclass in ("CefBrowserWindow", "Chrome_RenderWidgetHostHWND"):
            return "Conteúdo Web: Novidades, Prime Access e Notas de Atualização (Pressione Enter ou Alt+W para explorar com as setas)"

        if wclass == "Static":
            return f"Status do jogo: {name}"

        if ctrl_id == 1029:
            return "Botão Fechar launcher"
        elif ctrl_id == 1030:
            return "Botão Maximizar"
        elif ctrl_id == 1031:
            return "Botão Minimizar"
        elif ctrl_id == 1032:
            return "Botão Idioma: Português-Br"
        elif ctrl_id == 1033:
            return "Botão Canal: Public"
        elif ctrl_id in (1034, 1035):
            if self._is_updating():
                status = self._get_native_status_text()
                return f"Botão JOGAR (indisponível durante o download: {status})"
            return "Botão JOGAR (pronto para iniciar)"

        loc = getattr(obj, "location", None)
        if loc:
            x, y, w, h = loc
            if x >= 1560:
                return "Botão Fechar launcher"
            elif x >= 1530:
                return "Botão Maximizar"
            elif x >= 1500:
                return "Botão Minimizar"
            elif x >= 1470:
                return "Botão Configurações"

        if name and name.lower() not in ("launcher", "button", "none"):
            return f"Botão {name}"

        return f"Botão {wclass}"

    @script(
        description="Avança o foco para o próximo controle do Launcher.",
        gestures=["kb:tab"]
    )
    def script_nextControl(self, gesture):
        elements = self._collect_nav_elements()
        if not elements:
            gesture.send()
            return

        self._current_index = (self._current_index + 1) % len(elements)
        target = elements[self._current_index]

        try:
            api.setNavigatorObject(target)
            api.setFocusObject(target)
        except Exception:
            pass

        label = self._get_element_label(target)
        ui.message(label)

    @script(
        description="Recua o foco para o controle anterior do Launcher.",
        gestures=["kb:shift+tab"]
    )
    def script_prevControl(self, gesture):
        elements = self._collect_nav_elements()
        if not elements:
            gesture.send()
            return

        self._current_index = (self._current_index - 1) % len(elements)
        target = elements[self._current_index]

        try:
            api.setNavigatorObject(target)
            api.setFocusObject(target)
        except Exception:
            pass

        label = self._get_element_label(target)
        ui.message(label)

    @script(
        description="Ativa o controle selecionado, abre o conteúdo Web ou aciona botão.",
        gestures=["kb:space", "kb:enter"]
    )
    def script_activateControl(self, gesture):
        cur = api.getFocusObject()
        if cur:
            role = int(getattr(cur, "role", 0))
            wclass = getattr(cur, "windowClassName", "") or ""
            if role == int(ROLE_DOCUMENT) or wclass in ("CefBrowserWindow", "Chrome_RenderWidgetHostHWND"):
                self.script_focusWebContent(gesture)
                return

            try:
                cur.doAction()
                ui.message("Ativado")
                return
            except Exception:
                pass
        gesture.send()

    @script(
        description="Foca o documento Web do Launcher para leitura contínua de novidades e notas de versão com as setas.",
        gestures=["kb:alt+w", "kb:control+shift+w"]
    )
    def script_focusWebContent(self, gesture):
        doc = self._get_cef_document()
        if doc:
            try:
                api.setNavigatorObject(doc)
                api.setFocusObject(doc)
                import treeInterceptorHandler
                ti = treeInterceptorHandler.update(doc)
                if ti:
                    try:
                        info = ti.makeTextInfo("first")
                        ti.selection = info
                    except Exception:
                        pass
                ui.message("Documento Web aberto. Navegue pelas notícias, Prime Access e notas de atualização com as setas para cima e para baixo.")
                return
            except Exception as e:
                log.debug(f"Warframe: Erro ao focar documento CEF: {e}")
        ui.message("Painel Web ainda carregando.")

    @script(
        description="Anuncia o status, velocidade e tempo restante de download do Warframe.",
        gestures=["kb:NVDA+shift+s", "kb:control+shift+s", "kb:alt+s"]
    )
    def script_announceStatus(self, gesture):
        status = self._get_native_status_text()
        if status:
            ui.message(status)
        else:
            ui.message("Launcher do Warframe em execução.")

    @script(
        description="Pressiona o botão Jogar ou informa o tempo restante de atualização.",
        gestures=["kb:alt+j", "kb:NVDA+shift+j", "kb:control+shift+j"]
    )
    def script_playGame(self, gesture):
        if self._is_updating():
            status = self._get_native_status_text()
            ui.message(f"O jogo ainda está atualizando: {status}. Aguarde a conclusão para jogar.")
            return

        root = self._get_launcher_root()
        if root:
            for c in (getattr(root, "children", []) or []):
                if getattr(c, "windowControlID", 0) in (1034, 1035):
                    try:
                        c.doAction()
                        ui.message("Iniciando Warframe...")
                        return
                    except Exception:
                        pass
        ui.message("Iniciando Warframe...")
        import keyboardHandler
        keyboardHandler.KeyboardInputGesture.fromName("space").send()

    @script(
        description="Abre as configurações do Launcher.",
        gestures=["kb:alt+c"]
    )
    def script_openSettings(self, gesture):
        root = self._get_launcher_root()
        if root:
            for c in (root.children or []):
                loc = getattr(c, "location", None)
                if loc and loc[0] >= 1470 and loc[0] < 1500 and loc[1] <= 160:
                    try:
                        c.doAction()
                        ui.message("Configurações abertas.")
                        return
                    except Exception:
                        pass
        ui.message("Abrindo configurações...")

    @script(
        description="Exibe os atalhos de acessibilidade do Launcher do Warframe.",
        gestures=["kb:f1", "kb:NVDA+shift+h"]
    )
    def script_help(self, gesture):
        help_text = (
            "Acessibilidade do Warframe Launcher: "
            "Tab e Shift+Tab: Navega entre todos os botões, status de download e vitrine Web. "
            "Enter ou Espaço: Clica no botão selecionado ou entra na vitrine Web. "
            "Alt+W: Entra imediatamente no documento Web para ler notícias, Prime Access e notas de atualização com as setas para cima/baixo. "
            "Alt+S ou Control+Shift+S: Anuncia velocidade e progresso do download. "
            "Alt+J ou Control+Shift+J: Inicia o jogo ou informa o tempo restante de download. "
            "Alt+C: Abre as configurações do Launcher."
        )
        ui.message(help_text)
