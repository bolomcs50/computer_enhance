# Read assembled Intel 8086 binaries and decode them to instructions
# https://edge.edx.org/c4x/BITSPilani/EEE231/asset/8086_family_Users_Manual_1_.pdf

reg_to_name = {
    0: {
        0b000 : "al",
        0b001 : "cl",
        0b010 : "dl",
        0b011 : "bl",
        0b100 : "ah",
        0b101 : "ch",
        0b110 : "dh",
        0b111 : "bh",
    },
    1: {
        0b000 : "ax",
        0b001 : "cx",
        0b010 : "dx",
        0b011 : "bx",
        0b100 : "sp",
        0b101 : "bp",
        0b110 : "si",
        0b111 : "di",
    }
}

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
    0b000 : "add",
    0b101 : "sub",
    0b111 : "cmp"
}

def mod_reg_rm_to_dest_source(b1, bytes: bytearray):
    b2 = bytes.pop(0)
    d = b1 >> 1 & 1
    w = b1 & 1
    mod = b2 >> 6
    reg = b2 >> 3 & 0b111
    rm = b2 & 0b111
    reg_name = reg_to_name[w][reg]
    
    if mod == 0b11:
        rm_name = reg_to_name[w][rm]
        dest = reg_name if d else rm_name
        source = rm_name if d else reg_name
        return dest, source
    
    if mod == 0b00 and rm == 0b110:
        value = f"[{int.from_bytes(bytes[:2], "little")}]"
        del bytes[:2]
        dest = reg_name if d else value
        source = value if d else reg_name
        return dest, source
    
    displacement = None
    if mod == 0b01 or mod == 0b10:
        disp_length = 1 if mod == 0b01 else 2
        displacement = int.from_bytes(bytes[:disp_length], "little", signed=True)
        del bytes[:disp_length]
    rm_name = format_register_displacement(rm_to_effective_address[rm], displacement)
    dest = reg_name if d else rm_name
    source = rm_name if d else reg_name
    return dest, source

def format_register_displacement(r_name, displacement):
    if not displacement:
        return f"[{r_name}]"
    elif displacement > 0:
        return f"[{r_name} + {displacement}]"
    return f"[{r_name} - {abs(displacement)}]"

def mod_opcode_rm_to_dest_width_value(b1, bytes:bytearray, s_for_width = False):
    s = b1 >> 1 & 1
    w = b1 & 1
    b2 = bytes.pop(0)
    mod = b2 >> 6
    opcode = b2 >> 3 & 0b111
    rm = b2 & 0b111
    operation = opcode_to_op[opcode]
    displacement = None
    if (mod == 0b00 and rm == 0b110) or mod == 0b01 or mod == 0b10:
        disp_width = 1 if mod == 0b01 else 2
        displacement = int.from_bytes(bytes[:disp_width], "little", signed=True)
        del bytes[:disp_width]
    data_width = 2 if (s_for_width and not s and w) or (not s_for_width and w) else 1
    value = int.from_bytes(bytes[:data_width], "little")
    del bytes[:data_width]
    rm_name = None
    instant_width = None
    if mod == 0b11:
        rm_name = reg_to_name[w][rm]
        return rm_name, instant_width, value, operation
    else:
        instant_width = "word " if w else "byte "
        if mod == 0b00 and rm == 0b110:
            rm_name = f"[{displacement}]"
        else:
            rm_name = rm_to_effective_address[rm]
            rm_name = format_register_displacement(rm_name, displacement)
    return rm_name, instant_width, value, operation

def mem_to_accumulator(b1, bytes: bytearray):
    d = b1 >> 1 & 1
    w = b1 & 1
    width = 2 if w else 1
    addr = int.from_bytes(bytes[:width], "little")
    del bytes[:width]
    accumulator = "ax" if w else "al"
    addr = f"[{addr}]"
    if d:
        return addr, accumulator
    return accumulator, addr

def data_to_accumulator(b1, bytes: bytearray):
    w = b1 & 1
    width = 2 if w else 1
    value = int.from_bytes(bytes[:width], "little", signed=True)
    del bytes[:width]
    accumulator = "ax" if w else "al"
    return accumulator, value

def ip_inc8(bytes: bytearray):
    increment = int.from_bytes(bytes[:1], "little", signed=True)
    del bytes[:1]
    return increment

