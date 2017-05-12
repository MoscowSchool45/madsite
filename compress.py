#!/usr/bin/env python3

from Site import SiteHandler
import requests.exceptions
import requests
import tempfile
import subprocess
from PIL import Image
import io
import sys
import gettext
import os
import getpass
import argparse
import socket
import traceback

t = gettext.translation('default', os.path.join(os.path.dirname(__file__), 'locales'))
_ = t.gettext

argparse._ = _  # Is it an ugly hack, or is it how it's done? Not sure.

parser = argparse.ArgumentParser()
parser.add_argument("sitename", help="Имя сайта (например sch45uz)", type=str)
parser.add_argument("-a", "--admin", default=None, type=str,
                    help="Логин администратора (по умолчанию совпадает с именем сайта)")
parser.add_argument("-v", "--verbosity", action="count", default=0,
                    help="Выводить больше отладочной информации")
parser.add_argument("-g", "--ghostscript", default=None, help="Путь к ghostscript")
parser.add_argument("-p", "--password", default=None,
                    help="Пароль (будет запрошен в интерактивном режиме если не задать как аргумент)")
parser.add_argument("-A", "--all", default=False, action='store_true',
                    help="Обработать все тома")
parser.add_argument("-d", "--dump", default=None,
                    help="Создать список всех файлов вместо того чтобы их сжимать и сохранить их в файл")

parser.parse_args()

args = parser.parse_args()

dump_list = []

site_name = args.sitename
if args.admin is None:
    login = site_name
else:
    login = args.admin

print("Этот инструмент сжимает файлы на типовом сайте ОУ города Москвы.")
print("Данный процесс называют «чиска диского пространства» (орфография сохранена)")
print()
print("Мы будем скачивать файлы .pdf и картинки, пыаться сжать их размер (с потерей качества).")
print("Если выйдет что результат меньше оригинала - будем заливать обратно под тем же именем.")
print("Для справки по дополнительным ключам запуска выполните {} -h".format(sys.argv[0]))
print()

if args.ghostscript is None:
    # Try to find ghostscript
    try:
        gs = subprocess.check_output(["which", "gs"]).decode().strip()
    except subprocess.CalledProcessError:
        print("Не удалось найти ghostscript. Укажите путь к ghostscript с помощью ключа -g.")
        exit(2)
    if args.verbosity > 0:
        print("Удалось найти ghostscript: {}.".format(gs))
    args.ghostscript = gs
if not os.path.isfile(args.ghostscript):
    print("{} не является файлом.".format(args.ghostscript))
    exit(1)

try:
    site_ip = socket.gethostbyname("{}.mskobr.ru".format(site_name))
except socket.gaierror:
    print("Не удалось распознать домен {}.mskobr.ru. Проверьте подключение к интеренту и доменное имя.".
          format(site_name))
    exit(3)

if args.verbosity > 0:
    print("{}.mskobr.ru -> {}".format(site_name, site_ip))

if args.password is None:
    print("Введите пароль от пользователя {} на {}.mskobr.ru".format(login, site_name))
    args.password = getpass.getpass()

site = SiteHandler(login, args.password, '{}.mskobr.ru'.format(site_name), timeout=600)

dirs = site.list_directories()

print("Найдены следующие тома:")
n=0
hashes = []
for d in dirs:
    hashes.append(d['hash'])
    print("{}:\t{}".format(n+1, d['name']))
    print(d)
    n=n+1

process = []
if args.all:
    print("Обрабатываем все.")
    process = hashes
else:
    good = False
    while not good:
        print("Введите список томов для обработки (номера разделенные пробелами, например «1 2 13»)")
        request = input().strip().split()
        good = True
        process = []
        for r in request:
            try:
                process.append(hashes[int(r)-1])
            except ValueError:
                print("{} не число".format(r))
                good = False
            except IndexError:
                print("{} не входит в диапазон 1..{}".format(r, len(hashes)))
                good = False

process = list(set(process))

if args.verbosity > 0:
    print("Обрабатываем тома со следующими хешами: {}".format(", ".join(process)))


