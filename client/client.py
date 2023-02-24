from time import monotonic, strftime, gmtime, time
from crypter import code, RSA
from random import randbytes
import socket

timestamp = lambda: strftime("%d.%m.%y %H:%M:%S", gmtime(time()))
calculate_time = lambda x: round((monotonic() - x) * 1000, 2)
bytes_to_int = lambda x: int.from_bytes(x, "big")

class Log:
    class LogType:
        @property
        def INFO():
            return '\033[36minfo\033[0m'

        @property
        def WARN():
            return '\033[33mwarn\033[0m'

        @property
        def ERROR():
            return '\033[31merrn\033[0m'

    def __call__(self, type: LogType, message: str, time: float = 0.0) -> None:
        print(f"{timestamp()}: {time} ms : [{type.fget()}] : {message}")

    def LogDecorator(self, func) -> None:
        def wrapper(*args, **kwargs) -> None:
            self(self.LogType.INFO, f"Calling function '{func.__name__}' with args {args, kwargs}")
            try:
                runtime = monotonic()
                result = func(*args, **kwargs)
                self(self.LogType.INFO, f"End function {func.__name__}", calculate_time(runtime))
                return result
            except Exception as error:
                self(self.LogType.WARN, error)
        return wrapper

log = Log()

class PacketManager:
    @log.LogDecorator
    def keys_packet(rsa: RSA) -> bytes:
        data: bytes = (
            rsa._data['pubkey'][0].to_bytes(32, "big") + 
            rsa._data['pubkey'][1].to_bytes(32, "big")
            )
        zerosize = 1022 - data.__len__()
        return zerosize.to_bytes(2, "big") + data + randbytes(zerosize)

    def fetch_pubkey_keys(keys: bytes) -> tuple[int, int]:
        zerosize = 1024 - bytes_to_int(keys[:2])
        data = keys[2:zerosize]
        keys = (bytes_to_int(data[:32]), bytes_to_int(data[32:64]))
        log(log.LogType.INFO, f"Public key fetched! pubkey: {keys}")
        return keys

    @log.LogDecorator
    def encode_packet(message: str, rsa: RSA) -> bytes:
        payload = rsa.encode(code(message), rsa._data['_pubkey'])
        zerosiez = 1022 - payload.__len__()
        return zerosiez.to_bytes(2, "big") + payload + randbytes(zerosiez)
    
    def decode_packet(message: str, rsa: RSA) -> bytes:
        zerosize = 1024 - int.from_bytes(message[:2], "big")
        return code(rsa.decode(message[2:zerosize], rsa._data['privkey']))

class Client:
    @log.LogDecorator
    def __init__(self, addr: tuple[str, int]) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rsa = RSA(key_length = 32)
        self.addr = addr

    @log.LogDecorator
    def start(self) -> bool:
        log(log.LogType.INFO, "Generating keys...")
        self.rsa.generate()
        log(log.LogType.INFO, "Keys generated!")

        log(log.LogType.INFO, "Connectin to server...")
        if not self._connect(): return False
        log(log.LogType.INFO, "Connected!")
        return True

    @log.LogDecorator
    def _connect(self) -> bool:
        try:
            self.socket.connect(self.addr)
            keys = self.socket.recv(1024)
            self.rsa._data['_pubkey'] = PacketManager.fetch_pubkey_keys(keys)
            self.socket.sendall(PacketManager.keys_packet(self.rsa))
            return True
        except Exception as error:
            log(log.LogType.ERROR, error)

    @log.LogDecorator
    def disconnect(self) -> None:
        self.socket.close()

    @log.LogDecorator
    def send(self, message: str) -> bool:
        try:
            encoded = PacketManager.encode_packet(message, self.rsa)
            self.socket.sendall(encoded)
            return True
        except Exception as error:
            log(log.LogType.WARN, error)
            