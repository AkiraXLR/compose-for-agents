from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello from localhost:5000!'

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
http://localhost:5000/
