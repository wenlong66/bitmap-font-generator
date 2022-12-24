# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_fnt (https://github.com/aillieo/bitmap-font-generator)
Fast and easy way to generate bitmap font with images
Created by Aillieo on 2017-09-06
With Python 3.5
"""

from functools import reduce
from PIL import Image
import os
import re

head = '<?xml version="1.0"?>\n<font>\n'
end = '</font>'

def getVStr(s):
    if type(s) == "int":
        return s
    else:
        return str(s)


def format_str(func):
    def wrapper(*args, **kw):
        ret = func(*args, **kw)
        ret = re.sub(r'[\(\)\{\}]', "", ret)
        ret = re.sub(r'\'(?P<name>\w+)\': ', "\g<name>=", ret)
        ret = re.sub(r', (?P<name>\w+)=', " \g<name>=", ret)
        ret = ret.replace("'", '"')
        return ret

    return wrapper


class FntConfig:
    def __init__(self):
        self.padding = (0,0,0,0)
        self.spacing = (1,1)
        self.info = {
            "face": "NA",
            "size": "32",
            "bold": "0",
            "italic": "0",
            "charset": "",
            "unicode": "1",
            "stretchH": "100",
            "smooth": "1",
            "aa": "1",
            "padding": str(self.padding),
            "spacing": str(self.spacing),
        }

        self.common = {
            "lineHeight": "32",
            "base": "26",
            "scaleW": "128",
            "scaleH": "128",
            "pages": "1",
            "packed": "0"
        }

        self.pages = {}

    @format_str
    def __str__(self):
        return '<info ' + str(self.info) + '/>\n<common ' + str(self.common) + '/>\n'


class CharDef:
    def __init__(self, id, file):
        self.file = file
        self.param = {
            "id": str(id),
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "xoffset": 0,
            "yoffset": 0,
            "xadvance": 0,
            "page": 0,
            "chnl": "15"
        }
        img = Image.open(self.file)
        self.ini_with_texture_size(img.size)

    @format_str
    def __str__(self):
        return '<char ' + str(self.param) + '/>'

    def ini_with_texture_size(self, size):
        padding = fnt_config.padding
        self.param["width"], self.param["height"] = str(size[0] + padding[1] + padding[3]), str(size[1] + padding[0] + padding[2])
        self.param["xadvance"] = str(size[0])
        self.param["xoffset"] = str(-padding[1])
        self.param["yoffset"] = str(-padding[0])

    def set_texture_position(self, position):
        self.param["x"], self.param["y"] = map(lambda v: str(v),position)

    def set_page(self, page_id):
        self.param["page"] = str(page_id)


class CharSet:
    def __init__(self):
        self.chars = []

    def __str__(self):
        ret = '<chars count="' + str(len(self.chars)) + '">\n'
        ret += reduce(lambda char1, char2: str(char1) + str(char2) + '\n', self.chars, "")
        ret += '</chars>\n'
        return ret

    def add_new_char(self, new_char):
        self.chars.append(new_char)

    def sort_for_texture(self):
        self.chars.sort(key=lambda char: char.param["width"], reverse=True)
        self.chars.sort(key=lambda char: char.param["height"], reverse=True)


class PageDef:
    def __init__(self, page_id, file):
        self.param = {
            "id": str(page_id),
            "file": file
        }

    @format_str
    def __str__(self):
        return '<pages> \n<page ' + str(self.param) + '/>\n</pages>'


class TextureMerger:
    def __init__(self, fnt_name):
        self.charset = CharSet()
        self.pages = []
        self.current_page_id = 0
        self.page_name_base = fnt_name

    def get_images(self):
        files = os.listdir('.')
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext == '.png':
                if len(name) == 1:
                    new_char = CharDef(ord(name), filename)
                    self.charset.add_new_char(new_char)
                elif name[0:2] == '__' and name[2:].isdigit():
                    new_char = CharDef(int(name[2:]), filename)
                    self.charset.add_new_char(new_char)
        self.charset.sort_for_texture()

    def save_page(self, texture_to_save):
        current_page_id = len(self.pages)
        file_name = self.page_name_base
        file_name += '_'
        file_name += str(current_page_id)
        file_name += '.png'
        try:
            texture_to_save.save(file_name, 'PNG')
            self.pages.append(PageDef(current_page_id, os.path.basename(file_name)))
        except IOError:
            print("IOError: save file failed: " + file_name)

    def next_page(self, texture_to_save):
        if texture_to_save:
            self.save_page(texture_to_save)
        texture_w, texture_h = int(fnt_config.common["scaleW"]), int(fnt_config.common["scaleH"])
        return Image.new('RGBA', (texture_w, texture_h), (0, 0, 0, 0))

    def gen_texture(self):
        self.get_images()
        texture = self.next_page(None)
        padding = fnt_config.padding
        spacing = fnt_config.spacing
        pos_x, pos_y, row_h = 0, 0, 0
        for char in self.charset.chars:
            img = Image.open(char.file)
            size_with_padding = (padding[1] + img.size[0] + padding[3], padding[0] + img.size[1] + padding[2])
            if row_h == 0:
                row_h = size_with_padding[1]
                if size_with_padding[0] > texture.size[0] or size_with_padding[1] > texture.size[1]:
                    raise ValueError('page has smaller size than a char')
            need_new_row = texture.size[0] - pos_x < size_with_padding[0]
            if need_new_row:
                need_new_page = texture.size[1] - pos_y < size_with_padding[1]
            else:
                need_new_page = False

            if need_new_page:
                texture = self.next_page(texture)
                pos_x, pos_y = 0, 0
                row_h = size_with_padding[1]
            elif need_new_row:
                pos_x = 0
                pos_y += row_h + spacing[1]
                row_h = size_with_padding[1]
            char.set_texture_position((pos_x, pos_y))
            texture.paste(img, (pos_x + padding[1], pos_y + padding[0]))
            pos_x += size_with_padding[0] + spacing[0]
            char.set_page(self.current_page_id)
        self.save_page(texture)

    def pages_to_str(self):
        return reduce(lambda page1, page2: str(page1) + str(page2) + "\n", self.pages, "")


class FntGenerator:
    def __init__(self, fnt_name):
        self.fnt_name = fnt_name
        self.textureMerger = TextureMerger(fnt_name)

    def gen_fnt(self):
        self.textureMerger.gen_texture()
        fnt_file_name = self.fnt_name + '.fnt'
        print(fnt_file_name)
        try:
            with open(fnt_file_name, 'w', encoding='utf8') as fnt:
                fnt.write(head)
                fnt.write(str(fnt_config))
                fnt.write(self.textureMerger.pages_to_str())
                fnt.write(str(self.textureMerger.charset))
                fnt.write(end)
            fnt.close()
        except IOError:
            print("IOError: save file failed: " + fnt_file_name)


if __name__ == '__main__':
    current_dir = os.path.abspath(".")
    os.chdir(current_dir)

    basename = os.path.basename(current_dir)
    
    fnt_config = FntConfig()
    full_path = current_dir
    cur_path = full_path.split('/')[-1]
    fnt_generator = FntGenerator(cur_path)
    fnt_generator.gen_fnt()
