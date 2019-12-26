# Python module for control of Zemismart Roller Shade
#
#

from bluepy import btle



class Zemismart:
    def __init__(self, mac):
        self.mac = mac
    
    def set_percentage(self, percentage):
        self.percentage = percentage

    def connect(self):
        self.device = btle.Peripheral(self.mac, addrType=btle.ADDR_TYPE_PUBLIC)