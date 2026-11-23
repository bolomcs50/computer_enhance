from enum import Enum, auto

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

class Operation(Enum):
    MOV = auto()
    ADD = auto()
    SUB = auto()
    CMP = auto()
    
class CPU:
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
            print(f"Set {register.name} {self.words[code]:08b} -> {value:08b}")
            self.words[code] = value & 0xFFFF
            return

        index = code & 0b11
        shift = 8 if code & 0b100 else 0
        mask = 0xFF << shift
        self.words[index] = (
            (self.words[index] & ~mask) | ((value & 0xFF) << shift)
        )

    def execute(self, op: Operation, dest : Register, source: int):
        match op:
            case Operation.MOV:
                if type(source) == Register:
                    print(f"{op.name} {dest.name}, {source.name}")
                    self[dest] = self[source]
                    return
                print(f"{op.name} {dest.name}, {source}")
                self[dest] = source
            case _:
                print(f"Can't simulate unsupported operation {op.name}")
    
    def printState(self):
        print(f"CPU registers state:")
        for code in range(8):
            register = Register((1, code))
            print(f"{register.name}: {self[register]:08b}")