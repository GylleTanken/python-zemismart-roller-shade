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



