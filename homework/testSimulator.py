from decoder import decode

ROOT_FOLDER = "/home/michele/git/computer_enhance/perfaware/part1/"

## simulating
for binFile in ["listing_0043_immediate_movs",
                "listing_0044_register_movs",
                "listing_0046_add_sub_cmp",
                "listing_0048_ip_register",
                "listing_0049_conditional_jumps",
                "listing_0051_memory_mov",
                "listing_0056_estimating_cycles"]:
    print(f"binary: {binFile}")
    result = decode(ROOT_FOLDER + binFile)
    print("\n")
