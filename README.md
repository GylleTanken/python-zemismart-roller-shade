# python-zemismart-roller-shade
A simple Python API for controlling Zemismart roller shade.

## Example use
This will connect to the roller shade with the mac address "00:11:22:33:44:55" and the pin 8888, and open the shade. It will try for 40 seconds to connect to the device. This automaticly sends the pin code. It will automaticly disconnect when the 'with' block is endning
```
import Zemismart

shade = Zemismart.Zemismart("00:11:22:33:44:55", 8888, max_connect_time=40)
with shade:
    shade.open()
```

This will begin to close the shade and stop it after 2 seconds (requires that time module is imported).
```
with shade:
    shade.close()
    time.sleep(2)
    shade.stop()
```

This will stop the shade.
```
with shade:
    shade.stop()
```

This will set the shade to 80% closed.
```
with shade:
    shade.set_position(80)
```

This will get the current battery level and position.
This is not working correctly yet. (Sometimes needs to be called multiple times)   
```
with shade:
    shade.update()
```
This will get the updated values.

```
pos = shade.position
bat = shade.battery
```

### Threading
If multiple threads will access the same object, mutexes should be enabled as below
```
shade = Zemismart.Zemismart("00:11:22:33:44:55", 8888, withMutex=True)
```

## Zemismart Protocol
The host application communicates with the Zemismart device (in both directions) via the BLE handle with the UUID 0xfe51.

### Packet format

| Field            | Length (Bytes) | Value/description    |
|------------------|----------------|----------------------|
| `Start sequence` | 5              | 0x00ff00009a         |
| `Command ID`     | 1              | See below            |
| `Length`         | 1              | Length of `Data`     |
| `Data`           | `Length`       | Data for the command |
| `Checksum`       | 1              | See below            |

All multi byte fields are send as big endian. (MSB first)

### Checksum

The `Checksum` field in the packet is calculated by computing the XOR of all the other bytes in the packet (`Start sequence`, `Command ID`, `Length` and `Data`) and XOR-ing the result with 0xFF, to ensure odd paraity. 

See https://en.wikipedia.org/wiki/Checksum#Parity_byte_or_parity_word


### Commands


#### `pin_cmd` (0x17)

`Command ID = 0x17`

This command must be used to provide the pin code to allow any other command.

| Data Field     | Length (Bytes) | Value/description    |
|------------------|----------------|----------------------|
| pin            | 2              | The 4 digit pin code as an unsigned interger         |

#### `move_cmd` (0x0a)

`Command ID = 0x0a`

This command is used to, open, close or stop the shade.

| Data Field     | Length (Bytes) | Value/description    |
|----------------|----------------|----------------------|
| Instruction    | 1              | 0xdd: Open shade <br /> 0xee: Close shade  <br /> 0xcc: Stop shade |


#### `set_position_cmd` (0x0d)

`Command ID = 0x0d`

This command is used to set the shade to a specific position (percentage)

| Data Field     | Length (Bytes) | Value/description    |
|----------------|----------------|----------------------|
| Posiiton    | 1              | Unsigned integer between 0 and 100 |

#### `get_position_cmd` (0xa7)

`Command ID = 0xa7`

This command is used to get the current battery status of the device

| Data Field            | Length (Bytes) | Value/description    |
|-----------------------|----------------|----------------------|
| *No suitable name*    | 1              | 0x01                 |

#### `get_battery_cmd` (0xa2)

`Command ID = 0xa2`

This command is used to get the current battery status of the device

| Data Field            | Length (Bytes) | Value/description    |
|-----------------------|----------------|----------------------|
| *No suitable name*    | 1              | 0x01                 |
                                 



