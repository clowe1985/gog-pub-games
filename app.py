from flask import Flask, request, jsonify, send_from_directory
import threading

app = Flask(__name__, static_folder='.', static_url_path='')

# Serve the web app (index.html, script.js, style.css, images, etc.)
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# API endpoint - this is where the web app talks to the bot
@app.route('/api/action', methods=['POST'])
def api_action():
    data = request.get_json()
    action = data.get('action')

    if action == "enter_pub":
        # ← We'll add wallet check here soon
        return jsonify({"status": "ENTER_OK"})

    if action == "pickteam_web":
        # ← We'll add claim logic here later
        return jsonify({"status": "CLAIM_SUCCESS"})

    return jsonify({"status": "UNKNOWN_ACTION"})

# Run Flask in background
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Flask server started on port 5000")
