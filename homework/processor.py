from enum import Enum, auto
from ctypes import c_uint8


class Register(Enum):
    # 8-bit registers: w = 0
    AL = (0, 0b000)
    CL = (0, 0b001)
    DL = (0, 0b010)
    BL = (0, 0b011)
    AH = (0, 0b100)
    CH = (0, 0b101)
    DH = (0, 0b110)
    BH = (0, 0b111)

    # 16-bit registers: w = 1
    AX = (1, 0b000)
    CX = (1, 0b001)
    DX = (1, 0b010)
    BX = (1, 0b011)
    SP = (1, 0b100)
    BP = (1, 0b101)
    SI = (1, 0b110)
    DI = (1, 0b111)
    # BX_SI = 0b000
    # BX_DI = 0b001
    # BP_SI = 0b010
    # BP_DI = 0b011
    # SI = 0b100
    # DI = 0b101
    # BP = 0b110
    # BX = 0b111


class Flags(Enum):
    ZF = 0  # Zero flag
    SF = 1  # Sign flag
    # We don't simulate other flags for now


class Operation(Enum):
    MOV = auto()
    ADD = auto()
    SUB = auto()
    CMP = auto()


class FlagWord:
    def __init__(self):
        # SF, ZF
        self.word = 0

    def __getitem__(self, bit):
        return self.word >> bit & 1

    def __setitem__(self, bit: Flags, value: int):
        self.word = (self.word & ~(1 << bit.value)) | ((value & 1) << bit.value)


class Registers:
    def __init__(self):
        # AX, CX, DX, BX, SP, BP, SI, DI
        self.words = [0] * 8

    def __getitem__(self, register):
        w, code = register.value
        if w:
            return self.words[code]

        index = code & 0b11
        shift = 8 if code & 0b100 else 0
        return (self.words[index] >> shift) & 0xFF

    def __setitem__(self, register, value):
        w, code = register.value
        if w:
            print(f"Set {register.name} {self.words[code]:#04x} -> {value:#04x}")
            self.words[code] = value & 0xFFFF
            return

        index = code & 0b11
        shift = 8 if code & 0b100 else 0
        mask = 0xFF << shift
        self.words[index] = (
            (self.words[index] & ~mask) | ((value & 0xFF) << shift)
        )


class CPU:
    registers: Register
    flags: FlagWord

    def __init__(self):
        self.registers = Registers()
        self.flags = FlagWord()
        return
    
    def _printInstruction(self, op: Operation, dest: str, source: str):
        print(f"{op.name:<4} {dest}, {source:<4}", end="; ")
        
    def execute(self, op: Operation, dest: Register, source: int):
        match op:
            case Operation.MOV:
                if type(source) == Register:
                    self._printInstruction(op, dest.name, source.name)
                    self.registers[dest] = self.registers[source]
                    return
                self._printInstruction(op, dest.name, source)
                self.registers[dest] = source
            case _:
                print(f"Can't simulate unsupported operation {op.name}")

    def printState(self):
        print(f"CPU registers state:")
        for reg in range(8):
            register = Register((1, reg))
            print(
                f"{register.name}: {self.registers[register]:016b} - {self.registers[register]:#04x}")
        for flag in range(len(Flags)):
            print(f"{Flags(flag).name}: {self.flags[flag]}", end=";\t")
