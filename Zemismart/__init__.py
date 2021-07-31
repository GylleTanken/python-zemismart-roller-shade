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
    get_status_cmd = bytearray.fromhex('a7')
    finished_moving_cmd = bytearray.fromhex('a1')
    update_timer_cmd = bytearray.fromhex('15')

    get_timers_cmd = bytearray.fromhex('a8')
    unknown_cmd_a9 = bytearray.fromhex('a9')

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
        self.timers = []
        self._get_status_responses = set()
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
            elif data[1] == self.get_status_cmd[0]:
                pos = data[5]
                self.save_position(pos)
                self._get_status_responses.add(data[1])
                self._check_full_status_received()
            elif data[1] == self.finished_moving_cmd[0]:
                pos = data[4]
                self.save_position(pos)
                self.last_command_status = True
            elif data[1] == self.unknown_cmd_a9[0]:
                self._get_status_responses.add(data[1])
                self._check_full_status_received()
            elif data[1] == self.get_timers_cmd[0]:
                self._get_status_responses.add(data[1])
                self.timers = Timer.from_raw_data(self, data)
                self._check_full_status_received()
            elif data[1] in (self.set_position_cmd[0], self.pin_cmd[0], self.move_cmd[0], self.update_timer_cmd[0], self.sync_time_cmd[0]):
                # It's very likely that this byte is incorrectly interpreted: 0xA5 is sent in response to successfull timer deletion
                if data[3] == 0x5A or (data[3] == 0xA5 and data[1] == self.update_timer_cmd[0]):
                    self.last_command_status = True
                elif data[3] == 0xA5:
                    self.last_command_status = False

    def _check_full_status_received(self):
        """
        Command 0xA7 (get_status) yields three responses from the device. We can't treat the command result as
        a success, unless we have received all of them.
        This method checks that since the last update() call, where self._get_status_responses is reset, we
        received all the required responses.
        """
        if self._get_status_responses.issuperset({self.get_status_cmd[0], self.get_timers_cmd[0], self.unknown_cmd_a9[0]}):
            self.last_command_status = True

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
        self._get_status_responses.clear()
        if not self.send_Zemismart_packet(self.get_status_cmd, bytearray([0x01]), 1):
            return False
        elif not self.send_Zemismart_packet(self.get_battery_cmd, bytearray([0x01]), 1):
            return False
        else:
            return True


