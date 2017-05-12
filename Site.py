#!/usr/bin/env python3
import requests
import json
import mimetypes
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import os.path
import traceback


class Fieldset(object):
    fields = None

    def __init__(self, xml=None):
        if type(self).fields is None:
            raise Exception("Please subclass Fieldset and define one or more fields")
        self.values = {}
        for field in type(self).fields:
            self.values[field] = None
        self.obj_id = None
        self.parent_id = None
        self.type_id = None
        if xml is not None:
            self.load_xml(xml)

    def load_xml(self, xml):
        root = ET.fromstring(xml)
        for child in root:
            if child.tag == 'field':
                self.values[child.attrib['name']] = child.text
            elif child.tag == 'object_id':
                self.obj_id = child.text
            elif child.tag == 'parent_id':
                self.parent_id = child.text
            elif child.tag == 'object_type_id':
                self.type_id = child.text

    def __str__(self):
        result = str(self.obj_id) + ", parent = " + str(self.parent_id)
        for f in type(self).fields:
            result += "\n{}:{}".format(f, self.values[f])
        return result

    def form(self):
        data = {}
        id = self.obj_id if self.obj_id is not None else "new"
        for field in type(self).fields:
            if self.values[field] is not None:
                data["data[{}][{}]".format(id, field)] = self.values[field]
        data['parent_id'] = self.parent_id
        return(data)


class Teacher(Fieldset):
    fields = [
        "anons_pic",
        "is_unindexed",
        "h1",
        "post",
        "disciplines",
        "branch_name",
        "branch",
        "work_fact",
        "education",
        "college",
        "specialty",
        "length_of_work",
        "length_of_specialty",
        "degree",
        "skill",
        "category",
        "experience",
        "awards",
        "email",
        "phone",
        "skype",
        "personal_page",
        "blog",
        "content",
    ]


class SiteTree():
    def __init__(self, site, timeout=10, dump=None):
        self.timeout = timeout
        self.site = site
        self.seen = []
        self.dump = dump

    def process_url(self, url, referer):
        if url.strip() == '':
            return None
        else:
            url = url.strip()
        p = urlparse(url)
        if p.scheme not in ['','http', 'https']:
            return None
        if p.netloc == '' or p.netloc == self.site:
            if len(p.path) == 0:
                return None
            if p.path[0] == '/':
                return p.path
            else:
                parent = urlparse(referer)
                location = os.path.split(parent.netloc)
                if len(parent.netloc) > 0 and parent.netloc[-1] != '/':
                    location = location[:-1]
                path = os.path.join(*location, p.path)
                return path
        else:
            return None

    def process_page(self, page, rec=0, max=20):
        r = requests.get("{}://{}/{}".format("http", self.site, page), timeout=self.timeout)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = []
        for a in soup.findAll("a"):
            try:
                link = self.process_url(a['href'], page)
                if link is not None:
                    links.append(link)
            except KeyError as e:
                pass
        for img in soup.findAll("img"):
            try:
                link = self.process_url(img['src'], page)
                if link is not None:
                    links.append(link)
            except KeyError as e:
                pass
        self.seen.append(page)
        unseen = []
        for link in links:
            if not link in self.seen:
                unseen.append(link)
                if self.dump is not None:
                    self.dump.write("{}\n".format(link))
                    self.dump.flush()
        print("Processed {} at level {}. Found {} links, {} unseen.".format(page, rec, len(links), len(unseen)))
        if rec > max:
            return links
        for link in unseen:
            self.process_page(link, rec+1, max)
        return links


