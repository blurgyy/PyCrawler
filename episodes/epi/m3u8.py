#!/usr/bin/python
#-*- coding:utf-8 -*-
__author__ = "Blurgy";

import os
from os import environ as env
import time
import shutil
import requests
from urllib.parse import unquote
from .globalfunctions import *

class m3u8:
    def __init__(self, _base_url = None, _from_ep = None, _from_file = None, ):
        try:
            # print("initializing class m3u8 with (base_url = %s, from_ep = %s)" % (_base_url, _from_ep, ));
            self.base_url = _base_url;
            if(self.base_url != None):
                if(not is_url(self.base_url)):
                    self.base_url = unquote(self.base_url);
                if(not is_url(self.base_url)):
                    print("invalid m3u8 url");
            self.from_ep = _from_ep;
            self.from_file = _from_file;
            self.content = None;
            if(self.from_file != None):
                if(os.path.exists(self.from_file)):
                    self.content = open(self.from_file).read();
                else:
                    raise Exception("%s not found" % self.from_file);
            self.url_pool = [];
            self.retry_pool = [];
            self.is_downloading = False;
            self.running_threads = None;
            self.maximum_threads = None;
            self.success_threads = None;
            self.video_fname = self.from_ep.epname if(self.from_ep) else split_fname(self.from_file);
            self.cachedir = env["HOME"] + "/.cache/blurgy/m3u8Download" + "/" + self.video_fname;
        except KeyboardInterrupt:
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("\033[1;31mm3u8.py::m3u8::__init__(): %s\033[0m" % e);

    def unify(self, url = None, ):  # download and unify the m3u8 document to a universal version (i.e. playable)
        try:
            if(self.from_file):
                return self.content;
            if(url == None):
                url = self.base_url;
            if(not is_url(url)):
                raise Exception("no url found during download");
            if(is_m3u8(url)):
                content = get_content(url);
                nurl = url;
                for line in content.splitlines():
                    if(re.match(r'^#.*?$', line)):
                        continue;
                    if(is_m3u8(line)):
                        nurl = None;
                        if(line[0] == '/'):
                            nurl = split_host(url) + line;
                        else:
                            nurl = re.sub(url.split('/')[-1], line, url);
                        # print("nurl =", nurl);
                        nurl = nurl.strip();
                        content = get_content(nurl);
                        break;
                    else:
                        break;
                self.content = "";
                for line in content.splitlines():
                    if(not is_url(line) and is_ts(line)):
                        if(line[0] == '/'):
                            host = split_host(url);
                            line = host + line;
                        else:
                            line = re.sub(line, re.sub(nurl.split('/')[-1], line, nurl), line);
                    self.content += line + '\n';
            else:   # what's this
                content = get_content(url);
                nurl = re.findall(r'"(.*?m3u8)', content)[0];
                if(not is_url(nurl)):
                    nurl = split_host(url) + nurl;
                # print(nurl);
                self.unify(nurl);
            return self.content;
        except KeyboardInterrupt:
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("\033[1;31mm3u8.py::m3u8::unify(): %s\033[0m" % e);
            return None;

    def download(self, dldir = None):
        fn_name = "m3u8.py::m3u8::download()";
        try:
            while(self.success_threads != len(self.url_pool)):
                print("caching..");
                self.cache();
            print("-- cache complete, concatenating..");
            self.concatenate(dldir);
            print("-- concatenate complete, file saved at [%s]" % (self.dl_fname))
        except KeyboardInterrupt:
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("%s: %s" % (fn_name, e));
            return False;


    def write_bin(self, url, target_file, ):
        fn_name = "m3u8.py::m3u8::write_bin()";
        try:
            if(self.is_downloading):
                if(not os.path.exists(target_file)):
                    with open(target_file, 'wb') as f:
                        f.write(requests.get(url).content);
            return True;
        except KeyboardInterrupt:
            os.remove(target_file);
            self.is_downloading = False;
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("%s: %s" % (fn_name, e));
            return False;

    def cache(self, ):
        fn_name = "m3u8.py::m3u8::cache()";
        try:
            if(not os.path.exists(self.cachedir)):
                os.makedirs(self.cachedir);
            os.chdir(self.cachedir);
            self.unify();
            for line in self.content.splitlines():
                if(is_url(line) and is_ts(line)):
                    self.url_pool.append(line);
            if(os.path.exists("self.m3u8")):
                excontent = open("self.m3u8").read();
                if(excontent != self.content):
                    os.chdir("..");
                    shutil.rmtree(self.video_fname);
                    os.makedirs(self.video_fname);
                    os.chdir(self.cachedir);
            with open("self.m3u8", 'w') as f:
                f.write(self.content);

            self.is_downloading = True;
            self.running_threads = 0;
            self.maximum_threads = 16;
            self.success_threads = 0;
            progbar = myThread(target = self.progressbar, args = ());
            progbar.start();
            self.supervisor_list = [];
            for i in range(len(self.url_pool)):
                url = self.url_pool[i];
                th = myThread(target = self.write_bin, args = (url, "%09d"%(i)));
                sup = myThread(target = self.supervisor, args = (th, ));
                sup.start();
                self.supervisor_list.append(sup);
            for sup in self.supervisor_list:
                sup.join();
            ### Retry
            self.supervisor_list = [];
            for th in self.retry_pool:
                sup = myThread(target = self.supervisor, args = (th, ));
                sup.start();
                self.supervisor_list.append(sup);
            for sup in self.supervisor_list:
                sup.join();
            self.is_downloading = False;
            progbar.join();
        except KeyboardInterrupt:
            self.is_downloading = False;
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("%s: %s" % (fn_name, e));

    def concatenate(self, dldir = None, ):
        fn_name = "m3u8.py::m3u8::concatenate()";
        try:
            if(self.is_downloading):
                print("download not finished, abort concatenating");
                return;
            if(dldir == None):
                dldir = env["HOME"] + "/Downloads/m3u8Download";
            if(not os.path.exists(dldir)):
                os.makedirs(dldir);
            fname = self.update_fname(dldir, self.video_fname);
            self.dl_fname = fname;

            fd = open(fname, 'wb');
            os.chdir(self.cachedir);
            for root, dirs, files in os.walk('.'):
                files.sort();
                for file in files:
                    if(re.match(r'\d+', file)):
                        with open(file, 'rb') as f:
                            fd.write(f.read());
            fd.close();
        except KeyboardInterrupt:
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("%s: %s" % (fn_name, e));

    def update_fname(self, fpath = None, fname = None):
        fn_name = "m3u8.py::m3u8::update_fname()";
        try:
            os.chdir(fpath);
            if(fname == None):
                fname = self.video_fname;
            ret = fname;
            idx = 1;
            while(os.path.exists(ret + ".ts")):
                idx += 1;
                ret = fname + " (%d)"%(idx);
            return fpath + '/' + ret + ".ts";
        except KeyboardInterrupt:
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("%s: %s" % (fn_name, e));
            return randstring();

    def supervisor(self, th, ):
        fn_name = "m3u8.py::m3u8::supervisor()";
        try:
            while(self.running_threads >= self.maximum_threads):
                pass;
            th.start();
            self.running_threads += 1;
            th.join();
            self.running_threads -= 1;
            if(th.fetch_result() == False):
                os.remove(th.args[1]);
                # print("removed %s" % th.args[1]);
                self.retry_pool.append(myThread(target = th.func, args = th.args));
            else:
                self.success_threads += 1;
        except KeyboardInterrupt:
            self.is_downloading = False;
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("%s: %s" % (fn_name, e));

    def progressbar(self, ):
        fn_name = "m3u8.py::m3u8::progressbar()";
        try:
            while(self.is_downloading):
                width = os.get_terminal_size().columns;
                length = width - 13;
                percent = self.success_threads / len(self.url_pool) * 100;
                # print(percent);
                print("\r [%s] %02.2f%%" % (bar(self.success_threads, len(self.url_pool), length), percent), end = '\r');
                time.sleep(0.3);
            percent = self.success_threads / len(self.url_pool) * 100;
            print(" [%s] %02.2f%%" % (bar(self.success_threads, len(self.url_pool), length), percent));
        except KeyboardInterrupt:
            self.is_downloading = False;
            print("\n KeyboardInterrupt, exiting");
            exit();
        except Exception as e:
            print("%s: %s" % (fn_name, e));
