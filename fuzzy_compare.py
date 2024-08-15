
single_test = False
test_number = 0
treshold = 3
fuzzy_log = False

tests = [
    ['al di meola', 'al di meola'],                          # 0
    ['Al di Meola', 'Al DiMeola'],                           # 1
    ['Paul Mccartney', 'John Lennon'],                       # 2
    ['Larry Carlton & Lee Ritenour', 'Lee Ritenour'],        # 3
    ['Allan Holdsworth', 'Allan Holsdworth'],                # 4
    ["It's My Life", "It's My Life -"],                      # 5
    ['Steve Hackett', 'Hackett, Steve'],                     # 6
    ['Steve Hackett', 'steve Hillage'],                      # 7
    ['F R David', 'F.R. David'],                             # 8
    ['Church of the poison mind', 'curch of the poison mind'],   # 9
    ['mm-mm good', 'mm mm good'],                                  # 10
    ['I could not ask for more', 'for the love of you'],             # 11
    ['peter white', 'peter green']                                      # 12
]
def logging(level):
    global fuzzy_log
    fuzzy_log = True if level > 2 else False

def only_alnum(string):
    str_out = ''.join([s for s in string if s.isalnum()])
    return str_out


def fuzzy_compare(string1, string2):
    string_1 = only_alnum(string1)
    string_2 = only_alnum(string2)
    string_a = string_1 if len(string_1) > len(string_2) else string_2      # string_a  - longest
    string_b = string_2 if len(string_1) > len(string_2) else string_1
    string_a = string_a.lower()
    string_b = string_b.lower()
    length_a = len(string_a)        # static
    length_b = len(string_b)        # sliding
    zone_length = length_a + 2 * length_b
    zone = [string_a[i - length_b] if i > length_b -1 and i < length_b + length_a else 0 for i in range(zone_length)]
    sums = list()
    for shift in range(zone_length):
        sum = 0
        slider = [string_b[i - shift] if i >= shift and i <length_b + shift else 0 for i in range(zone_length)]
        for k in range(zone_length):
            if slider[k] == zone[k] and slider[k] != 0:
                sum = sum + 1
        sums.append(sum)

    total = 0
    for i in range(length_b, length_b + length_a):
        total = total + sums[i] if sums[i] > treshold else total
    if fuzzy_log:
        print(sums)
        print(f'<{string_a}|{string_b}>total: {total} length: {length_a} correlation={total * 100 / length_a}')
    return total * 100 / length_a


def main():
    if single_test:
        corr = fuzzy_compare(tests[test_number][0], tests[test_number][1])
        print(f'correlation = {corr}')
    else:
        for test in tests:
            corr = fuzzy_compare(test[0], test[1])
            print(f'------{test[0]} :: {test[1]} correlation = {corr}')


if __name__ == '__main__':
    main()