class SiteHandler():
    def __init__(self, login, password, site, timeout = 10):
        self.timeout = timeout
        self.site = site
        r = requests.get("{}://{}/{}".format("http", site, ""), timeout=self.timeout)
        self.cookies = r.cookies
        r = requests.post("{}://{}/{}".format("http", site, "users/login_do/"), data={'login':login, 'password':password, 'json':1}, cookies = self.cookies, timeout=self.timeout)
        try:
            if json.loads(r.text)['result'] != 'success':
                raise ValueError("Authentication failed")
        except ValueError as e:
            raise ValueError("Authentication failed")


    def upload_image(self, filename, file):
        print("Uploading image {}".format(filename))
        r = requests.post(
            "{}://{}/{}".format("http", self.site, 'js/ckeditor/kcfinder/upload.php?type=images&CKEditor=editor_content&CKEditorFuncNum=1&langCode=ru'),
            files={'upload': (filename, file, 'image/png', {'Expires': '0'})}, cookies = self.cookies, timeout=self.timeout
        )

    def upload_file(self, filename, file):
        print("Uploading file {}".format(filename))
        r = requests.post(
            "{}://{}/{}".format("http", self.site, 'js/ckeditor/kcfinder/upload.php?type=files&CKEditor=editor_content&CKEditorFuncNum=1&langCode=ru'),
            files={'upload': (filename, file, mimetypes.guess_type(filename), {'Expires': '0'})}, cookies = self.cookies, timeout=self.timeout
        )

    def upload_file_new(self, filename, file, parent_hash):
        print("Uploading file {}".format(filename))
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/admin/data/elfinder_connector/'),
            data={'cmd': 'upload', 'target': parent_hash, 'water_mark': 0},
            files={'upload[]': (filename, file, mimetypes.guess_type(filename), {'Expires': '0'})}, cookies=self.cookies,
            timeout=self.timeout
        )

    def list_directories(self):
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/admin/data/elfinder_connector/'),
            data={'water_mark': 0, 'cmd': 'open', 'target': '', 'init':1, 'tree': 1}, cookies=self.cookies, timeout=self.timeout
        )
        # print(r.text)
        result = json.loads(r.text)
        if not 'files' in result:
            print(result.keys())
            return []
        return [x for x in result['files'] if 'volumeid' in x]

    def read_file_dir(self, dir, is_hash=False):
        if is_hash:
            hash = dir
        else:
            hash = 'l{}_Lw'.format(dir)
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/admin/data/elfinder_connector/'),
            data={'water_mark':0, 'cmd':'open', 'target':hash}, cookies = self.cookies, timeout=self.timeout
        )
        #print(r.text)
        return json.loads(r.text)

    def search_file_dir(self, dir, query):
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/admin/data/elfinder_connector/'),
            data={'water_mark':0, 'cmd':'search', 'q': query,'target':'l{}_Lw'.format(dir)}, cookies = self.cookies, timeout=self.timeout
        )
        return json.loads(r.text)

    def delete_file_by_hash(self, hash):
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/admin/data/elfinder_connector/'),
            data={'water_mark':0, 'cmd':'rm', 'targets[]': hash}, cookies = self.cookies, timeout=self.timeout
        )

    def save_object(self, object):
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/data/saveObject/'),
            data = object.form(), cookies = self.cookies, timeout=self.timeout
        )
        #print(r.text)

    def add_teacher(self, parent, name, post, disciplines, branch_name, branch, address, education, speciality, experience, experience_qualifying):
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/data/addObject/901/'),
            data={
                'data[new][h1]': name,
                'data[new][post]': post,
                'data[new][disciplines]': disciplines,
                'data[new][branch_name]': branch_name,
                'data[new][branch]': branch,
                'data[new][work_fact]': address,
                'data[new][education]': education,
                'data[new][specialty]': speciality,
                'data[new][length_of_work]': experience,
                'data[new][length_of_specialty]':experience_qualifying,
                'parent_id': parent,
            }
        )

    def save_teacher(self, id, parent, name, post, disciplines, branch, address, education, speciality, experience, experience_qualifying):
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/data/saveObject/'),
            data={
                'data[{}][h1]'.format(id): name,
                'data[{}][post]'.format(id): post,
                'data[{}][disciplines]'.format(id): disciplines,
                'data[{}][branch_name]'.format(id): branch,
                'data[{}][branch]'.format(id): address,
                'data[{}][work_fact]'.format(id): address,
                'data[{}][education]'.format(id): education,
                'data[{}][specialty]'.format(id): speciality,
                'data[{}][length_of_work]'.format(id): experience,
                'data[{}][length_of_specialty]'.format(id):experience_qualifying,
                'parent_id': parent,
            }
        )

    def add_department(self, parent, name):
        r = requests.post(
            "{}://{}/{}".format("http", self.site, '/data/addObject/900/'),
            data={
                'data[new][h1]': name,
                'parent_id': parent,
            }
        )

    def get_divisions(self):
        r = requests.get(
            "{}://{}/{}".format("http", self.site, '/info_edu/staff/'), cookies = self.cookies,
        )
        soup = BeautifulSoup(r.text, 'html.parser')
        hrefs = soup.findAll("a", {"target" : "_blank"})
        results = []
        for href in hrefs:
            if '/obwie_svedeniya/pedagogicheskij_kollektiv/' in href['href']:
                results.append(href['href'][:-len('/obwie_svedeniya/pedagogicheskij_kollektiv/')])

        return results

    def get_teacher_collections(self, division):
        if division is None:
            url = "{}://{}/{}".format("http", self.site, '/info_edu/staff/')
        else:
            url = "{}://{}/{}/{}".format("http", self.site, division, 'obwie_svedeniya/pedagogicheskij_kollektiv/')
        r = requests.get(url, cookies = self.cookies, timeout=self.timeout)
        soup = BeautifulSoup(r.text, 'html.parser')
        hrefs = soup.findAll("a", {"role": "button", 'class': 'subjecttitle'})
        results = []
        for href in hrefs:
            id = href.findNext()['data-id']
            name = href.text
            if id is not None:
                results.append((id,name))

        return results

    def get_teachers_in_collection(self, division, collection_id):
        if division is None:
            url = "{}://{}/{}".format("http", self.site, '/info_edu/staff/')
        else:
            url = "{}://{}/{}/{}".format("http", self.site, division, 'obwie_svedeniya/pedagogicheskij_kollektiv/')
        r = requests.get(url, cookies = self.cookies, timeout=self.timeout)
        soup = BeautifulSoup(r.text, 'html.parser')
        div = soup.find("div", id='collapse{}'.format(collection_id))
        divs = div.findAll("div", {"class": "col-md-3 teacherblock"})
        results = []
        for div in divs:
            name = div.findAll("a", {"class": "fio"})[0].text
            id = div.findAll("a", {"class": "copy_teacher"})[0]['id']
            results.append((id, name))
        return results

    def get_teacher_details(self, id):
        root = 0    # We'll never know why they need those
        parent = 0
        r = requests.get(
            "{}://{}/{}".format("http", self.site, "/udata/data/editForm//{}/{}/{}/void/(anons_pic,is_unindexed,h1,post,disciplines,branch_name,branch,work_fact,education,college,specialty,length_of_work,length_of_specialty,degree,skill,category,experience,awards,email,phone,skype,personal_page,blog,content)".format(id, root, parent)),
            cookies=self.cookies
        )
        t = Teacher(xml = r.text)
        return t

    def replace_file(self, file, binary_data, original_data, verbosity=0):
        if verbosity > 1:
            print("Удаляю старую картинку с сайта ({})".format(hash))
        uploaded = False
        deleted = False
        try:
            self.delete_file_by_hash(hash)
            deleted = True
            if verbosity > 1:
                print("Закачиваю картинку на сайт (tagret={})".format(file['phash']))
            self.upload_file_new(file['name'], binary_data, file['phash'])
            uploaded = True
        except Exception as e:
            if verbosity > 0:
                print("Произошла исключительная ситуация.")
                traceback.print_exc()
            if deleted and not uploaded:
                if verbosity > 0:
                    print("Внимание! Файл удален но копия не загружена. Попытка повторить загрузку.")
                try:
                    self.upload_file_new(file['name'], binary_data, file['phash'])
                    if verbosity > 0:
                        print("Успешно")
                except Exception:
                    if verbosity > 0:
                        traceback.print_exc()
                        print("Безуспешно. Попытка вернуть старый файл.")
                    try:
                        self.upload_file_new(file['name'], original_data, file['phash'])
                        if verbosity > 0:
                            print("Успешно")
                    except Exception:
                        if verbosity > 0:
                            traceback.print_exc()
                            print("Безуспешно. Остановка работы сценария.")
                            return False
            if isinstance(e, KeyboardInterrupt):
                raise KeyboardInterrupt()
            else:
                if verbosity > 0:
                    print("Попытка продолжить работу.")
