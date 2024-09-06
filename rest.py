import re


title = "ultraviolet led lump like. it2"
title_words = re.findall(r'\b\w+\b', title.lower())

if "ultra".lower() in title_words:
    print("zalupa")
else:
    print(f"ne zalupa: {title_words}")

