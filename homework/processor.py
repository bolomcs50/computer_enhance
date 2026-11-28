from enum import Enum, auto
from ctypes import c_uint16, c_uint8


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
    
class PointerRegister(Enum):
    BX_SI = 0b000
    BX_DI = 0b001
    BP_SI = 0b010
    BP_DI = 0b011
    SI = 0b100
    DI = 0b101
    BP = 0b110
    BX = 0b111
    NONE = auto()


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
        if isinstance(value, c_uint16) or isinstance(value, c_uint8):
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

class Address:
    fromRegister: PointerRegister
    displacement: int
    
    def __init__(self, fromRegister: PointerRegister, displacement: int = 0):
        self.fromRegister = fromRegister
        self.displacement = displacement

def parity(result: c_uint16):
    count = 0
    for shift in range(8):
        count += result >> shift & 0b1
    return count % 2 == 0

def formatRegAddrInt(x: Register | Address | int):
    src = x
    if type(x) == Register:
        src = x.name.lower()
    elif type(x) == Address:
        if x.fromRegister == PointerRegister.NONE:
            src = f"[{x.displacement}]"
        elif not x.displacement:
            src = f"[{x.fromRegister.name.lower()}]"
        else:
            src = f"[{x.fromRegister.name.lower()} + {x.displacement}]"
    return src

class CPU:
    registers: Register
    flags: FlagWord
    instructions: bytearray
    ip: int # Instruction Pointer
    memory: list[c_uint8]
    cycles: int

    def __init__(self, instructions: bytearray):
        self.registers = Registers()
        self.flags = FlagWord()
        self.instructions = instructions
        self.ip = 0
        self.memory = [c_uint8(0)] * 1024 * 1024 # 1 MB of memory on a 8086
        self.cycles = 0
        return


    def __printInstruction(self, op: Operation, dest: Register | Address | int, source: Register | Address | int):
        dst = formatRegAddrInt(dest)
        src = formatRegAddrInt(source)
        
        print(f"{op.name.lower():<4} {dst}", end="")
        if src:
            print(f", {src:<6}", end = "; ")
        else:
            print("", end="; ")

    def __upateFlags(self, result: c_uint16):
        self.flags[Flags.ZF] = result == 0
        self.flags[Flags.SF] = result >> 15 & 1
        self.flags[Flags.PF] = parity(result)
    
    def __calcAddr(self, addr: Address):
        start: int = 0
        cycles: int = 0
        match addr.fromRegister:
            case PointerRegister.BX_SI:
                start = self.registers[Register.BX] + self.registers[Register.SI]
            case PointerRegister.BX_DI:
                start = self.registers[Register.BX] + self.registers[Register.DI]
            case PointerRegister.BP_SI:
                start = self.registers[Register.BP] + self.registers[Register.SI]
            case PointerRegister.BP_DI:
                start = self.registers[Register.BP] + self.registers[Register.DI]
            case PointerRegister.SI:
                start = self.registers[Register.SI]
            case PointerRegister.DI:
                start = self.registers[Register.DI]
            case PointerRegister.BP:
                start = self.registers[Register.BP]
            case PointerRegister.BX:
                start = self.registers[Register.BX]

        match addr.fromRegister:
            case PointerRegister.NONE:
                cycles += 6
            case PointerRegister.SI | PointerRegister.DI | PointerRegister.BP | PointerRegister.BX:
                cycles += 9 if addr.displacement else 5
            case PointerRegister.BP_DI | PointerRegister.BX_SI:
                cycles += 11 if addr.displacement else 7
            case PointerRegister.BP_SI | PointerRegister.BX_DI:
                cycles += 12 if addr.displacement else 8
        
        self.cycles += cycles
        return start + addr.displacement

    def hasNextByte(self):
        return self.ip < len(self.instructions)

    def getNextByte(self):
        if self.ip >= len(self.instructions):
            return None
        byte = self.instructions[self.ip]
        self.ip += 1
        return byte

    def extractValue(self, x: Register | Address | int):
        if type(x) == int or x == None:
            return x
        if type(x) == Register:
            return self.registers[x]
        addr = self.__calcAddr(x)
        return self.memory[addr]
    
    def execute(self, op: Operation, dest: Register | Address | int, source: Register | Address | int = None):
        self.__printInstruction(op, dest, source)
        src = self.extractValue(source)
        match op:
            case Operation.MOV:
                # Cycle estimation
                if type (dest) == Register:
                    if type(source) == Register:
                        self.cycles += 2
                    elif type(source) == int:
                        self.cycles += 4
                    elif type(source) == Address:
                        self.cycles += 8
                        self.cycles += 4 # Memory fetch penalty
                if type(dest) == Address:
                    self.cycles += 4 # Memory write penalty
                    if type(source) == Register:
                        self.cycles += 9
                        
                if type(dest) == Address:
                    addr = self.__calcAddr(dest)
                    self.memory[addr] = src
                    print()
                else:
                    self.registers[dest] = src
            case Operation.ADD:
                if type(dest) == Register:
                    if type(source) == Register:
                        self.cycles += 3
                    elif type(source) == Address:
                        self.cycles += 9
                        self.cycles += 4 # Memory transfer penalty
                    elif type(source) == int:
                        self.cycles += 4
                if type(dest) == Address:
                    self.cycles += 8 # Double memory transfer penalty
                    if type(source) == Register:
                        self.cycles += 16
                
                if type(dest) == Address:
                    addr = self.__calcAddr(dest)
                    self.memory[addr] += src
                    self.__upateFlags(self.memory[addr])
                    print()
                else:
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
        print(f"Now cycles {self.cycles}")

    def printState(self):
        print(f"CPU registers state:")
        for reg in range(8):
            register = Register((1, reg))
            if self.registers[register] == 0:
                continue
            print(
                f"\t{register.name}: {self.registers[register]:#04x} ({self.registers[register]})")

        print("Flags and Instruction Pointer")
        for flag in Flags:
            print(f"\t{flag.name}: {self.flags[flag]}", end="")
            
        print()
        print(f"\tIP: {self.ip}")
        print(f"Estimated cylces: {self.cycles}")
        
        print("Nonzero Memory")
        for i in range(len(self.memory)):
            if self.memory[i]:
                print(f"\t{i:<4}: {self.memory[i]:#04x}")
