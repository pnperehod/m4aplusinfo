fuzzy_log = False

def logging(level):
    global fuzzy_log
    fuzzy_log = True if level > 2 else False


def fuzzy_compare(string1, string2):
    treshold = 3

    string_a = string1.lower() if len(string1) > len(string2) else string2.lower()  # static
    string_b = string2.lower() if len(string1) > len(string2) else string1.lower()  # slider
    length_a = len(string_a)
    length_b = len(string_b)
    zone_length = length_a + 2 * length_b
    zone = [string_a[i - length_b] if i > length_b - 1 and i < length_b + length_a else 0 for i in range(zone_length)]

    sums = []
    for shift in range(zone_length):
        sum = 0
        slider = [string_b[i - shift] if i >= shift and i < length_b + shift else 0 for i in range(zone_length)]
        for k in range(zone_length):
            if slider[k] == zone[k] and slider[k] != 0:
                sum = sum + 1
        sums.append(sum)

    total = 0
    for i in range(length_b, length_b + length_a):
        total = total + sums[i] if sums[i] > treshold else total
    if fuzzy_log:
        print(sums)
        print(f'<{string_a}|{string_b}> total: {total}  length: {length_a} corr={total * 100 / length_a}')
    return total * 100 / length_a
