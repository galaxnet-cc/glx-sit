## 系统依赖

 OS: ubuntu 20.04
 Python: python3

## 办公室环境包重部署

### 前提
将本机public key加入所有目标dut的受信列表中。

### 配置
将conf目录的sitconf-example.json复制并改为sitconf.json，修改sitconf.json为自己的测试环境。

### 部署

将待安装的包拷贝到miscs/redeploy_1t_4d目录中的debs目录

```
cd misc/redeploy_1t_4d/
sh redeploy.sh
```

如果不进行出厂初始化，只更新包可以添加-f参数。

```
sh redeploy.sh -f
```

### 复位实验环境（恢复出厂激活状态）

```
cd misc/redeploy_1t_4d/
sh redeploy.sh -r
```

## 使用

方式0（makefile包装）


```
make test-basic
```

方式1/2本质上对于python unittest包的包装，可以直接参考python unittest包的文档了解如何执行测试用例，包括
执行特定用例（一个文件是一个测试集，代表一类测试例，一个test_*的类函数，则是一个具体的特试用例）。

方式1（手工执行）：

```
python3 -m unittest test_module1 test_module2
python3 -m unittest test_module.TestClass
python3 -m unittest test_module.TestClass.test_method
```

方式2（文件执行）：

```
python3 -m unittest testcases/test_something.py
```

## 待改进点

1. (DONE)~~topo对象支持读取配置文件。~~
2. (DONE)~~topo对象中的tst对象，连入topo的linux接口需支持读取配置文件。~~
