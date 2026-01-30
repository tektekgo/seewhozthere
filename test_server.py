import http.server
import socketserver

PORT = 8888

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler ):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            html_content = """
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Pure Python Test</title>
                </head>
                <body>
                    <h1>This is a test.</h1>
                    <p>This server has no dependencies.</p>
                </body>
            </html>
            """
            self.wfile.write(bytes(html_content, "utf8"))
        else:
            super().do_GET()

Handler = MyHttpRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"--- Pure Python server running at http://localhost:{PORT} ---" )
    print("--- Press CTRL+C to stop. ---")
    httpd.serve_forever( )