class Timer:
    REPEAT_SUNDAY = 0x01
    REPEAT_MONDAY = 0x02
    REPEAT_TUESDAY = 0x04
    REPEAT_WEDNESDAY = 0x08
    REPEAT_THURSDAY = 0x10
    REPEAT_FRIDAY = 0x20
    REPEAT_SATURDAY = 0x40

    REPEAT_EVERY_DAY = REPEAT_SUNDAY | REPEAT_MONDAY | REPEAT_TUESDAY | REPEAT_WEDNESDAY | REPEAT_THURSDAY \
        | REPEAT_FRIDAY | REPEAT_SATURDAY

    @classmethod
    def from_raw_data(cls, device, data):
        ret = []

        # Single timer takes 5 bytes
        for timer_id in range(0, int(int(data[2]) / 5)):
            timer_data_start = 3 + timer_id * 5
            hours = int(data[timer_data_start + 3])
            if hours > 0:
                # I'm extremely unsure about this, but my devices report 00 for midnight,
                # 02 for 1AM, 09 for 8am and so on.
                hours -= 1
            ret.append(cls(
                bool(data[timer_data_start]),
                int(data[timer_data_start + 1]),
                int(data[timer_data_start + 2]),
                hours,
                int(data[timer_data_start + 4]),
                timer_id,
                device
            ))

        return ret

    def __init__(self, enabled, target_position, repeats, hours, minutes, timer_id=None, device=None):
        """
        Parameters:
            enabled (bool): defines whether the timer is enabled or not
            target_position (int): desired shares target position
            repeats (int): day when the timer should be repeated (use `binary or` to create desired combination,
                            e.g. `Zemismart.Timer.REPEAT_SUNDAY | Zemismart.Timer.REPEAT_FRIDAY`)
            hours (int): hour when the timer should trigger
            minutes (int): minute when the timer should trigger
        """
        if type(enabled) is not bool:
            raise AttributeError('`enabled` must be bool')
        self._enabled = enabled

        if type(target_position) is not int or not (0 <= target_position <= 100):
            raise AttributeError('`target_position` must be integer between 0 and 100')
        self._target_position = target_position

        if type(repeats) is not int or repeats > self.REPEAT_EVERY_DAY:
            raise AttributeError('`repeats` must be integer less than %d' % self.REPEAT_EVERY_DAY)
        self._repeats = repeats

        if type(hours) is not int or not (0 <= hours <= 23):
            raise AttributeError('`hours` must be integer between 0 and 23')
        self._hours = hours

        if type(minutes) is not int or not (0 <= minutes <= 59):
            raise AttributeError('`minutes` must be integer between 0 and 59')
        self._minutes = minutes

        self._timer_id = timer_id
        self._device = device

    def _verify_timer_can_be_saved(self, device):
        if not device and not self._device:
            raise AttributeError('Can\'t save timer before assigning it to a device')

    @classmethod
    def _update_timer(cls, device, timer_id, is_enabled=False, target_position=0, repeats=0, hours=0, minutes=0, action=0):
        """
        Sends the update command to the AM43 device. There're two known actions: `0` is update and `1` is delete.
        """
        return device.send_Zemismart_packet(device.update_timer_cmd,
                                            bytearray([timer_id + 1, action, int(is_enabled), target_position,
                                                       repeats,
                                                       hours if hours == 0 else hours + 1,
                                                       minutes]),
                                            1)

    def _select_device(self, device):
        """
        Returns the device provided as a method argument, if any, and self._device otherwise.
        """
        if device:
            return device
        return self._device

    def remove(self):
        if self._timer_id is None:
            raise ValueError('Unable to remove timer that wasn\'t assigned to a device')

        self._verify_timer_can_be_saved(None)

        if self._timer_id >= len(self._device.timers):
            raise ValueError('Trying to remove unknown timer')

        ret = self._update_timer(self._device, self._timer_id, action=1)

        if ret:
            del self._device.timers[self._timer_id]

            timer_id = 0
            for timer in self._device.timers:
                timer._timer_id = timer_id
                timer_id += 1

            self._device = None
            self._timer_id = None

        return ret

    def save(self, device=None):
        self._verify_timer_can_be_saved(device)
        if len(self._select_device(device).timers) >= 4:
            raise ValueError('You can have only 4 timers')

        timer_id = self._timer_id

        if device is not None:
            timer_id = len(device.timers)
        elif timer_id is None:
            timer_id = len(self._device.timers)
        elif timer_id >= len(self._device.timers):
            raise ValueError('Trying to update unknown timer')

        ret = self._update_timer(self._select_device(device), timer_id, self._enabled, self._target_position,
                                 self._repeats, self._hours, self._minutes)

        if ret:
            self._device = self._select_device(device)
            self._timer_id = timer_id

            if len(self._device.timers) - 1 >= timer_id:
                self._device.timers[timer_id] = self
            else:
                self._device.timers.append(self)

        return ret

    def _update_if_assigned(self):
        if self._device and self._timer_id:
            return self.save()
        return None

    def disable(self):
        self._enabled = False
        return self._update_if_assigned()

    def enable(self):
        self._enabled = True
        return self._update_if_assigned()

    def set_repeats(self, repeats):
        self._repeats = repeats
        return self._update_if_assigned()

    def set_time(self, hours, minutes):
        if not 0 <= hours <= 23:
            raise ValueError('The value must be between 0 and 23')

        if not 0 <= minutes <= 59:
            raise ValueError('The value must be between 0 and 59')

        self._minutes = minutes
        self._hours = hours

        return self._update_if_assigned()

    def __repr__(self):
        ret = ''

        if self._device is None:
            ret += 'Unassigned'
        else:
            ret += 'Assigned'

        ret += ' '

        if self._enabled:
            ret += 'active'
        else:
            ret += 'inactive'

        ret += ' timer'

        if self._timer_id is None:
            ret += ' w/o id'
        else:
            ret += '#%d' % self._timer_id

        ret += ': set to %s%% at %02d:%02d ' % (self._target_position, self._hours, self._minutes)

        if self._repeats:
            ret += 'on '
            repeats = []
            if self._repeats == self.REPEAT_EVERY_DAY:
                repeats.append('everyday')
            else:
                if self._repeats & self.REPEAT_MONDAY:
                    repeats.append('Monday')
                if self._repeats & self.REPEAT_TUESDAY:
                    repeats.append('Tuesday')
                if self._repeats & self.REPEAT_WEDNESDAY:
                    repeats.append('Wednesday')
                if self._repeats & self.REPEAT_THURSDAY:
                    repeats.append('Thursday')
                if self._repeats & self.REPEAT_FRIDAY:
                    repeats.append('Friday')
                if self._repeats & self.REPEAT_SATURDAY:
                    repeats.append('Saturday')
                if self._repeats & self.REPEAT_SUNDAY:
                    repeats.append('Sunday')

            ret += ' + '.join(repeats)
        else:
            ret += 'NEVER REPEAT'

        return ret
