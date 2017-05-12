# MADSITE: Автоматизация для mskobr.ru

Library and collection of scripts to work with mskobr.ru: directory listings, file uploads, hatered and fear.

## What the hell is this

Moscow department of education introduced a mandatory-to-use service for local public schools. The service is based on umi.cms; unfortunately, school administrators don't have any direct access to uploading files, or the database. All operations are performed through web interface. 

In our school, a necessity of integrating some local databases with the site has risen, and we had to develop this project as an interface to the site.

## Установка

* Шаг 1: скачать проект

    `git clone https://github.com/iharthi/madsite.git madsite`

* Шаг 2: установить зависимости

    `pip install -r madsite/requirements.txt `

## Использование

### Сжатие картинок и pdf на сайте: compress.py

Для работы сценария compress.py у вас на компьютере должен быть установлен ghostscript (https://www.ghostscript.com/) — этот замечательный пакет используется для сжатия pdf-ок.

В простейшем случае, compress.py запускается с единственным аргументом - именем сайта (__sitename__.mskobr.ru); остальные параметры задаются в интерактивном режиме.

Например: `compress.py sch45uz`
