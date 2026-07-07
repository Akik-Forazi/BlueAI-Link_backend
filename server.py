#!/usr/bin/env python3
"""
BlueAI Laptop Server - Bluetooth LLM Bridge
Supports:
- Ollama
- LM Studio / llama-server (llama.cpp)
- OpenAI API
- Anthropic Claude API
- Custom OpenAI-compatible endpoints

Generates a terminal QR code & saves "connection_qr.png" to make pairing with the Android App instant.
"""

import os
import sys
import json
import socket
import urllib.request
import urllib.error
import time

# Attempt to import optional QR code and Serial libraries
try:
    import qrcode
    QR_SUPPORT = True
except ImportError:
    QR_SUPPORT = False

try:
    import serial
    SERIAL_SUPPORT = True
except ImportError:
    SERIAL_SUPPORT = False

# Default Config
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "backend": "ollama",          # "ollama", "lm_studio", "openai", "anthropic"
    "model": "llama3",            # Model name or ID
    "ollama_url": "http://localhost:11434/api/generate",
    "lm_studio_url": "http://localhost:1234/v1/chat/completions",
    "openai_url": "https://api.openai.com/v1/chat/completions",
    "openai_api_key": "",
    "anthropic_url": "https://api.anthropic.com/v1/messages",
    "anthropic_api_key": "",
    "bluetooth_port": 1,
    "bluetooth_uuid": "00001101-0000-1000-8000-00805F9B34FB",
    "mac_address": ""             # Your laptop's Bluetooth address
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                # Merge defaults for any missing keys
                config = DEFAULT_CONFIG.copy()
                config.update(loaded)
                return config
        except Exception as e:
            print(f"Warning: Could not read {CONFIG_FILE}, using defaults. Error: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        print(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving config: {e}")

