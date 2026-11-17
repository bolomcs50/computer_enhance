# Read assembled Intel 8086 binaries and decode them to instructions
# https://edge.edx.org/c4x/BITSPilani/EEE231/asset/8086_family_Users_Manual_1_.pdf

reg_to_name_w = {
    0b000 : "ax",
    0b001 : "cx",
    0b010 : "dx",
    0b011 : "bx",
    0b100 : "sp",
    0b101 : "bp",
    0b110 : "si",
    0b111 : "di",
}

reg_to_name_now = {
    0b000 : "al",
    0b001 : "cl",
    0b010 : "dl",
    0b011 : "bl",
    0b100 : "ah",
    0b101 : "ch",
    0b110 : "dh",
    0b111 : "bh",
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

def parse(bytes: bytearray):
    output = ["bits 16"]
    while len(bytes):
        b1 = bytes.pop(0)
        if b1 >> 2 == 0b100010:
            d = b1 >> 1 & 1
            w = b1 & 1
            b2 = bytes.pop(0)
            mod = b2 >> 6
            reg = b2 >> 3 & 0b111
            rm = b2 & 0b111
            reg_name = reg_to_name_w[reg] if w else reg_to_name_now[reg]
            if mod == 0b11:
                rm_name = reg_to_name_w[rm] if w else reg_to_name_now[rm]
                dest = reg_name if d else rm_name
                source = rm_name if d else reg_name
                output.append(f"mov {dest}, {source}")
            elif mod == 0b00 and rm == 0b110:
                value, bytes = int.from_bytes(bytes[:2], "little"), bytes[2:]
                dest = reg_name if d else value
                source = value if d else reg_name
                output.append(f"mov {dest}, {source}")
                continue
            else:
                displacement = None
                if mod == 0b01:
                    displacement = bytes.pop(0)
                elif mod == 0b10:
                    displacement, bytes = int.from_bytes(bytes[:2], "little"), bytes[2:]
                rm_name = f"[{rm_to_effective_address[rm]} + {displacement}]" if displacement else f"[{rm_to_effective_address[rm]}]"
                dest = reg_name if d else rm_name
                source = rm_name if d else reg_name
                output.append(f"mov {dest}, {source}")
        elif b1 >> 4 == 0b1011:
            instruction = "mov "
            w = b1 >> 3 & 1
            reg = b1 & 0b111
            reg_name = reg_to_name_w[reg] if w else reg_to_name_now[reg]
            arguments = f"{reg_name}, "
            if w:
                value, bytes = int.from_bytes(bytes[:2], "little"), bytes[2:]
                arguments += str(value)
            else:
                d1 = bytes.pop(0)
                arguments += str(d1)
            output.append(instruction + arguments)
        else:
            if len(bytes):
                b2 = bytes.pop(0)
            print(f"Unknown instruction {b1:08b}")
            output.append(f"UNK {b1:08b}")
    return output

def decode(file):
    with open(file, "rb") as source:
        data = source.read()
        return parse(bytearray(data))
            
