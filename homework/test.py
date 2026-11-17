from decoder import decode

ROOT_FOLDER = "/home/michele/git/computer_enhance/perfaware/part1/"

for binFile in ["listing_0037_single_register_mov",
                "listing_0038_many_register_mov",
                "listing_0039_more_movs",
                "listing_0040_challenge_movs"]:
    print(f"binary: {binFile}")
    result = decode(ROOT_FOLDER + binFile)
    target = []
    with open(ROOT_FOLDER + binFile + ".asm", "r") as source:
        target = [line.strip() for line in source if line.strip()
                  and not line.startswith(";")]
    spaces = 25
    print(f"{'RES':<{spaces}}{'TARGET':<{spaces}}")
    for i in range(0, len(target)):
        wrong = result[i] != target[i]
        line_by_line = f"{result[i]:<{spaces}}{target[i]:<{spaces}}"
        print(f"\033[31m{line_by_line}\033[0m" if wrong else f"{line_by_line}")
    print()