def get_local_mac_address():
    # Attempt to auto-detect Bluetooth MAC Address
    # 1. Linux (hciconfig)
    if sys.platform.startswith("linux"):
        try:
            import subprocess
            out = subprocess.check_output(["hciconfig"], stderr=subprocess.DEVNULL)
            for line in out.decode("utf-8", errors="ignore").split("\n"):
                if "BD Address" in line:
                    return line.split("BD Address:")[1].split()[0].strip()
        except Exception:
            pass
            
    # 2. macOS (system_profiler)
    elif sys.platform == "darwin":
        try:
            import subprocess
            out = subprocess.check_output(["system_profiler", "SPBluetoothDataType"], stderr=subprocess.DEVNULL)
            for line in out.decode("utf-8", errors="ignore").split("\n"):
                if "Address:" in line or "MAC Address:" in line:
                    parts = line.split(":")
                    if len(parts) >= 6:
                        return ":".join(parts[-6:]).strip()
        except Exception:
            pass
            
    # 3. Windows (getmac or registry)
    elif sys.platform == "win32":
        try:
            import subprocess
            # Query getmac
            out = subprocess.check_output(["getmac"], stderr=subprocess.DEVNULL)
            # Find a MAC address pattern
            import re
            macs = re.findall(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", out.decode())
            if macs:
                # Returns first network/bluetooth MAC as fallback
                return macs[0].replace("-", ":")
        except Exception:
            pass
            
    return ""

def generate_qr_code(mac_address, uuid):
    if not mac_address:
        print("\n[QR Code] No MAC address configured. Skipping QR Code generation.")
        print("Tip: Run setup or add your laptop's Bluetooth MAC to config.json to enable instant QR pairing!")
        return

    # Create connection dictionary
    conn_data = {
        "address": mac_address,
        "uuid": uuid,
        "name": socket.gethostname()
    }
    qr_string = json.dumps(conn_data)
    
    print("\n" + "="*60)
    print("                 CONNECTION QR CODE                      ")
    print("="*60)
    
    if QR_SUPPORT:
        try:
            # Print ASCII QR Code to Terminal
            qr = qrcode.QRCode(version=1, box_size=1, border=2)
            qr.add_data(qr_string)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
            
            # Save QR Image file
            img_qr = qrcode.make(qr_string)
            img_qr.save("connection_qr.png")
            print("\n[QR Code] QR Code saved as 'connection_qr.png' in the current directory.")
            print("Scan this QR code using the BlueAI mobile app to connect instantly!")
        except Exception as e:
            print(f"Error printing ASCII QR: {e}")
    else:
        print(f"\nBluetooth MAC Address: {mac_address}")
        print("Install 'qrcode' and 'pillow' to generate a scannable QR Code:")
        print("  pip install qrcode pillow")
        print(f"\nQR Raw Data: {qr_string}")
        
    print("="*60 + "\n")

def call_ollama(prompt, config):
    payload = {
        "model": config["model"],
        "prompt": prompt,
        "stream": True
    }
    req = urllib.request.Request(
        config["ollama_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        for line in response:
            if line:
                resp_json = json.loads(line.decode("utf-8"))
                chunk = resp_json.get("response", "")
                if chunk:
                    yield chunk

def call_openai_compatible(prompt, config, url, api_key):
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req) as response:
        for line in response:
            line_decoded = line.decode("utf-8").strip()
            if line_decoded.startswith("data:"):
                data_content = line_decoded[5:].strip()
                if data_content == "[DONE]":
                    break
                try:
                    data_json = json.loads(data_content)
                    choices = data_json.get("choices", [])
                    if choices:
                        chunk = choices[0].get("delta", {}).get("content", "")
                        if chunk:
                            yield chunk
                except Exception:
                    pass

def call_anthropic(prompt, config):
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "stream": True
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["anthropic_api_key"],
        "anthropic-version": "2023-06-01"
    }
    req = urllib.request.Request(
        config["anthropic_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req) as response:
        for line in response:
            line_decoded = line.decode("utf-8").strip()
            if line_decoded.startswith("event:"):
                continue
            if line_decoded.startswith("data:"):
                data_content = line_decoded[5:].strip()
                try:
                    data_json = json.loads(data_content)
                    event_type = data_json.get("type")
                    if event_type == "content_block_delta":
                        chunk = data_json.get("delta", {}).get("text", "")
                        if chunk:
                            yield chunk
                except Exception:
                    pass

def stream_llm_response(prompt, config):
    backend = config["backend"].lower()
    print(f"\n[AI Request] Querying backend '{backend}' using model '{config['model']}'...")
    
    try:
        if backend == "ollama":
            yield from call_ollama(prompt, config)
        elif backend == "lm_studio":
            yield from call_openai_compatible(prompt, config, config["lm_studio_url"], "")
        elif backend == "openai":
            if not config["openai_api_key"]:
                yield "[Error: OpenAI API Key is empty in config.json!]"
                return
            yield from call_openai_compatible(prompt, config, config["openai_url"], config["openai_api_key"])
        elif backend == "anthropic":
            if not config["anthropic_api_key"]:
                yield "[Error: Anthropic API Key is empty in config.json!]"
                return
            yield from call_anthropic(prompt, config)
        else:
            yield f"[Error: Unknown backend '{backend}']"
    except Exception as e:
        yield f"\n[Backend Error: {str(e)}. Please make sure your server/API key is valid and running.]"

def handle_client_connection(client_name, send_func, recv_func):
    print(f"Client connected: {client_name}")
    buffer = ""
    while True:
        try:
            data = recv_func()
            if not data:
                break
            buffer += data.decode("utf-8", errors="ignore")
            if "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                prompt = line.strip()
                if not prompt:
                    continue
                
                print(f"User Prompt Received: '{prompt}'")
                
                # Stream results to Android
                for chunk in stream_llm_response(prompt, global_config):
                    send_func(chunk.encode("utf-8"))
                
                # Terminate response stream with a custom boundary if needed, 
                # or let it end naturally. Android reads sequentially.
                
        except (IOError, ConnectionResetError):
            print("Connection lost.")
            break
        except Exception as e:
            print(f"Error handling client data: {e}")
            break
    print("Client disconnected.")

def run_bluetooth_socket_server(config):
    port = config["bluetooth_port"]
    uuid = config["bluetooth_uuid"]
    
    print("\nStarting RFCOMM Bluetooth Socket Server...")
    try:
        server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        server_sock.bind(("", port))
        server_sock.listen(1)
        print(f"Bluetooth socket bound to port {port}.")
    except Exception as e:
        print(f"Failed to create native RFCOMM socket: {e}")
        print("Note: Windows 10/11 & Linux support native AF_BLUETOOTH. macOS requires Serial Emulation instead.")
        return False

    # Advertise via pybluez if available
    try:
        import bluetooth
        bluetooth.advertise_service(
            server_sock, "BlueAI Bridge Server",
            service_id=uuid,
            service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE]
        )
        print("Bluetooth Service advertised successfully via PyBluez.")
    except ImportError:
        print("PyBluez not installed. Connection works with generic SPP profiles.")

    try:
        while True:
            print("\nWaiting for Android device connection...")
            client_sock, client_info = server_sock.accept()
            
            def send(data):
                client_sock.sendall(data)
                
            def recv():
                return client_sock.recv(1024)
                
            handle_client_connection(client_info, send, recv)
            client_sock.close()
    except KeyboardInterrupt:
        print("\nStopping Server.")
    finally:
        server_sock.close()
    return True

def run_serial_server(config):
    if not SERIAL_SUPPORT:
        print("\nError: 'pyserial' is not installed. Serial mode is required for macOS / virtual COM setups.")
        print("Install it with: pip install pyserial")
        return False
        
    print("\nAvailable Serial Ports:")
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No active serial/COM ports found. Please pair the phone via Bluetooth first.")
        print("Then check 'Bluetooth Settings -> Advanced -> Serial Ports' to bind an incoming COM port.")
        return False
        
    for i, p in enumerate(ports):
        print(f" [{i}] {p.device} - {p.description}")
        
    try:
        choice = input("\nSelect COM Port index [default: 0]: ").strip()
        idx = int(choice) if choice else 0
        selected_port = ports[idx].device
    except Exception:
        selected_port = ports[0].device
        
    print(f"Opening serial port {selected_port} at 115200 baud...")
    try:
        ser = serial.Serial(selected_port, 115200, timeout=1)
        print("Serial port opened successfully. Listening for RFCOMM/SPP data...")
    except Exception as e:
        print(f"Failed to open port: {e}")
        return False

    try:
        while True:
            # Serial helper block
            def send(data):
                ser.write(data)
                ser.flush()
                
            def recv():
                # Read until data is available
                while ser.in_waiting == 0:
                    time.sleep(0.05)
                return ser.read(ser.in_waiting)
                
            print("\nWaiting for incoming data stream on serial...")
            handle_client_connection(selected_port, send, recv)
    except KeyboardInterrupt:
        print("\nClosing Serial Port.")
    finally:
        ser.close()
    return True

def run_setup_wizard():
    print("\n" + "="*60)
    print("             BlueAI LAPTOP SERVER SETUP WIZARD            ")
    print("="*60)
    config = load_config()
    
    # 1. MAC Address
    detected_mac = get_local_mac_address()
    print(f"Detected Laptop MAC Address: {detected_mac or 'None'}")
    mac_in = input(f"Enter Laptop Bluetooth MAC address [default: {detected_mac or config['mac_address']}]: ").strip()
    if mac_in:
        config["mac_address"] = mac_in
    elif detected_mac:
        config["mac_address"] = detected_mac
        
    # 2. Select Backend
    print("\nChoose your LLM Backend:")
    print(" [1] Ollama (Local, fully offline) [Default]")
    print(" [2] LM Studio / llama-server (Local OpenAI compatible)")
    print(" [3] OpenAI (Cloud, requires API key)")
    print(" [4] Anthropic Claude (Cloud, requires API key)")
    be_choice = input("Enter option [1-4]: ").strip()
    
    if be_choice == "1":
        config["backend"] = "ollama"
        config["model"] = input(f"Ollama Model Name [default: {config['model']}]: ").strip() or config["model"]
    elif be_choice == "2":
        config["backend"] = "lm_studio"
        config["model"] = input("LM Studio / Llama Model Identifier (e.g. meta-llama-3): ").strip() or "local-model"
        config["lm_studio_url"] = input(f"LM Studio API URL [default: {config['lm_studio_url']}]: ").strip() or config["lm_studio_url"]
    elif be_choice == "3":
        config["backend"] = "openai"
        config["model"] = input("OpenAI Model (e.g. gpt-4o, gpt-3.5-turbo): ").strip() or "gpt-4o"
        config["openai_api_key"] = input("Enter OpenAI API Key: ").strip()
    elif be_choice == "4":
        config["backend"] = "anthropic"
        config["model"] = input("Anthropic Model (e.g. claude-3-5-sonnet-20240620): ").strip() or "claude-3-5-sonnet-20240620"
        config["anthropic_api_key"] = input("Enter Anthropic API Key: ").strip()
        
    save_config(config)
    print("\nSetup Wizard Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    global_config = load_config()
    
    # Check if user wants setup
    if len(sys.argv) > 1 and sys.argv[1] in ("--setup", "-s", "setup"):
        run_setup_wizard()
        global_config = load_config()
        
    print("BlueAI Bluetooth Bridge Server - Active")
    print(f"Backend: {global_config['backend'].upper()}  Model: {global_config['model']}")
    
    # Check MAC config
    if not global_config["mac_address"]:
        detected = get_local_mac_address()
        if detected:
            global_config["mac_address"] = detected
            save_config(global_config)
            
    # Show QR pairing code
    generate_qr_code(global_config["mac_address"], global_config["bluetooth_uuid"])
    
    # Main loop options
    print("Choose Server communication mode:")
    print(" [1] Native Bluetooth RFCOMM Socket (Windows & Linux) [Default]")
    print(" [2] Serial / COM Emulation (macOS & Virtual COM settings)")
    mode_in = input("Select mode [1 or 2]: ").strip()
    
    if mode_in == "2":
        run_serial_server(global_config)
    else:
        success = run_bluetooth_socket_server(global_config)
        if not success:
            print("\nNative socket server failed. Attempting to switch to Serial/COM mode...")
            run_serial_server(global_config)
