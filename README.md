## 系统依赖

 OS: ubuntu 20.04
 Python: python3

## 环境包重部署

### 前提
将本机public key加入所有目标dut的受信列表中。

### 部署

将待安装的包拷贝到miscs/redeploy_1t_4d目录中的debs目录
``
cd misc/redeploy_1t_4d/
sh redeploy.sh
# 不进行出厂初始化，即仅更新包
sh redeploy.sh -f
``

### 复位

``
cd misc/redeploy_1t_4d/
sh redeploy.sh -r
``

## 使用

方式０（全量执行）

``
make
``

方式１：

``
python3 -m unittest test_module1 test_module2
python3 -m unittest test_module.TestClass
python3 -m unittest test_module.TestClass.test_method
``

方式２：

``
python3 -m unittest testcases/test_something.py
``

## 待改进点

1. topo对象支持读取配置文件。
2. topo对象中的tst对象，连入topo的linux接口需支持读取配置文件。
