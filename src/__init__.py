import os

# 针对国内金融API数据源进行代理绕过，防止本地代理导致连接被封或连接失败
# 同时保留外部API(如DeepSeek)对系统代理的支持
os.environ["NO_PROXY"] = "eastmoney.com,sina.com.cn,sina.cn,tencent.com,126.net,163.com,cninfo.com.cn"
