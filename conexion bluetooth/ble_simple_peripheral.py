import bluetooth
import struct

_ADV_TYPE_FLAGS = 0x01
_ADV_TYPE_NAME = 0x09
_ADV_TYPE_UUID16_COMPLETE = 0x03
_ADV_TYPE_UUID32_COMPLETE = 0x05
_ADV_TYPE_UUID128_COMPLETE = 0x07

_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3

class BLESimplePeripheral:
    def __init__(self, ble, name="Cortina_ESP32"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle_tx, self._handle_rx),) = self._ble.gatts_register_services((
            (bluetooth.UUID(0xFFF0), ((bluetooth.UUID(0xFFF1), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY), (bluetooth.UUID(0xFFF2), bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE),),),
        ))
        self._connections = set()
        self._write_callback = None
        self._payload = self._advertising_payload(name=name, services=[bluetooth.UUID(0xFFF0)])
        self._advertise()

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.remove(conn_handle)
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if conn_handle in self._connections and value_handle == self._handle_rx:
                if self._write_callback:
                    self._write_callback(self._ble.gatts_read(self._handle_rx))

    def on_write(self, callback):
        self._write_callback = callback

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)

    def _advertising_payload(self, limited_disc=False, br_edr=False, name=None, services=None):
        payload = bytearray()
        def _append(adv_type, value):
            nonlocal payload
            payload.append(len(value) + 1)
            payload.append(adv_type)
            payload.extend(value)
        _append(_ADV_TYPE_FLAGS, struct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)))
        if name: _append(_ADV_TYPE_NAME, name)
        if services:
            for s in services:
                b = bytes(s)
                if len(b) == 2: _append(_ADV_TYPE_UUID16_COMPLETE, b)
                elif len(b) == 4: _append(_ADV_TYPE_UUID32_COMPLETE, b)
                elif len(b) == 16: _append(_ADV_TYPE_UUID128_COMPLETE, b)
        return payload