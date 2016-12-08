from Site import SiteHandler
from Import import OneAssServiceRecordDirectory, OneAssEducationDirectory
import re
import requests.exceptions
from functions import format_years, fix_education, fix_experience
import json
import requests
import tempfile
import subprocess
from PIL import Image
import io

site = SiteHandler('sch45uz', '??????', 'sch45uz.mskobr.ru', timeout=600)

#with open("/Users/koval/converted.png", 'rb') as f:
#    content = f.read()
#    site.upload_file_new('test.png', content, 'lfiles_Lw')

#site.delete_file_by_hash("lfiles_dGVzdC5wbmc")



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
    print("Total: {} bytes ({} GiB)".format(size, int(size / 1024 / 1024) / 1024))
    for dir, hash in dirs:
        print("\nSubdirectory: {} ({})".format(dir, hash))
        good = False
        fails = 0
        while not good and fails < 10:
            try:
                size = size + list_dir(hash, is_hash=True, handler=handler, path=localpath)
                good = True
            except Exception as e:
                fails += 1
        if fails == 10:
            print("Too much errors for {}, giving up on this one".format(dir))

    print("Total, with subdirectories: {} bytes ({} GiB)".format(size, int(size / 1024 / 1024) / 1024))
    return size


def testhandler(file, path):
    imagehandler(file, path)
    pdfhandler(file, path)


def imagehandler(file, path):
    if file['mime'] in ['image/jpeg', 'image/png']:
        localpath = "/".join(path + [file['name']])
        print("Image, size: {}".format(file['size']))
        r = requests.get("{}://{}/{}".format("http", site.site, localpath))
        print("Downloaded   {}".format(len(r.content)))
        image_bytes = io.BytesIO()
        image_bytes.write(r.content)
        try:
            image_object = Image.open(image_bytes)
        except OSError:  # Cannot identify image
            print("Can't open image")
            return
        image_object.thumbnail((1024, 1024))

        new_image_bytes = io.BytesIO()
        if file['mime'] == 'image/jpeg':
            image_object.save(new_image_bytes, format='JPEG')
        elif file['mime'] == 'image/png':
            image_object.save(new_image_bytes, format='PNG')
        else:
            print("Can't save image")
            return
        converted_size = len(new_image_bytes.getvalue())
        print("Converted    {}".format(converted_size))
        if converted_size < int(file['size']):
            print("Conversion successful")
            print("Delete old file from site ({})".format(localpath))
            site.delete_file_by_hash(file['hash'])
            print("Upload new file to site (tagret={})".format(file['phash']))
            site.upload_file_new(file['name'], new_image_bytes.getvalue(), file['phash'])
        else:
            print("Conversion unsuccessful")


def pdfhandler(file, path):
    if file['mime'] == 'application/pdf':
        localpath = "/".join(path + [file['name']])
        print(localpath)
        print("PDF, size: {}".format(file['size']))
        r = requests.get("{}://{}/{}".format("http", site.site, localpath))
        print("Downloaded {}".format(len(r.content)))
        tmp = tempfile.NamedTemporaryFile()
        tmp.write(r.content)
        tmp.flush()
        fname = tmp.name
        cname = fname + ".c.pdf"
        result = subprocess.run(['/usr/local/bin/gs', '-sDEVICE=pdfwrite',
                                          '-dCompatibilityLevel=1.4', '-dPDFSETTINGS=/screen ',
                                          '-dNOPAUSE', '-dQUIET', '-dBATCH', '-dDetectDuplicateImages',
                                          '-dCompressFonts=true', '-r150', '-sOutputFile={}.c.pdf'.format(fname),
                                          fname], stderr=subprocess.DEVNULL).returncode

        tmp.close()
        new = open(cname, 'rb')
        converted = new.read()
        print("Converted: {}".format(len(converted)))
        if result != 0:
            print("Conversion error. Won't touch.")
        elif len(converted) < int(file['size']):
            print("Conversion successful (filename={})".format(cname))
            print("Delete old file from site ({})".format(localpath))
            site.delete_file_by_hash(file['hash'])
            print("Upload new file to site (tagret={})".format(file['phash']))
            site.upload_file_new(file['name'], converted, file['phash'])
            #exit()
        else:
            print("Conversion unsuccessful")
        subprocess.run(['/bin/rm', cname])



list_dir('files', handler=testhandler)

exit();

#print(1415525122 - 1235692466)

dir = OneAssServiceRecordDirectory("staj_sotrudnikov.xls")
dir2 = OneAssEducationDirectory("obrazovanie_sotrudnikov.xls")

divisions = site.get_divisions()


n1, m1, l1 = fix_experience(dir, site, divisions, pretend=True)
n2, m2, l2 = fix_education(dir2, site, divisions, pretend=True)

missing = set(l1+l2)

print("Total missing:\n\n")
for m in missing:
    print(m)

