"""
Entrypoint: chạy FastAPI + HTTP server cho frontend.
Chạy từ project root: python run.py
"""
import os
import sys
import threading
import time
import webbrowser
import uvicorn
from dotenv import load_dotenv
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Load environment variables from .env file
load_dotenv()


class Server:
    """Chạy ứng dụng FastAPI với tùy chọn mở browser."""

    def __init__(
        self,
        app_module: str = "src.backends.api.v1.app:app",
        host: str = "0.0.0.0",
        port: int = 8000,
        reload: bool = False,  # ← DISABLED TO PREVENT RELOAD LOOPS
        open_browser: bool = True,
        browser_delay: float = 2.0,
    ) -> None:
        self.app_module = app_module
        self.host = host
        self.port = port
        self.reload = reload
        self.open_browser = open_browser
        self.browser_delay = browser_delay
        self._root_dir = os.path.dirname(os.path.abspath(__file__))

    def _check_requirements(self) -> bool:
        """Kiểm tra xem tất cả services có sẵn không."""
        print("\n✅ Kiểm tra services...")
        try:
            from src.backends.core.services.pgConnectionService import get_connection_service
            conn = get_connection_service()
            conn.execute_query("SELECT 1", fetch='one', dict_cursor=False)
            print("  ✅ Database OK")
            
            from src.backends.core.services.enhancedEmbedding import create_embedding_service
            emb = create_embedding_service()
            print("  ✅ Embedding Model OK")
            
            from src.backends.api.v1.app import app
            print("  ✅ API App OK")
            print()
            return True
        except Exception as e:
            print(f"  ❌ Lỗi: {str(e)}\n")
            return False

    def _launch_browser(self) -> None:
        time.sleep(self.browser_delay)
        webbrowser.open("http://localhost:3000")

    def _serve_frontend(self) -> None:
        """Serve frontend HTML files via HTTP on port 3000."""
        frontend_dir = os.path.join(self._root_dir, "public", "shared")
        
        # Create a custom handler that serves from the frontend directory
        import os as _os
        from http.server import SimpleHTTPRequestHandler
        
        class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
            def translate_path(self, path):
                # Override to serve from frontend directory
                path = SimpleHTTPRequestHandler.translate_path(self, path)
                relpath = _os.path.relpath(path, _os.getcwd())
                return _os.path.join(frontend_dir, relpath)
            
            def log_message(self, format, *args):
                # Suppress logging
                pass
        
        try:
            from http.server import ThreadingHTTPServer
            server = ThreadingHTTPServer(("127.0.0.1", 3000), CustomHTTPRequestHandler)
            print("✅ Frontend server running on http://localhost:3000")
            server.serve_forever()
        except ImportError:
            # Fallback for older Python versions
            from http.server import HTTPServer
            server = HTTPServer(("127.0.0.1", 3000), CustomHTTPRequestHandler)
            print("✅ Frontend server running on http://localhost:3000")
            server.serve_forever()
        except OSError as e:
            print(f"⚠️ Frontend server error: {e}")

    def run(self) -> None:
        # Kiểm tra trước
        if not self._check_requirements():
            print("❌ Không thể khởi động server!")
            sys.exit(1)
        
        print("="*70)
        print("🚀 KHỞI ĐỘNG HỆ THỐNG".center(70))
        print("="*70)
        print("\n📍 API Server: http://localhost:8000")
        print("📍 Frontend: http://localhost:3000")
        print("📖 API Docs: http://localhost:8000/docs")
        print("📚 ReDoc: http://localhost:8000/redoc\n")
        print("="*70 + "\n")
        
        # Start frontend HTTP server
        frontend_thread = threading.Thread(target=self._serve_frontend, daemon=True)
        frontend_thread.start()
        time.sleep(1)
        
        # Launch browser
        if self.open_browser:
            threading.Thread(target=self._launch_browser, daemon=True).start()
        
        try:
            uvicorn.run(
                self.app_module,
                host=self.host,
                port=self.port,
                reload=self.reload,
            )
        except KeyboardInterrupt:
            print("\n\n👋 Server dừng.")
            sys.exit(0)


def main() -> None:
    server = Server()
    server.run()


if __name__ == "__main__":
    main()
