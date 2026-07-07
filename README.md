# BlueAI Laptop Server - Bluetooth LLM Bridge

Turn your laptop into a private, local LLM companion for your Android device.

This backend bridges the Android app with AI models running locally on your machine (via **Ollama**, **LM Studio**, or **llama.cpp/llama-server**) or in the cloud (**OpenAI**, **Anthropic Claude**) using standard **Bluetooth RFCOMM/SPP**.

---

## Features

- 📶 **Fully Offline Local AI**: Talk to models on your laptop without needing an internet connection.
- 📱 **QR Code Connection**: The server displays an ASCII QR code in your terminal. Scan it with the BlueAI app to pair instantly.
- 🤖 **Multi-Engine Support**:
  - **Ollama** (Dynamic models like `llama3`, `mistral`, `gemma`)
  - **LM Studio** / **llama-server** (Direct OpenAI-compatible local completions)
  - **OpenAI API** (`gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`)
  - **Anthropic Claude** (`claude-3-5-sonnet-20240620`, etc.)
- 💻 **Cross-Platform**: Support for **Windows**, **macOS**, and **Linux** utilizing dual RFCOMM socket and Serial interface emulators.

---

## Setup Instructions

### 1. Prerequisites
Make sure you have **Python 3.9+** installed on your laptop.

### 2. Install Dependencies
Navigate to the `backend` folder on your laptop and install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Start your AI Engine (Ollama / LM Studio)
- **Ollama**: Download from [ollama.com](https://ollama.com). Once installed, download and start a model (e.g. `llama3`):
  ```bash
  ollama run llama3
  ```
- **LM Studio**: Open LM Studio, download a GGUF model, navigate to the "Local Server" tab, and click **Start Server**.

---

## Running the Server

### 1. Interactive Setup Wizard
Run the setup wizard to configure your preferred AI backend, model name, and optional API keys:
```bash
python server.py --setup
```

### 2. Normal Startup
Simply start the server:
```bash
python server.py
```

### 3. Scanning the QR Code
Upon startup, the server automatically tries to detect your local Bluetooth MAC address, generates a scannable **QR Code** inside your terminal, and saves a high-quality copy to `connection_qr.png`.

Open your **BlueAI Link** Android app, click the **Settings** gear button, and use the **QR Connection Scanner** to automatically find and connect to your laptop.

---

## Operating System Guides

### Windows & Linux
These systems support native Bluetooth RFCOMM sockets.
1. Turn on Bluetooth and make your laptop discoverable.
2. Select Option `[1]` (Native RFCOMM Socket) when prompted.
3. Launch your Android App, click the Bluetooth scan or QR scanner, and connect.

### macOS (Apple Silicon & Intel)
Since macOS blocks native user-space RFCOMM sockets, you should use **Serial emulation (Virtual COM Port)**.
1. Turn on Bluetooth on your Mac.
2. On your Android device, go to system Settings and pair with your Mac.
3. On your Mac, open **Bluetooth Settings** -> **Advanced** (or search macOS "Serial Ports") and ensure an incoming serial port is created for the paired Android phone.
4. Run `python server.py` and select Option `[2]` (Serial/COM Emulation).
5. Select the COM port corresponding to your Android connection (usually starts with `/dev/cu.Bluetooth-Incoming-Port` or similar).

---

## File Structure

- `server.py`: Main executable bridge code.
- `requirements.txt`: Python package list.
- `config.json`: Automatically created file to store your credentials and backend choices.
- `connection_qr.png`: High-resolution connection QR code image.
