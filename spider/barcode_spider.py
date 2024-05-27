#!/bin/env python3
# coding = utf-8
import requests
import logging
import json
import subprocess
import tempfile
import os

logging.basicConfig(level=logging.DEBUG)

def download_and_read_file(url):
    # 创建临时文件
    temp_file_path = tempfile.mktemp()
    try:
        # 使用 wget 下载文件到临时文件路径，并且在静默模式下执行
        subprocess.run(["wget", "-q", "-O", temp_file_path, url], check=True)
        # 读取文件内容
        with open(temp_file_path, 'r') as file:
            file_content = file.read()
            return file_content  # 在这里你可以对文件内容进行处理
    finally:
        # 删除临时文件
        os.remove(temp_file_path)

def download_img_file(url, file_path):
    try:
        # 使用 wget 下载文件到临时文件路径，并且在静默模式下执行
        subprocess.run(["wget", "-q", "-O", file_path, url], check=True)
    except:
        print("exception when downloading img file")

class BarCodeSpider:
    '''
    条形码爬虫类
    '''
    def __init__(self, rapid_api_url="https://barcodes1.p.rapidapi.com/", 
                 x_rapidapi_key="", 
                 x_rapidapi_host="barcodes1.p.rapidapi.com"):

        self.logger = logging.getLogger(__name__)
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        self.base_url = 'https://bff.gds.org.cn/gds/searching-api/ProductService/homepagestatistic'
        self.domestic_url = "https://bff.gds.org.cn/gds/searching-api/ProductService/ProductListByGTIN?PageSize=30&PageIndex=1&SearchItem="
        #self.domestic_url = "https://bff.gds.org.cn/gds/searching-api/ProductService/ProductListByGTIN?PageSize=30&PageIndex=1&Gtin="
        self.domestic_url_simple = "https://bff.gds.org.cn/gds/searching-api/ProductService/ProductSimpleInfoByGTIN?gtin="
        #self.domestic_url_simple = "https://bff.gds.org.cn/gds/searching-api/ProductService/ProductSimpleInfoByGTIN"
        self.imported_url = "https://bff.gds.org.cn/gds/searching-api/ImportProduct/GetImportProductDataForGtin?PageSize=30&PageIndex=1&Gtin="
        self.imported_url_blk = "https://www.barcodelookup.com/"
        self.rapid_api_url = rapid_api_url
        self.x_rapidapi_key = x_rapidapi_key
        self.x_rapidapi_host= x_rapidapi_host

    def fetch_data_from_url(self, url):
        print(url)
        content = download_and_read_file(url)
        if content == "":
            self.logger.error("url content is empty, url: {}".format(url))
            return False, ""

        data = json.loads(content)
        if "Code" not in data or data["Code"] != 1:
            self.logger.error("Code is not 1, url: {}".format(url))
            return False, ""
        return True, data

    def get_domestic_good(self, barcode):
        state, data = self.fetch_data_from_url(self.base_url)
        if state == False:
            return None
       
        state, data = self.fetch_data_from_url(self.domestic_url + barcode)
        if state == False:
            self.logger.error(
                "error in getting domestic_url barcode is {}".format(barcode))
            return None

        good = data
        if good["Code"] == 2:
            self.logger.error("error, {}, barcode is {}".format(good["Msg"], barcode))
            return None
        if good["Code"] != 1 or good["Data"]["Items"] == []:
            self.logger.error("error, item no found, barcode is {}".format(barcode))
            return None

        base_id = good["Data"]["Items"][0]["base_id"]
        simple_data_url = self.domestic_url_simple + str(barcode) + "&id=" + base_id
        state, simpleInfo = self.fetch_data_from_url(simple_data_url)
        if state:
            good["Data"]["Items"][0]["simple_info"] = simpleInfo["Data"]
        else:
            self.logger.error("error, failed to get item simple info")

        self.logger.debug("good data, {}".format(good["Data"]["Items"][0]))

        return self.rework_good(good["Data"]["Items"][0])
    
    def get_imported_good(self, barcode):
        state, data = self.fetch_data_from_url(self.base_url)
        if state == False:
            good_blk = self.get_imorted_good_from_blk(barcode)
            return good_blk
       
        state, data = self.fetch_data_from_url(self.imported_url + barcode)
        if state == False:
            self.logger.error(
                "error in getting domestic_url barcode is {}".format(barcode))
            good_blk = self.get_imorted_good_from_blk(barcode)
            return good_blk

        good = data
        has_good_info = True
        if good["Code"] == 2:
            self.logger.error("error, {}, barcode is {}".format(good["Msg"], barcode))
            has_good_info = False
        if good["Code"] != 1 or good["Data"]["Items"] == []:
            self.logger.error("error, item no found, barcode is {}".format(barcode))
            has_good_info = False

        if (len(good["Data"]["Items"]) == 1) and (good["Data"]["Items"][0]["description_cn"] == None):
            has_good_info = False

        if has_good_info == False:
            good_blk = self.get_imorted_good_from_blk(barcode)
            return good_blk

        if (len(good["Data"]["Items"]) == 1) and (good["Data"]["Items"][0]["description_cn"] != None):
            return self.rework_good(good["Data"]["Items"][0])
            
        if (len(good["Data"]["Items"]) == 1) and (good["Data"]["Items"][0]["description_cn"] == None):
            good_blk = self.get_imorted_good_from_blk(barcode)
            return good_blk
            
        if len(good["Data"]["Items"]) >= 2:
            for item in good["Data"]["Items"]:
                if item["realname"] == item["importer_name"]:
                    return self.rework_good(item)
            return self.rework_good(good["Data"]["Items"][0])

    def get_imorted_good_from_blk(self, barcode):
        good = {}
        querystring = {"query": barcode}
        headers = {
            "X-RapidAPI-Key": self.x_rapidapi_key,
            "X-RapidAPI-Host": self.x_rapidapi_host
        }
        response = requests.get(self.rapid_api_url, headers=headers, params=querystring)
        good_dict = response.json()
        if "product" not in good_dict:
            return None
        
        good["description_cn"] = good_dict["product"]["title"]
        good["picfilename"] = good_dict["product"]["images"][0]
        attributes = good_dict["product"]["attributes"]
        good["specification_cn"] = ", ".join([f"{key}:{value}" for key, value in attributes.items()])
        good["gtin"] = barcode

        return good
    
    def rework_good(self, good):
        if "id" in good:
            del good["id"]
        if "f_id" in good:
            del good["f_id"]
        if "brandid" in good:
            del good["brandid"]
        if "base_id" in good:
            del good["base_id"]

        if good["branch_code"]:
            good["branch_code"] = good["branch_code"].strip()
        if "picture_filename" in good:
            if good["picture_filename"] and (not good["picture_filename"].startswith("http")):
                good["picture_filename"] = "https://oss.gds.org.cn" + good["picture_filename"]
        if "picfilename" in good:
            if good["picfilename"] and (not good["picfilename"].startswith("http")):
                good["picfilename"] = "https://oss.gds.org.cn" + good["picfilename"]

        return good

    def get_good(self, barcode):
        if barcode.startswith("69") or barcode.startswith("069"):
            return self.get_domestic_good(barcode)
        else:
            return self.get_imported_good(barcode)
        
