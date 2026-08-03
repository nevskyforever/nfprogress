"""Bridge custom help topics into the native macOS Help menu search."""

from __future__ import annotations

import ctypes
import platform
import threading
import warnings
from dataclasses import dataclass
from typing import Callable, Iterable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class HelpSearchItem:
    """A localized help topic prepared for both Qt and native search."""

    key: str
    display_path: tuple[str, ...]
    normalized_titles: tuple[str, ...]
    search_text: str

    @classmethod
    def create(
        cls,
        key: str,
        display_path: Iterable[str],
        titles: Iterable[str],
        text_parts: Iterable[str],
    ) -> "HelpSearchItem":
        return cls(
            key=key,
            display_path=tuple(display_path),
            normalized_titles=tuple(
                " ".join(title.casefold().split()) for title in titles
            ),
            search_text="\n".join(text_parts).casefold(),
        )


def help_search_match_ranks(
    items: Iterable[HelpSearchItem], query: str
) -> dict[str, int]:
    """Ranks title matches ahead of matches found only inside an article."""
    terms = [term for term in query.casefold().split() if term]
    if not terms:
        return {item.key: 0 for item in items}

    normalized_query = " ".join(terms)
    match_ranks = {}
    for item in items:
        titles = item.normalized_titles
        if normalized_query in titles:
            match_ranks[item.key] = 0
        elif any(title.startswith(normalized_query) for title in titles):
            match_ranks[item.key] = 1
        elif any(all(term in title for term in terms) for title in titles):
            match_ranks[item.key] = 2
        elif all(term in item.search_text for term in terms):
            match_ranks[item.key] = 3
    return match_ranks


def ranked_help_search_items(
    items: Iterable[HelpSearchItem], query: str, limit: int
) -> list[HelpSearchItem]:
    """Returns matching items in stable relevance order."""
    items = tuple(items)
    match_ranks = help_search_match_ranks(items, query)
    ranked_items = sorted(
        enumerate(items),
        key=lambda pair: (match_ranks.get(pair[1].key, 4), pair[0]),
    )
    return [
        item for _index, item in ranked_items
        if item.key in match_ranks
    ][:max(0, limit)]


_ID = ctypes.c_void_p
_SEL = ctypes.c_void_p
_SearchMethod = ctypes.CFUNCTYPE(
    None, _ID, _SEL, _ID, ctypes.c_long, _ID
)
_TitlesMethod = ctypes.CFUNCTYPE(_ID, _ID, _SEL, _ID)
_ActionMethod = ctypes.CFUNCTYPE(None, _ID, _SEL, _ID)


class _BlockLiteral(ctypes.Structure):
    _fields_ = (
        ("isa", _ID),
        ("flags", ctypes.c_int),
        ("reserved", ctypes.c_int),
        ("invoke", _ID),
        ("descriptor", _ID),
    )


_bridges_by_native_id: dict[int, "MacOSHelpSearch"] = {}
_bridges_lock = threading.RLock()
_objective_c_runtime = None
_objective_c_runtime_lock = threading.Lock()


def _bridge_for(native_self) -> "MacOSHelpSearch | None":
    with _bridges_lock:
        return _bridges_by_native_id.get(int(native_self or 0))


@_SearchMethod
def _search_for_items(
    native_self, _selector, search_string, result_limit, matched_item_handler
):
    runtime = _objective_c_runtime
    if runtime is None or not matched_item_handler:
        return
    keys = ()
    try:
        bridge = _bridge_for(native_self)
        query = runtime.python_string(search_string)
        keys = bridge.search(query, result_limit) if bridge is not None else ()
    except Exception as exc:
        warnings.warn(
            f"Native macOS Help search failed: {exc}", RuntimeWarning
        )
    try:
        runtime.invoke_matched_item_handler(matched_item_handler, keys)
    except Exception as exc:
        warnings.warn(
            f"Native macOS Help result delivery failed: {exc}", RuntimeWarning
        )


@_TitlesMethod
def _localized_titles(native_self, _selector, item):
    runtime = _objective_c_runtime
    if runtime is None:
        return None
    try:
        bridge = _bridge_for(native_self)
        key = runtime.python_string(item)
        titles = bridge.localized_titles(key) if bridge is not None else ()
        return runtime.native_array(titles)
    except Exception as exc:
        warnings.warn(
            f"Native macOS Help title lookup failed: {exc}", RuntimeWarning
        )
        return runtime.native_array(())


@_ActionMethod
def _perform_action(native_self, _selector, item):
    runtime = _objective_c_runtime
    if runtime is None:
        return
    try:
        bridge = _bridge_for(native_self)
        if bridge is not None:
            bridge.open_requested.emit(runtime.python_string(item))
    except Exception as exc:
        warnings.warn(
            f"Native macOS Help action failed: {exc}", RuntimeWarning
        )


