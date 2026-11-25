from enum import Enum, auto
from ctypes import c_uint16


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


class Flags(Enum):
    ZF = 0  # Zero flag
    SF = 1  # Sign flag
    PF = 2  # Parity flag
    # We don't simulate other flags for now


class Operation(Enum):
    MOV = auto()
    ADD = auto()
    SUB = auto()
    CMP = auto()
    JNZ = auto()


class FlagWord:
    def __init__(self):
        # SF, ZF, PF, ...
        self.word = 0

    def __getitem__(self, bit: Flags):
        return self.word >> bit.value & 1

    def __setitem__(self, bit: Flags, value: int):
        if self[bit] == value:
            return
        print(f"Flag {bit.name}: {self[bit]} -> {int(value)}")
        self.word = (self.word & ~(1 << bit.value)) | (
            (value & 1) << bit.value)


class Registers:
    def __init__(self):
        # AX, CX, DX, BX, SP, BP, SI, DI
        self.words = [c_uint16(0) for _ in range(8)]

    def __getitem__(self, register) -> int:
        w, code = register.value

        if w:
            return self.words[code].value

        index = code & 0b11
        shift = 8 if code & 0b100 else 0
        return (self.words[index].value >> shift) & 0xFF

    def __setitem__(self, register, value: int | c_uint16) -> None:
        if isinstance(value, c_uint16):
            value = value.value

        w, code = register.value
        if w:
            word = self.words[code]
            new_value = value & 0xFFFF
            print(
                f"{register.name} "
                f"{word.value:#06x} -> {new_value:#06x}"
            )
            word.value = new_value
            return

        index = code & 0b11
        shift = 8 if code & 0b100 else 0
        mask = 0xFF << shift
        word = self.words[index]
        word.value = (word.value & ~mask) | ((value & 0xFF) << shift)


def parity(result: c_uint16):
    count = 0
    for shift in range(8):
        count += result >> shift & 0b1
    return count % 2 == 0

class CPU:
    registers: Register
    flags: FlagWord
    instructions: bytearray
    ip: int # Instruction Pointer

    def __init__(self, instructions: bytearray):
        self.registers = Registers()
        self.flags = FlagWord()
        self.instructions = instructions
        self.ip = 0
        return

    def __printInstruction(self, op: Operation, dest: Register | int, source: Register | int):
        src = source
        if type(source) == Register:
            src = source.name
        dst = dest
        if type(dest) == Register:
            dst = dest.name
        
        print(f"{op.name:<4} {dst}", end="")
        if src:
            print(f", {src:<6}", end = "; ")
        else:
            print("", end="; ")

    def __upateFlags(self, result: c_uint16):
        self.flags[Flags.ZF] = result == 0
        self.flags[Flags.SF] = result >> 15 & 1
        self.flags[Flags.PF] = parity(result)

    def hasNextByte(self):
        return self.ip < len(self.instructions)

    def getNextByte(self):
        if self.ip >= len(self.instructions):
            return None
        byte = self.instructions[self.ip]
        self.ip += 1
        return byte

    def execute(self, op: Operation, dest: Register | int, source: Register | int = None):
        self.__printInstruction(op, dest, source)
        src = self.registers[source] if type(source) == Register else source
        match op:
            case Operation.MOV:
                self.registers[dest] = src
                return
            case Operation.ADD:
                self.registers[dest] += src
                self.__upateFlags(self.registers[dest])
            case Operation.SUB:
                self.registers[dest] -= src
                self.__upateFlags(self.registers[dest])
            case Operation.CMP:
                res = self.registers[dest] - src
                self.__upateFlags(res)
            case Operation.JNZ:
                if not self.flags[Flags.ZF]:
                    self.ip += dest
            case _:
                print(f"Can't simulate unsupported operation {op.name}")

    def printState(self):
        print(f"CPU registers state:")
        for reg in range(8):
            register = Register((1, reg))
            if self.registers[register] == 0:
                continue
            print(
                f"\t{register.name}: {self.registers[register]:#04x} ({self.registers[register]})")

        print()
        for flag in Flags:
            print(f"\t{flag.name}: {self.flags[flag]}", end="")
            
        print()
        print(f"\tIP: {self.ip}")
