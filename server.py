"""Простое веб-приложение Memo на стандартной библиотеке Python.

Приложение отдаёт HTML-страницы проекта (главная, каталог, категория,
контакты, а также страницы ошибок 404 и 500), раздаёт статические файлы
из каталога ``static`` и принимает POST-запрос формы обратной связи,
выводя полученные данные в консоль.
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

# Кириллица в консоли Windows при перенаправленном выводе.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"
STATIC_DIR = BASE_DIR / "static"
STATIC_URL_PREFIX = "/static/"

GET_ROUTES = {
    "/": "index.html",
    "/index": "index.html",
    "/catalog": "catalog.html",
    "/category": "category.html",
    "/contacts": "contacts.html",
}

FLASH_PLACEHOLDER = "<!-- FLASH_MESSAGE -->"
SUCCESS_ALERT = (
    '<div class="alert alert-success" role="alert">'
    "Спасибо! Сообщение отправлено."
    "</div>"
)


class MemoRequestHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов для всех страниц проекта."""

    server_version = "MemoHTTP/1.0"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ #
    # HTTP-методы
    # ------------------------------------------------------------------ #
    def do_GET(self) -> None:  # noqa: N802 (имя задано стандартной библиотекой)
        try:
            self._handle_get()
        except Exception:  # pragma: no cover - защитная ветка
            traceback.print_exc()
            self._send_page("500.html", status=500)

    def do_POST(self) -> None:  # noqa: N802 (имя задано стандартной библиотекой)
        try:
            self._handle_post()
        except Exception:  # pragma: no cover - защитная ветка
            traceback.print_exc()
            self._send_page("500.html", status=500)

    # ------------------------------------------------------------------ #
    # Логика GET
    # ------------------------------------------------------------------ #
    def _handle_get(self) -> None:
        path = urlsplit(self.path).path

        if path.startswith(STATIC_URL_PREFIX):
            self._send_static(path)
            return

        page = GET_ROUTES.get(path)
        if page is None:
            self._send_page("404.html", status=404)
            return

        self._send_page(page)

    # ------------------------------------------------------------------ #
    # Логика POST
    # ------------------------------------------------------------------ #
    def _handle_post(self) -> None:
        path = urlsplit(self.path).path
        data = self._read_form_data()

        print(f"\nPOST {path}", flush=True)
        if data:
            for key, value in data.items():
                print(f"  {key}: {value}", flush=True)
        else:
            print("  (пустое тело запроса)", flush=True)

        if path == "/contacts":
            self._send_page(
                "contacts.html",
                replacements={FLASH_PLACEHOLDER: SUCCESS_ALERT},
            )
            return

        self._send_page("404.html", status=404)

    def _read_form_data(self) -> dict[str, str]:
        """Читает тело POST-запроса и возвращает данные формы."""
        length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(length) if length else b""
        content_type = self.headers.get("Content-Type", "")

        if "application/x-www-form-urlencoded" in content_type:
            decoded = raw_body.decode("utf-8", errors="replace")
            return {key: values[0] for key, values in parse_qs(decoded).items()}

        if raw_body:
            return {"body": raw_body.decode("utf-8", errors="replace")}

        return {}

    # ------------------------------------------------------------------ #
    # Отдача содержимого
    # ------------------------------------------------------------------ #
    def _send_page(
        self,
        file_name: str,
        status: int = 200,
        replacements: dict[str, str] | None = None,
    ) -> None:
        """Читает HTML-страницу и отправляет её клиенту."""
        file_path = PAGES_DIR / file_name
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
        except FileNotFoundError:
            self.send_error(404, "HTML page not found")
            return

        for old, new in (replacements or {}).items():
            content = content.replace(old, new)

        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: str) -> None:
        """Отдаёт статический файл (CSS, изображения и т.п.)."""
        relative = path[len(STATIC_URL_PREFIX):]
        static_root = STATIC_DIR.resolve()
        file_path = (STATIC_DIR / relative).resolve()

        if static_root not in file_path.parents or not file_path.is_file():
            self._send_page("404.html", status=404)
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        with open(file_path, "rb") as file:
            body = file.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Веб-приложение Memo")
    parser.add_argument("--host", default="127.0.0.1", help="Хост (по умолчанию 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Порт (по умолчанию 8000)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MemoRequestHandler)
    print(f"Сервер запущен: http://{args.host}:{args.port}")
    print("Для остановки нажмите Ctrl+C\n", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
