from decoder import decode

ROOT_FOLDER = "/home/michele/git/computer_enhance/perfaware/part1/"

for binFile in ["listing_0037_single_register_mov",
                "listing_0038_many_register_mov",
                "listing_0039_more_movs",
                "listing_0040_challenge_movs",
                "listing_0041_add_sub_cmp_jnz"]:
    print(f"binary: {binFile}")
    result = decode(ROOT_FOLDER + binFile)
    target = []
    with open(ROOT_FOLDER + binFile + ".asm", "r") as source:
        target = [line.strip() for line in source if line.strip()
                  and not line.startswith(";")]
    spaces = 30
    print(f"{'RES':<{spaces}}{'TARGET':<{spaces}}")
    for i in range(0, len(target)):
        wrong = result[i].replace(" ","") != target[i].replace("+ 0", "").replace(" ","")
        line_by_line = f"{result[i]:<{spaces}}{target[i]:<{spaces}}"
        print(f"\033[31m{line_by_line}\033[0m" if wrong else f"{line_by_line}")
    print()
