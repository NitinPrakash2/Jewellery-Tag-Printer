"""Printer abstraction. UI/services talk to PrinterAdapter, never to drivers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PrinterInfo:
    name: str
    is_default: bool = False
    status: str = "unknown"


@dataclass
class PrintJobResult:
    ok: bool
    message: str


class PrinterError(Exception):
    pass


class PrinterNotFound(PrinterError):
    pass


class PrinterOffline(PrinterError):
    pass


class PrinterAdapter(ABC):
    @abstractmethod
    def discover_printers(self) -> list[PrinterInfo]:
        ...

    @abstractmethod
    def get_status(self, printer_name: str) -> PrinterInfo:
        ...

    @abstractmethod
    def print_svg(self, printer_name: str, svg: str, copies: int = 1) -> PrintJobResult:
        """Print one side. Front/back are separate passes (no duplex assumed)."""

    @abstractmethod
    def print_test(self, printer_name: str) -> PrintJobResult:
        ...
