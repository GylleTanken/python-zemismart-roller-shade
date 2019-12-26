# Python module for control of Zemismart Roller Shade
#
#

from bluepy import btle
import struct
import time

#class Delegate(btle.DefaultDelegate):
#    def __init__(self, zemismart):
#        self.zemismart = zemismart
#        btle.DefaultDelegate.__init__(self)
#
#    def handleNotification(self, handle, data):
#        print("Got data: " + str(data))
#        print("Got handle: " + str(handle))
#        if handle == self.zemismart.datahandle.getHandle() and data[0] == self.zemismart.response_start_byte:
#            print("Got cmd: " + str(data[1]))
#            if data[1] == self.zemismart.get_battery_cmd[0]:
#                battery = data[7]
#                print("Got battery: " + str(battery))
#                self.zemismart.save_battery(battery)
#            elif data[1] == self.zemismart.get_position_cmd[0]:
#                pos = data[5]
#                print("Got posisition: " + str(pos))
#                self.zemismart.save_position(pos)
#            elif data[1] == self.zemismart.finished_moving_cmd[0]:
#                pos = data[4]
#                print("Finished moving to position: " + str(pos))
#                self.zemismart.save_position(pos)






class Zemismart(btle.DefaultDelegate):
    
    datahandle_uuid = "fe51"

    response_start_byte = 0x9a

    start_bytes = bytearray.fromhex('00ff00009a')

    pin_cmd = bytearray.fromhex('17')
    move_cmd = bytearray.fromhex('0a')
    position_cmd = bytearray.fromhex('0d')

    get_battery_cmd = bytearray.fromhex('a2')
    get_position_cmd = bytearray.fromhex('a7')
    finished_moving_cmd = bytearray.fromhex('a1')

    open_data = bytearray.fromhex('dd')
    close_data = bytearray.fromhex('ee')
    stop_data = bytearray.fromhex('cc')

    def __init__(self, mac="02:4E:F0:E8:7F:63", pin=8888):
        self.mac = mac
        self.pin = pin
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, handle, data):
        print("Got data: " + str(data))
        print("Got handle: " + str(handle))
        if handle == self.datahandle.getHandle() and data[0] == self.response_start_byte:
            print("Got cmd: " + str(data[1]))
            if data[1] == self.get_battery_cmd[0]:
                battery = data[7]
                print("Got battery: " + str(battery))
                self.save_battery(battery)
            elif data[1] == self.get_position_cmd[0]:
                pos = data[5]
                print("Got posisition: " + str(pos))
                self.save_position(pos)
            elif data[1] == self.finished_moving_cmd[0]:
                pos = data[4]
                print("Finished moving to position: " + str(pos))
                self.save_position(pos)
    
    def connect(self):
        self.device = btle.Peripheral(self.mac, addrType=btle.ADDR_TYPE_PUBLIC)
        self.device.withDelegate(self)
        handles = self.device.getCharacteristics()
        for handle in handles:
            if handle.uuid == self.datahandle_uuid:
                self.datahandle = handle
        self.login()

    def login(self):
       pin_data = bytearray(struct.pack(">H", self.pin))
       self.send_Zemismart_packet(self.pin_cmd, pin_data)
#       self.send_packet(self.datahandle, bytearray([0x00, 0xff, 0x00, 0x00, 0x9a, 0x17, 0x02, 0x22, 0xb8, 0x15]))

    def send_BLE_packet(self, handle, data):
        return handle.write(bytes(data), withResponse=False)

    def send_Zemismart_packet(self, command, data):
        lenght = bytearray([len(data)])
        data_without_checksum = self.start_bytes + command + lenght + data
        data_with_checksum = data_without_checksum + self.calculate_checksum(data_without_checksum)
        print(data_with_checksum)
        return self.send_BLE_packet(self.datahandle, data_with_checksum)

    def calculate_checksum(self, data):
        checksum = 0
        for byte in data:
            checksum = checksum ^ byte
        checksum = checksum ^ 0xff
        print(checksum)
        return bytearray([checksum])

    def open(self):
        self.send_Zemismart_packet(self.move_cmd, self.open_data)

    def close(self):
        self.send_Zemismart_packet(self.move_cmd, self.close_data)

    def stop(self):
        self.send_Zemismart_packet(self.move_cmd, self.stop_data)

    def set_position(self, position):
        if position >= 0 and position <= 100:
            self.send_Zemismart_packet(self.position_cmd, bytearray(struct.pack(">B", position)))

    def save_position(self, position):
        self.position = position

    def save_battery(self, battery):
        self.battery = battery

    def update(self):
        self.send_Zemismart_packet(self.get_position_cmd, bytearray([0x01]))
        self.send_Zemismart_packet(self.get_battery_cmd, bytearray([0x01]))
        self.device.waitForNotifications(1.0)

