import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.shared.utils.env_load import Settings


class SiriusDownloadService:
    def __init__(self) -> None:
        self.saida_folder_name = os.getenv("SIRIUS_SAIDA_FOLDER_NAME", "saida")
        self.download_menu_selector = os.getenv(
            "SIRIUS_DOWNLOAD_MENU_SELECTOR", "#Download-Action"
        )
        self.download_button_selector = os.getenv(
            "SIRIUS_DOWNLOAD_BUTTON_SELECTOR", "#btn-DownloadButton"
        )
        self.file_list_selector = os.getenv("SIRIUS_FILE_LIST_SELECTOR", "#ListFiles-rows")

    def _listar_arquivos(self, page, extensoes: tuple[str, ...]) -> list[str]:
        padrao = re.compile(
            r"\b[^\s]+\.(?:%s)\b" % "|".join(
                re.escape(ext.lstrip(".")) for ext in extensoes
            ),
            re.IGNORECASE,
        )

        page.wait_for_selector(
            "#ListFiles-rows .aw-item-text",
            state="visible",
            timeout=Settings.SIRIUS_TIMEOUT,
        )

        textos = page.evaluate(
            """
            (sel) => {
                const container = document.querySelector(sel);
                if (!container) return [];
                return Array.from(container.querySelectorAll('.aw-item-text'))
                    .map(el => (el.textContent || '').trim())
                    .filter(Boolean);
            }
            """,
            self.file_list_selector,
        )

        encontrados: list[str] = []
        for texto in textos:
            for match in padrao.findall(texto):
                encontrados.append(match)

        vistos = set()
        resultado = []
        for nome in encontrados:
            if nome in vistos:
                continue
            vistos.add(nome)
            resultado.append(nome)

        return sorted(resultado)

    def _selecionar_arquivo(self, page, nome: str) -> None:
        try:
            clicked = page.evaluate(
                """
                (nome) => {
                    const items = Array.from(document.querySelectorAll('#ListFiles-rows .aw-item-text'));
                    const target = items.find(el => (el.textContent || '').trim() === nome);
                    if (!target) return false;
                    const row = target.closest('.aw-grid-row');
                    if (!row) return false;
                    row.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    row.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                    row.click();
                    return row.className.includes('aw-rows-selected') || row.className.includes('aw-rows-current');
                }
                """,
                nome,
            )
            if clicked:
                return
        except PlaywrightTimeoutError:
            pass

        texto = page.locator("#ListFiles-rows .aw-item-text", has_text=nome)
        try:
            texto.first.wait_for(state="visible", timeout=Settings.SIRIUS_TIMEOUT)
            texto.first.click(force=True)
            return
        except PlaywrightTimeoutError:
            pass

        regex_nome = re.escape(nome)
        texto = page.locator(f"#ListFiles-rows .aw-item-text:has-text(/{regex_nome}/i)")
        try:
            texto.first.wait_for(state="visible", timeout=3000)
            texto.first.click(force=True)
            return
        except PlaywrightTimeoutError:
            pass

        try:
            page.click(f"text={nome}", force=True)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Arquivo nao encontrado na lista: {nome}") from exc

    def _clicar_download(self, page) -> None:
        toolbar_selectors = (
            self.download_menu_selector,
            self.download_button_selector,
            "img[alt='Download']",
            "a:has-text('Download')",
            "button:has-text('Download')",
            "span:has-text('Download')",
            "text=Download",
        )
        for selector in toolbar_selectors:
            try:
                page.click(selector, timeout=1500, force=True)
                return
            except PlaywrightTimeoutError:
                continue

        try:
            clicked = page.evaluate(
                """
                () => {
                    const candidates = Array.from(document.querySelectorAll('[title], [aria-label]'));
                    const el = candidates.find(node => {
                        const t = (node.getAttribute('title') || node.getAttribute('aria-label') || '').toLowerCase();
                        return t.includes('download');
                    });
                    if (!el) return false;
                    el.click();
                    return true;
                }
                """
            )
            if clicked:
                return
        except PlaywrightTimeoutError:
            pass

        try:
            page.keyboard.press("Enter")
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Acao de download nao localizada") from exc

    def _baixar_arquivo(self, page) -> object:
        try:
            with page.expect_download(timeout=Settings.SIRIUS_TIMEOUT) as download_info:
                self._clicar_download(page)
            return download_info.value
        except PlaywrightTimeoutError:
            return None

    def download_arquivos(
        self,
        destino: Path,
        extensoes: tuple[str, ...] | None = None,
    ) -> list[Path]:
        destino.mkdir(parents=True, exist_ok=True)
        extensoes = extensoes or (".gpg", ".zip")

        arquivos_baixados: list[Path] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=300,
            )

            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            page.set_default_timeout(Settings.SIRIUS_TIMEOUT)
            page.set_default_navigation_timeout(Settings.SIRIUS_TIMEOUT)

            page.goto(Settings.SIRIUS_URL)

            page.wait_for_selector("#user-box-text")
            page.fill("#user-box-text", Settings.SIRIUS_USER)
            page.fill("#pword-box-text", Settings.SIRIUS_PASSWORD)
            page.click("#btn-LoginButton")

            page.wait_for_url("**/Web%20Client/ListDir.htm")
            page.wait_for_selector("text=Principal")

            page.dblclick(f"text={self.saida_folder_name}")
            page.wait_for_function(
                f"() => document.title.toLowerCase().includes('{self.saida_folder_name.lower()}')"
            )

            page.bring_to_front()
            page.wait_for_timeout(800)

            arquivos_remotos = self._listar_arquivos(page, extensoes)
            for nome in arquivos_remotos:
                destino_arquivo = destino / nome
                if destino_arquivo.exists():
                    arquivos_baixados.append(destino_arquivo)
                    continue

                self._selecionar_arquivo(page, nome)
                download = self._baixar_arquivo(page)
                if not download:
                    continue

                download.save_as(destino_arquivo)
                arquivos_baixados.append(destino_arquivo)
                time.sleep(0.5)

            browser.close()

        return arquivos_baixados
