# Python module for control of Zemismart Roller Shade
#
#

import struct
import threading
import time
import datetime

from bluepy import btle


class Zemismart(btle.DefaultDelegate):
    datahandle_uuid = "fe51"

    response_start_byte = 0x9a

    start_bytes = bytearray.fromhex('00ff00009a')

    pin_cmd = bytearray.fromhex('17')
    sync_time_cmd = bytearray.fromhex('14')
    move_cmd = bytearray.fromhex('0a')
    set_position_cmd = bytearray.fromhex('0d')

    get_battery_cmd = bytearray.fromhex('a2')
    get_position_cmd = bytearray.fromhex('a7')
    finished_moving_cmd = bytearray.fromhex('a1')

    notify_position_cmd = bytearray.fromhex('41')

    open_data = bytearray.fromhex('dd')
    close_data = bytearray.fromhex('ee')
    stop_data = bytearray.fromhex('cc')

    def __init__(self, mac="02:4E:F0:E8:7F:63", pin=8888, max_connect_time=30, withMutex=False, iface=None):
        self.mac = mac
        self.pin = pin
        self.max_connect_time = max_connect_time
        self.device = None
        self.datahandle = None
        self.battery = 0
        self.position = 0
        self.withMutex = withMutex
        self.last_command_status = None
        self.iface = iface
        if self.withMutex:
            self.mutex = threading.Lock()
        btle.DefaultDelegate.__init__(self)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.disconnect()

    def disconnect(self):
        try:
            if self.device:
                self.device.disconnect()
                self.device = None
        except Exception as ex:
            print("Could not disconnect with mac: " + self.mac + ", Error: " + str(ex))
        finally:
            if self.withMutex:
                self.mutex.release()

    def connect(self):
        if self.withMutex:
            self.mutex.acquire()

        try:
            self.device = btle.Peripheral()
            self.device.withDelegate(self)

            start_time = time.time()
            connection_try_count = 0

            while True:
                connection_try_count += 1
                if connection_try_count > 1:
                    print("Retrying to connect to device with mac: " +
                          self.mac + ", try number: " + str(connection_try_count))
                try:
                    self.device.connect(self.mac, addrType=btle.ADDR_TYPE_PUBLIC, iface=self.iface)
                    break
                except btle.BTLEException as ex:
                    print("Could not connect to device with mac: " + self.mac + ", error: " + str(ex))
                    if time.time() - start_time >= self.max_connect_time:
                        print("Connection timeout")
                        raise

            handles = self.device.getCharacteristics()
            for handle in handles:
                if handle.uuid == self.datahandle_uuid:
                    self.datahandle = handle

            if self.datahandle is None:
                self.device = None
                raise Exception("Unable to find all handles")

            self.login()
        except:
            self.disconnect()
            raise

    def handleNotification(self, handle, data):
        if handle == self.datahandle.getHandle() and data[0] == self.response_start_byte:
            if data[1] == self.get_battery_cmd[0]:
                battery = data[7]
                self.save_battery(battery)
                self.last_command_status = True
            elif data[1] == self.get_position_cmd[0]:
                pos = data[5]
                self.save_position(pos)
                self.last_command_status = True
            elif data[1] in (self.finished_moving_cmd[0], self.notify_position_cmd[0]):
                pos = data[4]
                self.save_position(pos)
                self.last_command_status = True
            elif data[1] in (self.set_position_cmd[0], self.pin_cmd[0], self.move_cmd[0], self.sync_time_cmd[0]):
                if data[3] == 0x5A:
                    self.last_command_status = True
                elif data[3] == 0xA5:
                    self.last_command_status = False

    def login(self):
        pin_data = bytearray(struct.pack(">H", self.pin))
        self.send_Zemismart_packet(self.pin_cmd, pin_data)

    def send_BLE_packet(self, handle, data):
        return handle.write(bytes(data), withResponse=False)

    def send_Zemismart_packet(self, command, data, wait_for_notification_time=2):
        self.last_command_status = None
        length = bytearray([len(data)])
        data_without_checksum = self.start_bytes + command + length + data
        data_with_checksum = data_without_checksum + self.calculate_checksum(data_without_checksum)
        if self.datahandle is None or self.device is None:
            print("datahandle or device is not defined. Did you use with statement?")
            return False
        else:
            write_result = self.send_BLE_packet(self.datahandle, data_with_checksum)
            if wait_for_notification_time > 0:
                start_time = time.time()
                while self.last_command_status is None and time.time() - wait_for_notification_time <= start_time:
                    if self.device.waitForNotifications(wait_for_notification_time) and self.last_command_status is not None:
                        return self.last_command_status is True
                return False
            return write_result

    def calculate_checksum(self, data):
        checksum = 0
        for byte in data:
            checksum = checksum ^ byte
        checksum = checksum ^ 0xff
        return bytearray([checksum])

    def open(self):
        return self.send_Zemismart_packet(self.move_cmd, self.open_data)

    def close(self):
        return self.send_Zemismart_packet(self.move_cmd, self.close_data)

    def stop(self):
        return self.send_Zemismart_packet(self.move_cmd, self.stop_data)

    def sync_time(self, tz=None):
        now = datetime.datetime.now(tz)
        data = bytearray()
        # DoW is expected to be an in between 0 and 6, where 0 is Sunday and 6 is Saturday
        data.append(int(now.strftime('%w')))
        data.append(now.hour)
        data.append(now.minute)
        data.append(now.second)
        return self.send_Zemismart_packet(self.move_cmd, data)

    def set_position(self, position):
        if 0 <= position <= 100:
            return self.send_Zemismart_packet(self.set_position_cmd, bytearray(struct.pack(">B", position)))

    def save_position(self, position):
        self.position = position

    def save_battery(self, battery):
        self.battery = battery

    def update(self):
        if not self.send_Zemismart_packet(self.get_position_cmd, bytearray([0x01]), 1):
            return False
        elif not self.send_Zemismart_packet(self.get_battery_cmd, bytearray([0x01]), 1):
            return False
        else:
            return True
