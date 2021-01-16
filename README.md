# Process Pool

Wraps python's `pool` module to provide extra functionality.  Most importantly,
this pool allows you to buffer output to stdout.  

## Example

```python
import time
import random

import ppool

def _test_func(i):
    print(i)
    time.sleep(random.randint(0,3))
    print(i)
    time.sleep(random.randint(0,3))
    print(i)

print("Buffered, Threaded")
ppool.map(_test_func, range(5))

print("Buffered, Processes")
ppool.map(_test_func, range(5), threaded=False)

print("Non-buffered, Threaded")
ppool.map(_test_func, range(5), buffered=False)

print("Non-buffered, Processes")
ppool.map(_test_func, range(5), buffered=False, threaded=False)

print("Foreground")
ppool.map(_test_func, range(5), fg=True)
```