def parse(bytes: bytearray):
    output = ["bits 16"]
    while len(bytes):
        b1 = bytes.pop(0)
        
        if b1 >> 2 == 0b100010: # MOV register/memory to/from register
            dest, source = mod_reg_rm_to_dest_source(b1, bytes)
            output.append(f"mov {dest}, {source}")

        elif b1 >> 4 == 0b1011: # MOV immediate to register
            w = b1 >> 3 & 1
            reg = b1 & 0b111
            reg_name = reg_to_name[w][reg]
            arguments = f"{reg_name}, "
            data_bytes = 2 if w else 1
            value, bytes = int.from_bytes(bytes[:data_bytes], "little"), bytes[data_bytes:]
            arguments += str(value)
            output.append(f"mov {arguments}")
            
        elif b1 >> 1 == 0b1100011: # MOV immediate to register/memory
            dest, width, value, _ = mod_opcode_rm_to_dest_width_value(b1, bytes)
            output.append(f"mov {dest}, {width if width else ""}{value}")

        elif b1 >> 2 == 0b101000: # MOV memory to accumulator and MOV accumulator to memory
            dest, src = mem_to_accumulator(b1, bytes)
            output.append(f"mov {dest}, {src}")

        elif b1 >> 2 == 0b000000: # ADD reg/memory with register to either
            dest, source = mod_reg_rm_to_dest_source(b1, bytes)
            output.append(f"add {dest}, {source}")
        
        elif b1 >> 2 == 0b100000: # ADD/SUB/CMP immediate to register/memory
            dest, width, value, opcode = mod_opcode_rm_to_dest_width_value(b1, bytes, True)
            output.append(f"{opcode} {width if width else ""}{dest}, {value}")
            
        elif b1 >> 1 == 0b0000010: # ADD immediate to accumulator
            acc, value = data_to_accumulator(b1, bytes)
            output.append(f"add {acc}, {value}")
        
        elif b1 >> 2 == 0b001010: # SUB reg/memory and register to either
            dest, source = mod_reg_rm_to_dest_source(b1, bytes)
            output.append(f"sub {dest}, {source}")
            
        elif b1 >> 1 == 0b0010110: # SUB immediate from accumulator
            acc, value = data_to_accumulator(b1, bytes)
            output.append(f"sub {acc}, {value}")
        
        elif b1 >> 2 == 0b001110: # CMP reg/memory and register
            dest, source = mod_reg_rm_to_dest_source(b1, bytes)
            output.append(f"cmp {dest}, {source}")
            
        elif b1 >> 1 == 0b0011110: # CMP immediate with accumulator
            acc, value = data_to_accumulator(b1, bytes)
            output.append(f"cmp {acc}, {value}")
            
        elif b1 == 0b01110101: # JNZ: Jump if not equal/zero
            inc8 = ip_inc8(bytes)
            output.append(f"jnz {inc8}")
        
        elif b1 == 0b01110100: # JE: Jump if equal/zero
            inc8 = ip_inc8(bytes)
            output.append(f"je {inc8}")

        elif b1 == 0b01111100: # JL: Jump on less
            inc8 = ip_inc8(bytes)
            output.append(f"jl {inc8}")
        
        elif b1 == 0b01111110: # JLE: Jump on less or equal
            inc8 = ip_inc8(bytes)
            output.append(f"jle {inc8}")
        
        elif b1 == 0b01110010: # JB: Jump on below
            inc8 = ip_inc8(bytes)
            output.append(f"jb {inc8}")
        
        elif b1 == 0b01110110: # JBE: Jump on below or equal
            inc8 = ip_inc8(bytes)
            output.append(f"jbe {inc8}")
                                
        elif b1 == 0b01111010: # JP: Jump on parity
            inc8 = ip_inc8(bytes)
            output.append(f"jp {inc8}")
        
        elif b1 == 0b01110000: # JO: Jump on overflow
            inc8 = ip_inc8(bytes)
            output.append(f"jo {inc8}")
        
        elif b1 == 0b01111000: # JS: Jump on sign
            inc8 = ip_inc8(bytes)
            output.append(f"js {inc8}")
                    
        elif b1 == 0b01111101: # JNL: Jump on not less
            inc8 = ip_inc8(bytes)
            output.append(f"jnl {inc8}")
                    
        elif b1 == 0b01111111: # JG: Jump on greater
            inc8 = ip_inc8(bytes)
            output.append(f"jg {inc8}")
                    
        elif b1 == 0b01110011: # JNB: Jump on not below
            inc8 = ip_inc8(bytes)
            output.append(f"jnb {inc8}")
                    
        elif b1 == 0b01110111: # JA: Jump if above
            inc8 = ip_inc8(bytes)
            output.append(f"ja {inc8}")
                    
        elif b1 == 0b01111011: # JNP: Jump on not par
            inc8 = ip_inc8(bytes)
            output.append(f"jnp {inc8}")
            
        elif b1 == 0b01110001: # JNO: Jump on not overflow
            inc8 = ip_inc8(bytes)
            output.append(f"jno {inc8}")

        elif b1 == 0b01111001: # JNS: Jump on not sign
            inc8 = ip_inc8(bytes)
            output.append(f"jns {inc8}")

        elif b1 == 0b11100010: # Loop CX times
            inc8 = ip_inc8(bytes)
            output.append(f"loop {inc8}")

        elif b1 == 0b11100001: # Loop while zero
            inc8 = ip_inc8(bytes)
            output.append(f"loopz {inc8}")

        elif b1 == 0b11100000: # Loop while nonzero
            inc8 = ip_inc8(bytes)
            output.append(f"loopnz {inc8}")

        elif b1 == 0b11100011: # Jump on CX zero
            inc8 = ip_inc8(bytes)
            output.append(f"jcxz {inc8}")

                    
        else:
            print(f"Unknown instruction {b1:08b}")
            output.append(f"UNK {b1:08b}")
            bytes.pop(0)
    return output

def decode(file):
    with open(file, "rb") as source:
        data = source.read()
        return parse(bytearray(data))
            
