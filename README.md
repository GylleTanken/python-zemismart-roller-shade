# python-zemismart-roller-shade
A simple Python API for controlling Zemismart roller shade.

## Example use
This will connect to the roller shade with the mac address "00:11:22:33:44:55" and the pin 8888, and open the shade. The connect method also sends the pin code to the device.
```
import Zemismart

shade = Zemismart.Zemismart("00:11:22:33:44:55", 8888)
shade.connect()
shade.open()
```

This will close the shade.
```
shade.close()
```

This will stop the shade.
```
shade.stop()
```

This will set the shade to 80% closed.
```
shade.set_position(80)
```

This will get the current battery level and position.
This is not working correctly yet. (Sometimes needs to be called multiple times)   
```
shade.update()
```
This will get the updated values.

```
pos = shade.position
bat = shade.battery
```



