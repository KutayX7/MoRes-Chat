import threading
import queue

_event_queue: queue.SimpleQueue[tuple[str, tuple, dict]] = queue.SimpleQueue()
_event_bindings: dict[str, queue.SimpleQueue[threading.Event]] = dict()
_threading_event_args: dict[threading.Event, tuple[tuple, dict]] = dict()
_to_unbind_thread_events: list[threading.Event] = []

class EventConnection:
    def __init__(self, event_name: str, callable, once: bool):
        self._connected = True
        self._thread_event = threading.Event()
        binding_queue = _event_bindings.setdefault(event_name, queue.SimpleQueue())
        def job():
            while True:
                if not self._connected:
                    break
                self._thread_event.wait()
                self._thread_event.clear()
                if not self._connected:
                    break
                args, kwargs = _threading_event_args.pop(self._thread_event)
                if once:
                    self.disconnect()
                callable(event_name, *args, **kwargs)
        self._thread = threading.Thread(None, job)
        self._thread.daemon = True
        self._thread.start()
        binding_queue.put(self._thread_event)
    def is_connected(self):
        return self._connected
    def disconnect(self):
        if not self._connected:
            raise Exception('Can not disconnect twice')
        self._connected = False
        _to_unbind_thread_events.append(self._thread_event)
        self._thread = None
        self._thread_event = None


def push_event(event: str, *args, **kwargs):
    _event_queue.put((event, args, kwargs))

def on_event(event: str, callable):
    connection = EventConnection(event, callable, False)
    return connection

def on_event_once(event: str, callable):
    connection = EventConnection(event, callable, True)
    return connection

def wait_event(event: str) -> tuple[str, *tuple[object, ...], dict]|tuple[str, *tuple[object, ...]]|str:
    thread_event = threading.Event()
    args_dict = dict()
    def callback(event_name, *args, **kwargs):
        args_dict['event'] = event_name
        args_dict['args'] = args
        args_dict['kwargs'] = kwargs
        thread_event.set()
    on_event_once(event, callback)
    thread_event.wait()
    if len(args_dict['kwargs']) > 0:
        return (args_dict['event'], *(args_dict['args']), args_dict['kwargs'])
    elif len(args_dict['args']) > 0:
        return (args_dict['event'], *(args_dict['args']))
    else:
        return args_dict['event']

if True:
    def dispatcher_work():
        while True:
            try:
                event, args, kwargs = _event_queue.get()
                if event in _event_bindings:
                    binding_queue = _event_bindings[event]
                    removed_bindings: list[threading.Event] = []
                    while True:
                        try:
                            binding = binding_queue.get_nowait()
                            removed_bindings.append(binding)
                            _threading_event_args[binding] = (args, kwargs)
                            binding.set()
                        except:
                            break
                    for binding in removed_bindings:
                        if binding in _to_unbind_thread_events:
                            _to_unbind_thread_events.remove(binding)
                        else:
                            binding_queue.put(binding)
            except Exception as e:
                print('Exception in thread dispatcher: ', e)

    dispatcher_thread = threading.Thread(None, dispatcher_work)
    dispatcher_thread.daemon = True
    dispatcher_thread.start()

