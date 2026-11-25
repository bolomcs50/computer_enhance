# Read assembled Intel 8086 binaries and decode them to instructions
# https://edge.edx.org/c4x/BITSPilani/EEE231/asset/8086_family_Users_Manual_1_.pdf

from processor import CPU, Operation, Register

rm_to_effective_address = {
    0b000 : "bx + si",
    0b001 : "bx + di",
    0b010 : "bp + si",
    0b011 : "bp + di",
    0b100 : "si",
    0b101 : "di",
    0b110 : "bp",
    0b111 : "bx",
}

opcode_to_op = {
    0b000 : Operation.ADD,
    0b101 : Operation.SUB,
    0b111 : Operation.CMP
}
    
def mod_reg_rm_to_dest_source(b1, cpu: CPU):
    b2 = cpu.getNextByte()
    d = b1 >> 1 & 1
    w = b1 & 1
    mod = b2 >> 6
    reg = b2 >> 3 & 0b111
    rm = b2 & 0b111
    register = Register((w,reg))
    
    if mod == 0b11:
        source_reg = Register((w,rm))
        dest = register if d else source_reg
        source = source_reg if d else register
        return dest, source
    
    if mod == 0b00 and rm == 0b110:
        data = [cpu.getNextByte(), cpu.getNextByte()]
        value = f"[{int.from_bytes(data, "little")}]"
        dest = register if d else value
        source = value if d else register
        return dest, source
    
    displacement = None
    if mod == 0b01 or mod == 0b10:
        disp_length = 1 if mod == 0b01 else 2
        displacement = int.from_bytes([cpu.getNextByte() for _ in range(disp_length)], "little", signed=True)

    rm_name = format_register_displacement(rm_to_effective_address[rm], displacement)
    dest = register if d else rm_name
    source = rm_name if d else register
    return dest, source

def format_register_displacement(r_name, displacement):
    if not displacement:
        return f"[{r_name}]"
    elif displacement > 0:
        return f"[{r_name} + {displacement}]"
    return f"[{r_name} - {abs(displacement)}]"

def mod_opcode_rm_to_dest_width_value(b1, cpu: CPU, s_for_width = False):
    s = b1 >> 1 & 1
    w = b1 & 1
    b2 = cpu.getNextByte()
    mod = b2 >> 6
    opcode = b2 >> 3 & 0b111
    rm = b2 & 0b111
    
    if opcode not in opcode_to_op.keys():
        return None, None, None, None
    operation = opcode_to_op[opcode]
    
    displacement = None
    if (mod == 0b00 and rm == 0b110) or mod == 0b01 or mod == 0b10:
        disp_length = 1 if mod == 0b01 else 2
        displacement = int.from_bytes([cpu.getNextByte() for _ in range(disp_length)], "little", signed=True)
    data_width = 2 if (s_for_width and not s and w) or (not s_for_width and w) else 1
    value = int.from_bytes([cpu.getNextByte() for _ in range(data_width)], "little")

    instant_width = None
    if mod == 0b11:
        return Register((w,rm)), instant_width, value, operation
    else:
        rm_name = None
        instant_width = "word " if w else "byte "
        if mod == 0b00 and rm == 0b110:
            rm_name = f"[{displacement}]"
        else:
            rm_name = rm_to_effective_address[rm]
            rm_name = format_register_displacement(rm_name, displacement)
        return rm_name, instant_width, value, operation

def mem_to_accumulator(b1, cpu: CPU):
    d = b1 >> 1 & 1
    w = b1 & 1
    width = 2 if w else 1
    addr = int.from_bytes([cpu.getNextByte() for _ in range(width)], "little")
    accumulator = "ax" if w else "al"
    addr = f"[{addr}]"
    if d:
        return addr, accumulator
    return accumulator, addr

def data_to_accumulator(b1, cpu: CPU):
    w = b1 & 1
    width = 2 if w else 1
    value = int.from_bytes([cpu.getNextByte() for _ in range(width)], "little", signed=True)
    accumulator = "ax" if w else "al"
    return accumulator, value

def regOrStringToLow(reg: Register | str):
    if type(reg) == Register:
        return reg.name.lower()
    return reg