def main():
    spider = BarCodeSpider(rapid_api_url="https://barcodes1.p.rapidapi.com/", 
                           x_rapidapi_key='c8d4c9fdeemsh07e3c4573bb3f16p12b0cejsnb4b979735e7c',
                           x_rapidapi_host="barcodes1.p.rapidapi.com")
    #国产商品
    #good = spider.get_good('06917878036526')
    #进口商品
    #good = spider.get_good('4901201103803')
    #国际商品
    good = spider.get_good('3346476426843')
    
    print(good)

if __name__ == '__main__':
    main()

'''
国产商品字典
"keyword": "农夫山泉",
"branch_code": "3301    ",
"gtin": "06921168593910",
"specification": "900毫升",
"is_private": false,
"firm_name": "农夫山泉股份有限公司",
"brandcn": "农夫山泉",
"picture_filename": "https://oss.gds.org.cn/userfile/uploada/gra/1712072230/06921168593910/06921168593910.1.jpg",
"description": "农夫山泉NFC橙汁900ml",
"logout_flag": "0",
"have_ms_product": 0,
"base_create_time": "2018-07-10T10:01:31.763Z",
"branch_name": "浙江分中心",
"base_source": "Source",
"gpc": "10000201",
"gpcname": "即饮型调味饮料",
"saledate": "2017-11-30T16:00:00Z",
"saledateyear": 2017,
"base_last_updated": "2019-01-09T02:00:00Z",
"base_user_id": "源数据服务",
"code": "69211685",
"levels": null,
"levels_source": null,
"valid_date": "2023-02-16T16:00:00Z",
"logout_date": null,
"gtinstatus": 1
'''

'''
进口商品字典
"gtin": "04901201103803",
"description_cn": "UCC117速溶综合咖啡90g",
"specification_cn": "90克",
"brand_cn": "悠诗诗",
"gpc": "10000115",
"gpc_name": "速溶咖啡",
"origin_cn": "392",
"origin_name": "日本",
"codeNet": null,
"codeNetContent": null,
"suggested_retail_price": 0,
"suggested_retail_price_unit": "人民币",
"txtKeyword": null,
"picfilename": "https://oss.gds.org.cn/userfile/importcpfile/201911301903478446204015916.png",
"realname": "磨禾（厦门）进出口有限公司",
"branch_code": "3501",
"branch_name": "福建分中心",
"importer_name": "磨禾（厦门）进出口有限公司",
"certificatefilename": null,
"certificatestatus": 0,
"isprivary": 0,
"isconfidentiality": 0,
"datasource": 0
'''

'''
国际商品字典
'''