def list_dir(name, is_hash = False, handler=None, path=[]):
    size = 0
    dirs = []
    result = site.read_file_dir(name, is_hash = is_hash)
    #print(result)
    if 'files' not in result:
        return 0
    if 'cwd' in result and 'name' in result['cwd']:
        localpath = path + [result['cwd']['name']]
    else:
        localpath = path + [name]

    list = result['files']
    for file in sorted(list, key = lambda x: int(x['size']) if x['size'] != 'unknown' else 0):
        if file['size'] == 'unknown':
            print("???\t{}".format(file['name']))
        else:
            print("{:09d}\t{}".format(int(file['size']), file['name']))
        size = size + int(file['size']) if file['size'] != 'unknown' else 0
        if file['mime'] == 'directory':
            dirs.append( (file['name'], file['hash']) )
        if handler is not None:
            handler(file, localpath)
    print("Всего: {} байт ({} GiB)".format(size, int(size / 1024 / 1024) / 1024))
    for dir, hash in dirs:
        print("\nКаталог: {} ({})".format(dir, hash))
        good = False
        fails = 0
        while not good and fails < 10:
            try:
                size = size + list_dir(hash, is_hash=True, handler=handler, path=localpath)
                good = True
            except Exception as e:
                fails += 1
        if fails == 10:
            print("Слишком много ошибок для {}, пропускаем".format(dir))

    print("Всего,с подкаталогами: {} байт ({} GiB)".format(size, int(size / 1024 / 1024) / 1024))
    return size


def handler(file, path):
    imagehandler(file, path)
    pdfhandler(file, path)


def imagehandler(file, path):
    if file['mime'] in ['image/jpeg', 'image/png']:
        localpath = "/".join(path + [file['name']])
        if args.verbosity > 0:
            print("Картинка, размер: {}".format(file['size']))
        r = requests.get("{}://{}/{}".format("http", site.site, localpath))
        if args.verbosity > 0:
            print("Скачано:          {}".format(len(r.content)))
        original = r.content
        image_bytes = io.BytesIO()
        image_bytes.write(r.content)
        try:
            image_object = Image.open(image_bytes)
        except OSError:  # Cannot identify image
            print("Не могу открыть картинку.")
            return
        image_object.thumbnail((800, 800))

        new_image_bytes = io.BytesIO()
        if file['mime'] == 'image/jpeg':
            image_object.save(new_image_bytes, format='JPEG')
        elif file['mime'] == 'image/png':
            image_object.save(new_image_bytes, format='PNG')
        else:
            print("Непонятный формат картинки {}".format(file['mime']))
            return
        converted_size = len(new_image_bytes.getvalue())
        if args.verbosity > 0:
            print("После сжатия:     {}".format(converted_size))
        if converted_size < int(file['size']):
            print("Сжатие успешно ({}%).".format(100*converted_size//len(r.content)))
            site.replace_file(file, new_image_bytes.getvalue(), r.content, args.verbosity)


def pdfhandler(file, path):
    if file['mime'] == 'application/pdf':
        localpath = "/".join(path + [file['name']])
        print(localpath)
        if args.verbosity > 0:
            print("PDF, размером: {}".format(file['size']))
        r = requests.get("{}://{}/{}".format("http", site.site, localpath))
        if args.verbosity > 0:
            print("Скачано:       {}".format(len(r.content)))
        tmp = tempfile.NamedTemporaryFile()
        tmp.write(r.content)
        tmp.flush()
        fname = tmp.name
        cname = fname + ".c.pdf"
        result = subprocess.run([args.ghostscript, '-sDEVICE=pdfwrite',
                                          '-dCompatibilityLevel=1.4', '-dPDFSETTINGS=/screen ',
                                          '-dNOPAUSE', '-dQUIET', '-dBATCH', '-dDetectDuplicateImages',
                                          '-dCompressFonts=true', '-r150', '-sOutputFile={}.c.pdf'.format(fname),
                                          fname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode

        tmp.close()
        new = open(cname, 'rb')
        converted = new.read()
        if args.verbosity > 0:
            print("Сжато:         {}".format(len(converted)))
        if result != 0:
            print("Ошибка сжатия.")
        elif len(converted) < int(file['size']):
            print("Сжатие успешно (файл: {})".format(cname))
            site.replace_file(file, converted, r.content, args.verbosity)
        else:
            print("Сжатие безуспешно")
        subprocess.run(['/bin/rm', cname])


def dumphandler(file, path):
    global dump_list
    localpath = "/".join(path + [file['name']])
    if not localpath in dump_list:
        dump_list.append(localpath)


for dir in process:
    if args.dump:
        list_dir(dir, handler=dumphandler, is_hash=True)
        with open(args.dump, 'w') as dumpfile:
            dumpfile.write("\n".join(dump_list) + "\n")
    else:
        list_dir(dir, handler=handler, is_hash=True)
exit();