class _ObjectiveCRuntime:
    """Minimal Objective-C runtime wrapper needed by the AppKit protocol."""

    CLASS_NAME = b"NFProgressHelpSearchHandler"

    def __init__(self):
        self.objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
        self.appkit = ctypes.CDLL(
            "/System/Library/Frameworks/AppKit.framework/AppKit",
            mode=ctypes.RTLD_GLOBAL,
        )
        self._configure_runtime_functions()
        self._configure_message_senders()
        self.help_search_protocol = self._load_help_search_protocol()
        self.handler_class = self._load_handler_class()
        self.ns_application = self._message_id(
            self.objc.objc_getClass(b"NSApplication"),
            self.selector(b"sharedApplication"),
        )
        if not self.ns_application:
            raise RuntimeError("could not access the shared NSApplication")

    def _configure_runtime_functions(self):
        self.objc.objc_getClass.argtypes = [ctypes.c_char_p]
        self.objc.objc_getClass.restype = _ID
        self.objc.objc_getProtocol.argtypes = [ctypes.c_char_p]
        self.objc.objc_getProtocol.restype = _ID
        self.objc.objc_allocateProtocol.argtypes = [ctypes.c_char_p]
        self.objc.objc_allocateProtocol.restype = _ID
        self.objc.objc_registerProtocol.argtypes = [_ID]
        self.objc.protocol_addMethodDescription.argtypes = [
            _ID,
            _SEL,
            ctypes.c_char_p,
            ctypes.c_bool,
            ctypes.c_bool,
        ]
        self.objc.protocol_addMethodDescription.restype = None
        self.objc.objc_lookUpClass.argtypes = [ctypes.c_char_p]
        self.objc.objc_lookUpClass.restype = _ID
        self.objc.objc_allocateClassPair.argtypes = [
            _ID,
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]
        self.objc.objc_allocateClassPair.restype = _ID
        self.objc.objc_registerClassPair.argtypes = [_ID]
        self.objc.class_addProtocol.argtypes = [_ID, _ID]
        self.objc.class_addProtocol.restype = ctypes.c_bool
        self.objc.class_addMethod.argtypes = [
            _ID,
            _SEL,
            _ID,
            ctypes.c_char_p,
        ]
        self.objc.class_addMethod.restype = ctypes.c_bool
        self.objc.sel_registerName.argtypes = [ctypes.c_char_p]
        self.objc.sel_registerName.restype = _SEL

    def _configure_message_senders(self):
        self._message_id = ctypes.CFUNCTYPE(_ID, _ID, _SEL)(
            ("objc_msgSend", self.objc)
        )
        self._message_id_string = ctypes.CFUNCTYPE(
            _ID, _ID, _SEL, ctypes.c_char_p
        )(("objc_msgSend", self.objc))
        self._message_string = ctypes.CFUNCTYPE(
            ctypes.c_char_p, _ID, _SEL
        )(("objc_msgSend", self.objc))
        self._message_id_size = ctypes.CFUNCTYPE(
            _ID, _ID, _SEL, ctypes.c_ulong
        )(("objc_msgSend", self.objc))
        self._message_void_id = ctypes.CFUNCTYPE(
            None, _ID, _SEL, _ID
        )(("objc_msgSend", self.objc))
        self._message_void = ctypes.CFUNCTYPE(None, _ID, _SEL)(
            ("objc_msgSend", self.objc)
        )
        self._message_bool_id = ctypes.CFUNCTYPE(
            ctypes.c_bool, _ID, _SEL, _ID
        )(("objc_msgSend", self.objc))

    def selector(self, name: bytes):
        return self.objc.sel_registerName(name)

    def _load_help_search_protocol(self):
        protocol = self.objc.objc_getProtocol(b"NSUserInterfaceItemSearching")
        if protocol:
            return protocol

        protocol = self.objc.objc_allocateProtocol(
            b"NSUserInterfaceItemSearching"
        )
        if not protocol:
            raise RuntimeError("could not allocate the macOS Help protocol")
        method_descriptions = (
            (
                b"searchForItemsWithSearchString:resultLimit:matchedItemHandler:",
                b"v@:@q@?",
                True,
            ),
            (b"localizedTitlesForItem:", b"@@:@", True),
            (b"performActionForItem:", b"v@:@", False),
            (b"showAllHelpTopicsForSearchString:", b"v@:@", False),
        )
        for selector_name, encoding, required in method_descriptions:
            self.objc.protocol_addMethodDescription(
                protocol,
                self.selector(selector_name),
                encoding,
                required,
                True,
            )
        self.objc.objc_registerProtocol(protocol)
        return protocol

    def _load_handler_class(self):
        existing_class = self.objc.objc_lookUpClass(self.CLASS_NAME)
        if existing_class:
            self.objc.class_addProtocol(
                existing_class, self.help_search_protocol
            )
            return existing_class

        handler_class = self.objc.objc_allocateClassPair(
            self.objc.objc_getClass(b"NSObject"), self.CLASS_NAME, 0
        )
        if not handler_class:
            raise RuntimeError("could not allocate the Objective-C help class")

        self.objc.class_addProtocol(
            handler_class, self.help_search_protocol
        )

        methods = (
            (
                b"searchForItemsWithSearchString:resultLimit:matchedItemHandler:",
                _search_for_items,
                b"v@:@q@?",
            ),
            (b"localizedTitlesForItem:", _localized_titles, b"@@:@"),
            (b"performActionForItem:", _perform_action, b"v@:@"),
        )
        for selector_name, method, encoding in methods:
            added = self.objc.class_addMethod(
                handler_class,
                self.selector(selector_name),
                ctypes.cast(method, _ID),
                encoding,
            )
            if not added:
                raise RuntimeError(
                    f"could not add Objective-C method {selector_name!r}"
                )
        self.objc.objc_registerClassPair(handler_class)
        return handler_class

    def new_handler(self):
        allocated = self._message_id(
            self.handler_class, self.selector(b"alloc")
        )
        return self._message_id(allocated, self.selector(b"init"))

    def register_handler(self, handler):
        conforms = self._message_bool_id(
            handler,
            self.selector(b"conformsToProtocol:"),
            self.help_search_protocol,
        )
        if not conforms:
            raise RuntimeError(
                "the native Help handler does not conform to its protocol"
            )
        self._message_void_id(
            self.ns_application,
            self.selector(b"registerUserInterfaceItemSearchHandler:"),
            handler,
        )

    def unregister_handler(self, handler):
        self._message_void_id(
            self.ns_application,
            self.selector(b"unregisterUserInterfaceItemSearchHandler:"),
            handler,
        )
        self._message_void(handler, self.selector(b"release"))

    def native_string(self, value: str):
        return self._message_id_string(
            self.objc.objc_getClass(b"NSString"),
            self.selector(b"stringWithUTF8String:"),
            value.encode("utf-8"),
        )

    def python_string(self, value) -> str:
        utf8_value = self._message_string(
            value, self.selector(b"UTF8String")
        )
        return utf8_value.decode("utf-8") if utf8_value else ""

    def native_array(self, values: Iterable[str]):
        values = tuple(values)
        array = self._message_id_size(
            self.objc.objc_getClass(b"NSMutableArray"),
            self.selector(b"arrayWithCapacity:"),
            len(values),
        )
        add_object = self.selector(b"addObject:")
        for value in values:
            self._message_void_id(array, add_object, self.native_string(value))
        return array

    def invoke_matched_item_handler(self, handler, values: Iterable[str]):
        results = self.native_array(values)
        block = ctypes.cast(handler, ctypes.POINTER(_BlockLiteral)).contents
        invoke = ctypes.CFUNCTYPE(None, _ID, _ID)(block.invoke)
        invoke(handler, results)


