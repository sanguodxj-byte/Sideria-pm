from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({}).encode('utf-8'))
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("=== WORKFLOW HAS BEEN SUBMITTED ===")
        # Instead of printing everything, print the node counts to satisfy the test
        data = json.loads(post_data.decode('utf-8'))
        print(f"Total nodes in workflow: {len(data['prompt'])}")
        has_loadimage = any(node['class_type'] == 'LoadImage' for node in data['prompt'].values())
        has_controlnet = any(node['class_type'] == 'ControlNetApplyAdvanced' for node in data['prompt'].values())
        print(f"Contains LoadImage: {has_loadimage}")
        print(f"Contains ControlNetApplyAdvanced: {has_controlnet}")
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"prompt_id": "test-123"}).encode('utf-8'))

# Make sure it listens on the same port config.json points to (8888)
httpd = HTTPServer(('127.0.0.1', 8888), SimpleHTTPRequestHandler)
print("Dummy ComfyUI server ready on 8888.")
httpd.serve_forever()
