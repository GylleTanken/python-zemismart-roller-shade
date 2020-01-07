# Python module for control of Zemismart Roller Shade
#
#

from bluepy import btle
import struct
import time


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

    def __init__(self, mac="02:4E:F0:E8:7F:63", pin=8888, max_connect_time=30):
        self.mac = mac
        self.pin = pin
        self.max_connect_time = max_connect_time
        self.device = None
        self.datahandle = None
        self.battery = 0
        self.position = 0
        btle.DefaultDelegate.__init__(self)



    def __enter__(self):

        self.device = btle.Peripheral()
        self.device.withDelegate(self)

        start_time = time.time()
        connection_try_count = 0

        while True:
            connection_try_count += 1
            if connection_try_count > 1:
                print("Retrying to connect to device with mac: " + self.mac + ", try number: " + str(connection_try_count))
            try:
                self.device.connect(self.mac, addrType=btle.ADDR_TYPE_PUBLIC)
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

        if self.datahandle == None:
            self.device = None
            raise Exception("Unable to find all handles")

        self.login()

        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.device:
            self.device.disconnect()
            self.device = None



    def handleNotification(self, handle, data):
        if handle == self.datahandle.getHandle() and data[0] == self.response_start_byte:
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
    

    def login(self):
       pin_data = bytearray(struct.pack(">H", self.pin))
       self.send_Zemismart_packet(self.pin_cmd, pin_data)

    def send_BLE_packet(self, handle, data, wait_for_notification_time=0):
        write_response = handle.write(bytes(data), withResponse=False)
        if wait_for_notification_time > 0:
            self.device.waitForNotifications(wait_for_notification_time)
        return write_response

    def send_Zemismart_packet(self, command, data, wait_for_notification_time=0):
        lenght = bytearray([len(data)])
        data_without_checksum = self.start_bytes + command + lenght + data
        data_with_checksum = data_without_checksum + self.calculate_checksum(data_without_checksum)
        if self.datahandle is None or self.device is None:
            print("datahandle or device is not defined. Did you use with statement?")
            return False
        else:
            return self.send_BLE_packet(self.datahandle, data_with_checksum, wait_for_notification_time)

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

    def set_position(self, position):
        if position >= 0 and position <= 100:
            return self.send_Zemismart_packet(self.position_cmd, bytearray(struct.pack(">B", position)))

    def save_position(self, position):
        self.position = position

    def save_battery(self, battery):
        self.battery = battery

    def update(self): 
        if self.send_Zemismart_packet(self.get_position_cmd, bytearray([0x01])) == False:
            return False
        elif self.send_Zemismart_packet(self.get_battery_cmd, bytearray([0x01]), 2) == False:
            return False
        else:
            return True

