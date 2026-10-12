"""Reject-only local USB/IP mock: checks client access without attaching hardware."""
import socket
import subprocess
import threading

listener = socket.socket()
listener.bind(('127.0.0.1', 0))
listener.listen()
listener.settimeout(8)
port = listener.getsockname()[1]
seen = []


def reject():
    try:
        connection, _ = listener.accept()
        with connection:
            seen.append(connection.recv(40))
            connection.sendall(bytes.fromhex('0111000300000001'))
    finally:
        listener.close()


threading.Thread(target=reject, daemon=True).start()
result = subprocess.run([r'C:\Program Files\USBip\usbip.exe', '--tcp-port', str(port),
                         'attach', '--once', '--remote', '127.0.0.1', '--bus-id', '1-1'],
                        capture_output=True, text=True, timeout=10)
assert seen, 'Native driver denied access before the USB/IP exchange: ' + result.stderr
assert result.returncode != 0, 'Mock import must fail; no virtual device should be attached'
print('PASS: normal-user native client reached the loopback reject-only mock; no hardware attached')
