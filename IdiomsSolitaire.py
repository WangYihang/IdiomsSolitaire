#!/usr/bin/env python
# encoding:utf-8

from pypinyin import pinyin, lazy_pinyin, Style
import random
import sys

data = []

def get_pinyin(word):
    result = []
    for i in word:
        for j in pinyin(i, style=Style.NORMAL):
            result.append(j[0])
    return result

def get_all_starts_with(letter):
    result = []
    target_pinyin = get_pinyin(letter)
    target_pinyin_first = target_pinyin[-1]
    for i in data:
        data_word = i[0]
        data_pinyin = i[1]
        data_meaning = i[2]
        data_pinyin_first = data_pinyin[0]
        if data_pinyin_first == target_pinyin_first:
            result.append([data_word, data_meaning])
    return result


def get_random_result(data):
    return random.choice(data)

def format_data(data):
    return "[%s] : [%s]" % (data[0], data[1])

def init():
    with open("data.txt", "r") as f:
        counter = 0
        for line in f:
            content = line.split("\t")
            word = content[0]
            pinyin = content[1].split("'")
            meaning = content[2].replace("\n", "")
            data.append([word, pinyin, meaning])
            counter += 1
        print("[+] Init finished! [%d] words." % (counter))

def guess(word):
    all_data_matched = get_all_starts_with(word)
    result_data = format_data(get_random_result(all_data_matched))
    return result_data

def main():
    if len(sys.argv) != 2:
        print("Usage : ")
        print("        python IdiomsSolitaire.py [Idioms]")
        print("Example : ")
        print("        python IdiomsSolitaire.py '一心一意'")
        print("Author : ")
        print("        WangYihang <wangyihanger@gmail.com>")
        exit(1)

    word = sys.argv[1]
    init()
    all_data_matched = get_all_starts_with(word)
    result_data = format_data(get_random_result(all_data_matched))
    print(result_data)

if __name__ == "__main__":
    main()
