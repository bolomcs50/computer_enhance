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

def format_register_displacement(r_name, displacement):
    if not displacement:
        return f"[{r_name}]"
    elif displacement > 0:
        return f"[{r_name} + {displacement}]"
    return f"[{r_name} - {abs(displacement)}]"

def parse(bytes: bytearray):
    output = ["bits 16"]
    while len(bytes):
        b1 = bytes.pop(0)
        
        if b1 >> 2 == 0b100010: # Register/memory to/from register
            d = b1 >> 1 & 1
            w = b1 & 1
            b2 = bytes.pop(0)
            mod = b2 >> 6
            reg = b2 >> 3 & 0b111
            rm = b2 & 0b111
            reg_name = reg_to_name[w][reg]
            if mod == 0b11:
                rm_name = reg_to_name[w][rm]
                dest = reg_name if d else rm_name
                source = rm_name if d else reg_name
                output.append(f"mov {dest}, {source}")
            elif mod == 0b00 and rm == 0b110:
                value, bytes = int.from_bytes(bytes[:2], "little"), bytes[2:]
                dest = reg_name if d else value
                source = value if d else reg_name
                output.append(f"mov {dest}, [{source}]")
                continue
            else:
                displacement = None
                if mod == 0b01 or mod == 0b10:
                    disp_length = 1 if mod == 0b01 else 2
                    displacement, bytes = int.from_bytes(bytes[:disp_length], "little", signed=True), bytes[disp_length:]
                rm_name = format_register_displacement(rm_to_effective_address[rm], displacement)
                dest = reg_name if d else rm_name
                source = rm_name if d else reg_name
                output.append(f"mov {dest}, {source}")
                
        elif b1 >> 4 == 0b1011: # Immediate to register
            w = b1 >> 3 & 1
            reg = b1 & 0b111
            reg_name = reg_to_name[w][reg]
            arguments = f"{reg_name}, "
            data_bytes = 2 if w else 1
            value, bytes = int.from_bytes(bytes[:data_bytes], "little"), bytes[data_bytes:]
            arguments += str(value)
            output.append(f"mov {arguments}")
            
        elif b1 >> 1 == 0b1100011: # Immediate to register/memory
            w = b1 & 1
            b2 = bytes.pop(0)
            mod = b2 >> 6
            rm = b2 & 0b111
            displacement = None
            if (mod == 0b00 and rm == 0b110) or mod == 0b01 or mod == 0b10:
                disp_width = 1 if mod == 0b01 else 2
                displacement, bytes = int.from_bytes(bytes[:disp_width], "little", signed=True), bytes[disp_width:]
            data_width = 2 if w else 1
            value, bytes = int.from_bytes(bytes[:data_width], "little", signed=True), bytes[data_width:]
            rm_name = None
            instant_width = "word" if w else "byte"
            if mod == 0b11:
                rm_name = reg_to_name[w][rm]
                output.append(f"mov {rm_name}, {instant_width} {value}")
                continue
            else:
                rm_name = rm_to_effective_address[rm]
                rm_name = format_register_displacement(rm_name, displacement)
            output.append(f"mov {rm_name}, {instant_width} {value}")

        elif b1 >> 2 == 0b101000: # Memory to accumulator and accumulator to memory
            d = b1 >> 1 & 1
            w = b1 & 1
            width = 2 if w else 1
            addr, bytes = int.from_bytes(bytes[:width], "little"), bytes[width:]
            args = f"[{addr}], ax" if d else f"ax, [{addr}]"
            output.append(f"mov {args}")

        # elif b1 == 0b10001100: # Segment to register/memory

        else:
            print(f"Unknown instruction {b1:08b}")
            output.append(f"UNK {b1:08b}")
    return output

def decode(file):
    with open(file, "rb") as source:
        data = source.read()
        return parse(bytearray(data))
            
