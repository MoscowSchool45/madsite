from Site import SiteHandler
from Import import OneAssServiceRecordDirectory, OneAssEducationDirectory
import re
import requests.exceptions
import xml.etree.ElementTree
import socket


def download_or_else(function, *args, **kwargs):
    okay = False
    while not okay:
        try:
            result = function(*args, **kwargs)
            okay = True
        except (requests.exceptions.ReadTimeout, xml.etree.ElementTree.ParseError):
            # retry
            pass
    return result # noinspection


def format_years(years):
    if years is None:
        return "?"
    years = int(years)
    last = str(years)[-1]
    if last == '1':
        if years in [11]:
            return "{} лет".format(years)
        else:
            return "{} год".format(years)
    elif last in ['2', '3', '4']:
        if years in [12, 13, 14]:
            return "{} лет".format(years)
        else:
            return "{} года".format(years)
    else:
        return "{} лет".format(years)


def fix_education(dir, site, divisions, pretend=False):
    n = 0
    m = 0
    missing = []
    for division in divisions:
        collections = download_or_else(site.get_teacher_collections, division)
        for c, c_name in collections:
            print(c_name)
            teachers = download_or_else(site.get_teachers_in_collection, division, c)
            for t, t_name in teachers:
                n = n + 1
                print(t_name)
                edu, spec, qual = dir.teacher_for_name(t_name)
                if edu is None:
                    print("Info missing in directory")
                    m = m + 1
                    missing.append(t_name)
                    continue
                got = False
                while not got:
                    try:
                        teacher = site.get_teacher_details(t)
                        got = True
                    except (requests.exceptions.ReadTimeout, xml.etree.ElementTree.ParseError):
                        "Timeout, retry getting"

                teacher.values["education"] = edu
                if spec:
                    teacher.values["specialty"] = "{} (Квалификация: {})".format(spec, qual) if qual is not None else spec
                elif qual:
                    teacher.values["specialty"] = "Квалификация: {}".format(qual)
                print(teacher.values["education"], teacher.values["specialty"])
                saved = pretend
                while not saved:
                    try:
                        site.save_object(teacher)
                        saved = True
                    except requests.exceptions.ReadTimeout:
                        "Timeout, retry saving"

    print("Education")
    print("{} teachers, {} missing".format(n, m))
    print("Missing: {}".format("\n".join(missing)))
    return (n, m, missing)


def fix_experience(dir, site, divisions, pretend=False):
    n = 0
    m = 0
    missing = []
    for division in divisions:
        collections = download_or_else(site.get_teacher_collections, division)
        for c, c_name in collections:
            print(c_name)
            teachers = download_or_else(site.get_teachers_in_collection, division, c)
            for t, t_name in teachers:
                n=n+1
                print(t_name)
                general, current = dir.teacher_for_name(t_name)
                if general is None and current is None:
                    print("Info missing in directory")
                    m=m+1
                    missing.append(t_name)
                    continue
                got = False
                while not got:
                    try:
                        teacher = site.get_teacher_details(t)
                        got = True
                    except (requests.exceptions.ReadTimeout, xml.etree.ElementTree.ParseError):
                        "Timeout, retry getting"

                teacher.values["length_of_work"] = format_years(general)
                teacher.values["length_of_specialty"] = format_years(current)
                print(teacher.values["length_of_work"], teacher.values["length_of_specialty"])
                saved = pretend
                while not saved:
                    try:
                        site.save_object(teacher)
                        saved = True
                    except (requests.exceptions.ReadTimeout, socket.timeout):
                        "Timeout, retry saving"

    print("Experience")
    print("{} teachers, {} missing".format(n,m))
    print("Missing: {}".format("\n".join(missing)))
    return (n, m, missing)
