from decoder import decode

ROOT_FOLDER = "/home/michele/git/computer_enhance/perfaware/part1/"

## simulating
for binFile in ["listing_0043_immediate_movs",
                "listing_0044_register_movs"]:
    print(f"binary: {binFile}")
    result = decode(ROOT_FOLDER + binFile)
    print("\n")