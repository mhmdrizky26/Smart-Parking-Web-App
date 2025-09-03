SMART PARKING DETECTION
1. Requirements
On your computer (server):
	- Python 3.8+
	- Flask, OpenCV, Requests, NumPy	
	- A webcam or IP camera

On the hardware side:
	- ESP32 board
	- Arduino IDE (with ESP32 board support installed)
	- LEDs or other indicators wired to ESP32 pins

2. Setup the ESP32
- Open the parkiran.ino file in Arduino IDE.
- Update WiFi credentials in the code:
	const char* ssid = "YOUR_WIFI_SSID";
	const char* password = "YOUR_WIFI_PASSWORD";

- Ensure the ESP32’s IP (shown after uploading) matches the one in app.py:
	ESP32_URL = "http://<ESP32_IP>/update"

- Connect your ESP32 to your computer and upload the sketch.
	After reboot, open Serial Monitor to confirm it connects to WiFi and shows its IP address.

3. Setup the Python Application
Install required packages:
	pip install flask opencv-python requests numpy

In app.py, check:
	- ESP32_URL → Use the ESP32 IP address printed in Serial Monitor.
	- Camera source (camera_loop(source=0) for default webcam).

Start the application:
	python app.py

4. Run the System
Open a browser at http://localhost:5000

You will see:
	- Live camera feed (left) with detected slots.
	- Parking slot status (right) updated in real-time.

The system will automatically send slot data to the ESP32 via HTTP POST.

The ESP32 will:
	- Turn LEDs red/green depending on slot occupancy.
	- Reflect the same status shown on the web dashboard.

5. Stopping the System

To stop the Flask server → press CTRL + C in the terminal.

To reset ESP32 → press the reset button on the board.
