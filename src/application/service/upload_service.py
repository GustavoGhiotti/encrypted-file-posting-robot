from pathlib import Path
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.shared.exceptions import UploadButtonNotFound, UploadDialogNotFound
from src.shared.utils.env_load import Settings


class SiriusUploadService:
    UPLOAD_MENU_SELECTOR = "#Upload-Action"
    UPLOAD_FRAME_SELECTOR = "#UploadFrame"
    UPLOAD_FRAME_FALLBACK_SELECTOR = "#UploadFrame1"
    UPLOAD_FRAME_GENERIC_SELECTOR = "iframe"
    FILE_INPUT_SELECTOR = "#file"
    UPLOAD_BUTTON_SELECTOR = "#btn-UploadButton"

    def _get_upload_frame(self, page):
        frame_element = page.query_selector(self.UPLOAD_FRAME_SELECTOR)
        if frame_element and frame_element.is_visible():
            frame = frame_element.content_frame()
            if frame:
                return frame

        fallback_element = page.query_selector(self.UPLOAD_FRAME_FALLBACK_SELECTOR)
        if fallback_element and fallback_element.is_visible():
            return fallback_element.content_frame()

        for element in page.query_selector_all(self.UPLOAD_FRAME_GENERIC_SELECTOR):
            if not element.is_visible():
                continue
            src = element.get_attribute("src") or ""
            if "Upload.htm" in src:
                frame = element.content_frame()
                if frame:
                    return frame

        frame = page.frame(name="UploadFrame")
        if frame:
            return frame

        return None

    def _wait_file_input_ready(self, frame) -> None:
        frame.wait_for_load_state("domcontentloaded", timeout=Settings.SIRIUS_TIMEOUT)
        frame.wait_for_selector(
            self.FILE_INPUT_SELECTOR,
            state="visible",
            timeout=Settings.SIRIUS_TIMEOUT,
        )
        end = time.time() + (Settings.SIRIUS_TIMEOUT / 1000)
        while time.time() < end:
            disabled = frame.eval_on_selector(
                self.FILE_INPUT_SELECTOR,
                "el => !!el.disabled",
            )
            if not disabled:
                return
            time.sleep(0.1)

    def _open_upload_modal(self, page) -> None:
        page.click(self.UPLOAD_MENU_SELECTOR)
        try:
            page.wait_for_selector(
                self.UPLOAD_FRAME_SELECTOR,
                state="attached",
                timeout=Settings.SIRIUS_TIMEOUT,
            )
        except PlaywrightTimeoutError as exc:
            raise UploadDialogNotFound(
                f"Iframe de upload nao encontrado: {self.UPLOAD_FRAME_SELECTOR}"
            ) from exc

        frame = self._get_upload_frame(page)
        if not frame:
            raise UploadDialogNotFound("Iframe de upload nao acessivel")
        try:
            frame.wait_for_selector(
                self.FILE_INPUT_SELECTOR,
                state="attached",
                timeout=Settings.SIRIUS_TIMEOUT,
            )
        except PlaywrightTimeoutError as exc:
            raise UploadDialogNotFound(
                f"Input de arquivo nao encontrado no iframe: {self.FILE_INPUT_SELECTOR}"
            ) from exc

    def _set_file(self, page, arquivo: Path) -> None:
        frame = self._get_upload_frame(page)
        if not frame:
            raise UploadDialogNotFound("Iframe de upload nao acessivel")
        try:
            self._wait_file_input_ready(frame)
            for _ in range(2):
                frame.set_input_files(self.FILE_INPUT_SELECTOR, [])
                frame.set_input_files(self.FILE_INPUT_SELECTOR, str(arquivo))
                frame.eval_on_selector(
                    self.FILE_INPUT_SELECTOR,
                    "el => el.dispatchEvent(new Event('change', { bubbles: true }))"
                )
                selected = frame.eval_on_selector(
                    self.FILE_INPUT_SELECTOR,
                    "el => el.files && el.files.length"
                )
                if selected:
                    return
                time.sleep(0.2)
                frame = self._get_upload_frame(page)
                if not frame:
                    break
                self._wait_file_input_ready(frame)
        except PlaywrightTimeoutError as exc:
            raise UploadDialogNotFound(
                f"Input de arquivo nao encontrado: {self.FILE_INPUT_SELECTOR}"
            ) from exc
        raise UploadDialogNotFound(
            f"Arquivo nao selecionado no input: {self.FILE_INPUT_SELECTOR}"
        )

    def _click_upload(self, page) -> None:
        button = page.locator(self.UPLOAD_BUTTON_SELECTOR)
        try:
            button.wait_for(state="visible", timeout=Settings.SIRIUS_TIMEOUT)
            button.wait_for(state="attached", timeout=Settings.SIRIUS_TIMEOUT)
            end = time.time() + (Settings.SIRIUS_TIMEOUT / 1000)
            while time.time() < end:
                if button.first.is_enabled():
                    break
                time.sleep(0.1)
            button.first.click(force=True)
            return
        except PlaywrightTimeoutError:
            pass

        span_button = page.locator("#UploadButton")
        try:
            span_button.wait_for(state="visible", timeout=Settings.SIRIUS_TIMEOUT)
            span_button.first.click(force=True)
            return
        except PlaywrightTimeoutError:
            pass

        try:
            clicked = page.evaluate(
                """
                () => {
                    const form = document.forms['UploadFile'] || document.querySelector('form[name="UploadFile"]');
                    if (form && typeof window.VerifyUpload === 'function') {
                        window.VerifyUpload(form);
                        return true;
                    }
                    const btn = document.querySelector('#btn-UploadButton');
                    if (btn) {
                        btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                        btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                        btn.click();
                        return true;
                    }
                    return false;
                }
                """
            )
            if clicked:
                return
        except PlaywrightTimeoutError:
            pass

        frame = self._get_upload_frame(page)
        if frame:
            try:
                clicked = frame.evaluate(
                    """
                    () => {
                        if (window.parent && typeof window.parent.VerifyUpload === 'function') {
                            const form = window.parent.document.forms['UploadFile'] || window.parent.document.querySelector('form[name="UploadFile"]');
                            if (form) {
                                window.parent.VerifyUpload(form);
                                return true;
                            }
                        }
                        return false;
                    }
                    """
                )
                if clicked:
                    return
            except PlaywrightTimeoutError:
                pass

        raise UploadButtonNotFound(
            f"Botao de upload nao localizado: {self.UPLOAD_BUTTON_SELECTOR}"
        )

    def upload_arquivos(self, arquivos_gpg: list[Path]) -> None:
        if not arquivos_gpg:
            raise ValueError("Lista de arquivos vazia")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=300,
            )

            context = browser.new_context(
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

            page.dblclick("text=entrada")
            page.wait_for_function(
                "() => document.title.toLowerCase().includes('entrada')"
            )

            page.bring_to_front()
            page.wait_for_timeout(800)

            for idx, arquivo in enumerate(arquivos_gpg, start=1):
                if not arquivo.exists():
                    raise FileNotFoundError(f"Arquivo nao encontrado: {arquivo}")

                arquivo_absoluto = arquivo.resolve()

                self._open_upload_modal(page)
                self._set_file(page, arquivo_absoluto)
                self._click_upload(page)

                print(
                    f"Upload {idx}/{len(arquivos_gpg)} enviado: {arquivo_absoluto.name}"
                )

                time.sleep(4)
                page.keyboard.press("Escape")
                page.wait_for_timeout(600)

            browser.close()