def parse(bytes: bytearray):
    output = ["bits 16"]
    cpu = CPU(bytes)
    
    while cpu.hasNextByte():
        b1 = cpu.getNextByte()
        
        if b1 >> 2 == 0b100010: # MOV register/memory to/from register
            dest, source = mod_reg_rm_to_dest_source(b1, cpu)
            # cpu.execute(Operation.MOV, dest, source)
            output.append(f"mov {regOrStringToLow(dest)}, {regOrStringToLow(source)}")

        elif b1 >> 4 == 0b1011: # MOV immediate to register
            w = b1 >> 3 & 1
            reg = b1 & 0b111
            register = Register((w,reg))
            reg_name = register.name.lower()
            arguments = f"{reg_name}, "
            data_bytes = 2 if w else 1
            value = int.from_bytes([cpu.getNextByte() for _ in range(data_bytes)], "little")
            arguments += str(value)
            # cpu.execute(Operation.MOV, register, value)
            output.append(f"mov {arguments}")
            
        elif b1 >> 1 == 0b1100011: # MOV immediate to register/memory
            dest, width, value, _ = mod_opcode_rm_to_dest_width_value(b1, cpu)
            output.append(f"mov {dest}, {width if width else ""}{value}")

        elif b1 >> 2 == 0b101000: # MOV memory to accumulator and MOV accumulator to memory
            dest, src = mem_to_accumulator(b1, cpu)
            output.append(f"mov {dest}, {src}")

        elif b1 >> 2 == 0b000000: # ADD reg/memory with register to either
            dest, source = mod_reg_rm_to_dest_source(b1, cpu)
            output.append(f"add {regOrStringToLow(dest)}, {regOrStringToLow(source)}")
        
        elif b1 >> 2 == 0b100000: # ADD/SUB/CMP immediate to register/memory
            dest, width, value, operation = mod_opcode_rm_to_dest_width_value(b1, cpu, True)
            if dest:
                # cpu.execute(operation, dest, value) # TODO: deal with width
                output.append(f"{operation.name.lower()} {width if width else ""}{regOrStringToLow(dest)}, {value}")
            else:
                print(f"Unknown instruction {b1:08b}")
                output.append(f"UNK {b1:08b}")
            
        elif b1 >> 1 == 0b0000010: # ADD immediate to accumulator
            acc, value = data_to_accumulator(b1, cpu)
            output.append(f"add {acc}, {value}")
        
        elif b1 >> 2 == 0b001010: # SUB reg/memory and register to either
            dest, source = mod_reg_rm_to_dest_source(b1, cpu)
            # cpu.execute(Operation.SUB, dest, source)
            output.append(f"sub {regOrStringToLow(dest)}, {regOrStringToLow(source)}")
            
        elif b1 >> 1 == 0b0010110: # SUB immediate from accumulator
            acc, value = data_to_accumulator(b1, cpu)
            output.append(f"sub {acc}, {value}")
        
        elif b1 >> 2 == 0b001110: # CMP reg/memory and register
            dest, source = mod_reg_rm_to_dest_source(b1, cpu)
            # cpu.execute(Operation.CMP, dest, source)
            output.append(f"cmp {regOrStringToLow(dest)}, {regOrStringToLow(source)}")
            
        elif b1 >> 1 == 0b0011110: # CMP immediate with accumulator
            acc, value = data_to_accumulator(b1, cpu)
            output.append(f"cmp {acc}, {value}")
            
        elif b1 == 0b01110101: # JNZ: Jump if not equal/zero
            inc8 = int(cpu.getNextByte())
            output.append(f"jnz {inc8}")
        
        elif b1 == 0b01110100: # JE: Jump if equal/zero
            inc8 = int(cpu.getNextByte())
            output.append(f"je {inc8}")

        elif b1 == 0b01111100: # JL: Jump on less
            inc8 = int(cpu.getNextByte())
            output.append(f"jl {inc8}")
        
        elif b1 == 0b01111110: # JLE: Jump on less or equal
            inc8 = int(cpu.getNextByte())
            output.append(f"jle {inc8}")
        
        elif b1 == 0b01110010: # JB: Jump on below
            inc8 = int(cpu.getNextByte())
            output.append(f"jb {inc8}")
        
        elif b1 == 0b01110110: # JBE: Jump on below or equal
            inc8 = int(cpu.getNextByte())
            output.append(f"jbe {inc8}")
                                
        elif b1 == 0b01111010: # JP: Jump on parity
            inc8 = int(cpu.getNextByte())
            output.append(f"jp {inc8}")
        
        elif b1 == 0b01110000: # JO: Jump on overflow
            inc8 = int(cpu.getNextByte())
            output.append(f"jo {inc8}")
        
        elif b1 == 0b01111000: # JS: Jump on sign
            inc8 = int(cpu.getNextByte())
            output.append(f"js {inc8}")
                    
        elif b1 == 0b01111101: # JNL: Jump on not less
            inc8 = int(cpu.getNextByte())
            output.append(f"jnl {inc8}")
                    
        elif b1 == 0b01111111: # JG: Jump on greater
            inc8 = int(cpu.getNextByte())
            output.append(f"jg {inc8}")
                    
        elif b1 == 0b01110011: # JNB: Jump on not below
            inc8 = int(cpu.getNextByte())
            output.append(f"jnb {inc8}")
                    
        elif b1 == 0b01110111: # JA: Jump if above
            inc8 = int(cpu.getNextByte())
            output.append(f"ja {inc8}")
                    
        elif b1 == 0b01111011: # JNP: Jump on not par
            inc8 = int(cpu.getNextByte())
            output.append(f"jnp {inc8}")
            
        elif b1 == 0b01110001: # JNO: Jump on not overflow
            inc8 = int(cpu.getNextByte())
            output.append(f"jno {inc8}")

        elif b1 == 0b01111001: # JNS: Jump on not sign
            inc8 = int(cpu.getNextByte())
            output.append(f"jns {inc8}")

        elif b1 == 0b11100010: # Loop CX times
            inc8 = int(cpu.getNextByte())
            output.append(f"loop {inc8}")

        elif b1 == 0b11100001: # Loop while zero
            inc8 = int(cpu.getNextByte())
            output.append(f"loopz {inc8}")

        elif b1 == 0b11100000: # Loop while nonzero
            inc8 = int(cpu.getNextByte())
            output.append(f"loopnz {inc8}")

        elif b1 == 0b11100011: # Jump on CX zero
            inc8 = int(cpu.getNextByte())
            output.append(f"jcxz {inc8}")
 
        else:
            print(f"Unknown instruction {b1:08b}")
            output.append(f"UNK {b1:08b}")
    
    cpu.printState()        
    return output

def decode(file):
    with open(file, "rb") as source:
        data = source.read()
        return parse(bytearray(data))
            
