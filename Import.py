from Site import Teacher
import xlrd
import re
import datetime


def normalize_name(name):
    components = re.split("\s+", name)
    return " ".join(components)


class Directory(object):
    def teacher_for_name(self, name):
        raise NotImplementedError()


class OneAssEducationDirectory(Directory):
    high = 'Высшее'
    mid = 'Среднее'
    def __init__(self, filename):
        self.book = xlrd.open_workbook(filename, formatting_info=True)
        self.sheet = self.book.sheet_by_index(0)
        self.directory = {}
        current = {'teacher': None}
        current_type = None
        all = {}
        for row_index in range(13, self.sheet.nrows):
            #style = self.sheet.cell(row_index)
            cell = self.sheet.cell(row_index, 0)
            fmt = self.book.xf_list[cell.xf_index]
            indent = fmt.alignment.indent_level
            if indent == 2:
                if current['teacher'] is not None:
                    all[current['teacher']] = current
                    current = {'teacher': normalize_name(cell.value)}
                else:
                    current = {'teacher': normalize_name(cell.value)}
            if indent == 4:
                current_type = cell.value
                spec = self.sheet.cell(row_index, 10).value
                qual = self.sheet.cell(row_index, 11).value
                current[current_type] = (spec, qual)
        all[current['teacher']] = current
        self.all = all

    def teacher_for_name(self, name):
        name = normalize_name(name)
        if name not in self.all:
            name_components = re.split("\s+", name)
            if len(name_components) == 3:
                name = ' '.join([name_components[-1], name_components[0], name_components[1]])
                if name not in self.all:
                    return (None, None, None)
            else:
                return (None, None, None)
        teacher = self.all[name]
        for key in teacher:
            if OneAssEducationDirectory.high in key:
                return (key, teacher[key][0], teacher[key][1])
        for key in teacher:
            if OneAssEducationDirectory.mid in key:
                return (key, teacher[key][0], teacher[key][1])
        return (None, None, None)

class OneAssServiceRecordDirectory(Directory):
    all_key = 'Общий стаж'
    current_key = 'Педагогический стаж'
    def __init__(self, filename):
        self.book = xlrd.open_workbook(filename, formatting_info=True)
        self.sheet = self.book.sheet_by_index(0)
        self.directory = {}
        current = {'teacher': None}
        current_type = None
        all = {}
        for row_index in range(12, self.sheet.nrows):
            #style = self.sheet.cell(row_index)
            cell = self.sheet.cell(row_index, 0)
            fmt = self.book.xf_list[cell.xf_index]
            indent = fmt.alignment.indent_level
            if indent == 2:
                if current['teacher'] is not None:
                    all[current['teacher']] = current
                    current = {'teacher': normalize_name(cell.value)}
                else:
                    current = {'teacher': normalize_name(cell.value)}
            if indent == 4:
                current_type = cell.value
                years = self.sheet.cell(row_index, 2).value
                months = self.sheet.cell(row_index, 4).value
                days = self.sheet.cell(row_index, 6).value
                current[current_type] = (years, months, days)
        all[current['teacher']] = current
        self.all = all

    def teacher_for_name(self, name):
        name = normalize_name(name)
        if name not in self.all:
            name_components = re.split("\s+", name)
            if len(name_components) == 3:
                name = ' '.join([name_components[-1], name_components[0], name_components[1]])
                if name not in self.all:
                    return (None, None)
            else:
                return (None, None)
        general = self.all[name][OneAssServiceRecordDirectory.all_key] \
            if OneAssServiceRecordDirectory.all_key in self.all[name] else (None, None, None)
        current = self.all[name][OneAssServiceRecordDirectory.current_key] \
            if OneAssServiceRecordDirectory.current_key in self.all[name] else (None, None, None)
        return (general[0], current[0])