def _runtime() -> _ObjectiveCRuntime:
    global _objective_c_runtime
    if _objective_c_runtime is None:
        with _objective_c_runtime_lock:
            if _objective_c_runtime is None:
                _objective_c_runtime = _ObjectiveCRuntime()
    return _objective_c_runtime


class MacOSHelpSearch(QObject):
    """Registers help topics through NSUserInterfaceItemSearching on macOS."""

    open_requested = Signal(str)

    def __init__(
        self,
        items: Iterable[HelpSearchItem],
        open_callback: Callable[[str], None],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._items_lock = threading.RLock()
        self._items = ()
        self._items_by_key = {}
        self._native_handler = None
        self.open_requested.connect(
            open_callback, Qt.ConnectionType.QueuedConnection
        )
        self.update_items(items)
        self._register()

    @property
    def is_registered(self) -> bool:
        return self._native_handler is not None

    def update_items(self, items: Iterable[HelpSearchItem]):
        items = tuple(items)
        with self._items_lock:
            self._items = items
            self._items_by_key = {item.key: item for item in items}

    def search(self, query: str, limit: int) -> tuple[str, ...]:
        if not query.strip():
            return ()
        with self._items_lock:
            items = self._items
        return tuple(
            item.key
            for item in ranked_help_search_items(items, query, limit)
        )

    def localized_titles(self, key: str) -> tuple[str, ...]:
        with self._items_lock:
            item = self._items_by_key.get(key)
        return item.display_path if item is not None else ()

    def _register(self):
        runtime = _runtime()
        handler = runtime.new_handler()
        if not handler:
            raise RuntimeError("could not create the native Help handler")
        with _bridges_lock:
            _bridges_by_native_id[int(handler)] = self
        try:
            runtime.register_handler(handler)
        except Exception:
            with _bridges_lock:
                _bridges_by_native_id.pop(int(handler), None)
            runtime.unregister_handler(handler)
            raise
        self._native_handler = handler
        application = QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.unregister)

    def unregister(self):
        handler = self._native_handler
        if handler is None:
            return
        self._native_handler = None
        with _bridges_lock:
            _bridges_by_native_id.pop(int(handler), None)
        _runtime().unregister_handler(handler)


def create_macos_help_search(
    items: Iterable[HelpSearchItem],
    open_callback: Callable[[str], None],
    parent: QObject | None = None,
) -> MacOSHelpSearch | None:
    """Creates the native bridge on macOS and is a no-op elsewhere."""
    if platform.system() != "Darwin":
        return None
    try:
        return MacOSHelpSearch(items, open_callback, parent)
    except Exception as exc:
        warnings.warn(
            f"Could not register native macOS Help search: {exc}",
            RuntimeWarning,
        )
        return None
