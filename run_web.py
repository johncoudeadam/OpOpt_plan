from webapp.app import app

if __name__ == '__main__':
    print("Starting Rail Operations & Maintenance Optimizer web application...")
    print("Navigate to http://127.0.0.1:5000/ in your browser")
    app.run(debug=True, host='127.0.0.1', port=5000)
